# HL7 v2 ADT Quickstart: Admit/Discharge/Transfer Basics

## What You’ll Do
- Recognize ADT message anatomy (MSH, EVN, PID, PV1)
- Parse pipe‑delimited fields and components
- Extract demographics and visit details
- Export to CSV and handle multiple messages

## Message Shape
```
MSH|^~\&|SND_APP|SND_FAC|RCV_APP|RCV_FAC|20240101123000||ADT^A04|MSG001|P|2.5
EVN||20240101123000|||OP123
PID|1||MRN123^^^FAC^MR~999999999^^^USA^SS||DOE^JOHN^M||19800115|M|||123 MAIN^^ANYTOWN^VA^12345||555-123-4567
PV1|1|O|CLINIC^01^A|||R|||ATT001|||||ADM||||20240101123000
```

Key separators: `|` field, `^` component, `~` repetition, `&` sub‑component, `\\` escape.

## Minimal Parser (Python)
```python
def parse_segments(text: str):
    return [ln.strip() for ln in text.strip().split('\n') if ln.strip()]

def split_fields(seg: str):
    parts = seg.split('|')
    return parts[0], parts[1:]

def parse_name(xpn: str):
    comps = (xpn or '').split('^')
    return {
        'family': comps[0] if len(comps) > 0 else '',
        'given': comps[1] if len(comps) > 1 else '',
        'middle': comps[2] if len(comps) > 2 else ''
    }

def parse_identifiers(cx_rep: str):
    ids = {}
    for rep in (cx_rep or '').split('~'):
        comps = rep.split('^')
        if len(comps) >= 5 and comps[0]:
            ids[comps[4]] = {'value': comps[0], 'assigner': comps[3]}
    return ids

def parse_address(xad: str):
    c = (xad or '').split('^')
    return {
        'street': c[0] if len(c) > 0 else '',
        'city': c[2] if len(c) > 2 else '',
        'state': c[3] if len(c) > 3 else '',
        'zip': c[4] if len(c) > 4 else ''
    }

def parse_adt(message: str):
    segs = {s[:3]: s for s in parse_segments(message)}
    msh = split_fields(segs.get('MSH',''))[1]
    pid = split_fields(segs.get('PID',''))[1]
    pv1 = split_fields(segs.get('PV1',''))[1]

    return {
        'message_type': msh[7] if len(msh) > 7 else '',  # MSH.9
        'control_id': msh[8] if len(msh) > 8 else '',     # MSH.10
        'patient': {
            'ids': parse_identifiers(pid[2] if len(pid) > 2 else ''),  # PID.3
            'name': parse_name(pid[4] if len(pid) > 4 else ''),        # PID.5
            'birth_date': pid[6] if len(pid) > 6 else '',              # PID.7 (YYYYMMDD)
            'gender': pid[7] if len(pid) > 7 else '',                  # PID.8
            'address': parse_address(pid[10] if len(pid) > 10 else ''),# PID.11
            'phone': pid[12] if len(pid) > 12 else ''                  # PID.13
        },
        'visit': {
            'class': pv1[1] if len(pv1) > 1 else '',                   # PV1.2
            'location': pv1[2] if len(pv1) > 2 else '',                 # PV1.3
            'attending': pv1[6] if len(pv1) > 6 else '',                # PV1.7
            'admit_time': pv1[43] if len(pv1) > 43 else ''              # PV1.44
        }
    }
```

## Multiple Messages → CSV
```python
import csv

def adt_file_to_csv(input_text: str, out_csv: str):
    messages = [m for m in input_text.strip().split('\n\n') if m.strip()]
    rows = []
    for m in messages:
        d = parse_adt(m)
        p = d['patient']; v = d['visit']
        mrn = (p['ids'].get('MR') or {}).get('value','')
        rows.append({
            'message_type': d['message_type'],
            'control_id': d['control_id'],
            'mrn': mrn,
            'first_name': p['name']['given'],
            'last_name': p['name']['family'],
            'birth_date': p['birth_date'],
            'gender': p['gender'],
            'address': f"{p['address']['street']}, {p['address']['city']}",
            'patient_class': v['class'],
            'location': v['location'],
            'admit_time': v['admit_time']
        })
    if not rows:
        return print('No messages found')
    with open(out_csv, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys())
        w.writeheader(); w.writerows(rows)
    print('Wrote', out_csv)
```

## Practical Notes
- Don’t assume encoding: parse from `MSH.2` if available.
- ADT events: A01 (admit), A02 (transfer), A03 (discharge), A04 (register), A08 (update).
- Segment optionality varies by trigger: tolerate missing PV2/AL1/OBX.
- Timestamps are `YYYYMMDD[HHMMSS]`; always validate length before parsing.

