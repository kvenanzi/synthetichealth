# HL7 v2 ORU Quickstart: Lab and Observation Results

## What You’ll Do
- Recognize ORU message anatomy (MSH, PID, OBR, OBX)
- Group OBX results under their OBR order context
- Parse numeric vs. coded vs. text result values
- Summarize abnormalities and build a lightweight lab DB

## Message Shape
```
MSH|^~\&|LAB|HOSP_LAB|EHR|HOSP|20240101143000||ORU^R01|MSG002|P|2.5
PID|1||MRN123^^^HOSP^MR||DOE^JOHN^M||19800115|M
OBR|1|PLACER1|FILLER1|2345-7^GLUCOSE^LN|||20240101140000|||||||||DR001|||F
OBX|1|NM|2345-7^GLUCOSE^LN|1|95|mg/dL|70-110|N|||F
OBX|2|TX|2345-7^COMMENT^LN|2|Slightly elevated last visit|||A|||F
```

## Minimal Parser (Python)
```python
from datetime import datetime

FS, CS, RS = '|', '^', '~'

def ts(s: str):
    if not s or len(s) < 8: return None
    if len(s) >= 14:
        return datetime.strptime(s[:14], '%Y%m%d%H%M%S')
    return datetime.strptime(s[:8], '%Y%m%d')

def coded(field: str):
    parts = (field or '').split(CS)
    return {'code': parts[0] if len(parts)>0 else '',
            'text': parts[1] if len(parts)>1 else '',
            'system': parts[2] if len(parts)>2 else ''}

def parse_oru(msg: str):
    lines = [ln for ln in msg.strip().split('\n') if ln.strip()]
    segs = {'MSH': None, 'PID': None, 'OBR': []}
    cur = None
    for ln in lines:
        st = ln[:3]
        if st == 'MSH': segs['MSH'] = ln
        elif st == 'PID': segs['PID'] = ln
        elif st == 'OBR':
            cur = {'OBR': ln, 'OBX': []}; segs['OBR'].append(cur)
        elif st == 'OBX' and cur:
            cur['OBX'].append(ln)

    # Parse MSH
    msh = (segs['MSH'] or '').split(FS)
    header = {
        'type': msh[8] if len(msh)>8 else '',
        'control_id': msh[9] if len(msh)>9 else '',
        'timestamp': ts(msh[6] if len(msh)>6 else '')
    }

    # Parse PID (ids+name only)
    pid = (segs['PID'] or '').split(FS)
    ids = {}
    for rep in (pid[3] if len(pid)>3 else '').split(RS):
        parts = rep.split(CS)
        if len(parts)>=5 and parts[0]:
            ids[parts[4]] = {'value': parts[0], 'assigner': parts[3]}
    name_parts = (pid[5] if len(pid)>5 else '').split(CS)
    patient = {
        'ids': ids,
        'name': {
            'family': name_parts[0] if len(name_parts)>0 else '',
            'given': name_parts[1] if len(name_parts)>1 else ''
        },
        'birth_date': pid[7] if len(pid)>7 else '',
        'gender': pid[8] if len(pid)>8 else ''
    }

    # Parse OBR/OBX
    observations = []
    for grp in segs['OBR']:
        obr_f = grp['OBR'].split(FS)
        order = {
            'placer': obr_f[2] if len(obr_f)>2 else '',
            'filler': obr_f[3] if len(obr_f)>3 else '',
            'service': coded(obr_f[4] if len(obr_f)>4 else ''),
            'obs_time': ts(obr_f[7] if len(obr_f)>7 else ''),
            'status': obr_f[25] if len(obr_f)>25 else ''
        }
        results = []
        for obx in grp['OBX']:
            f = obx.split(FS)
            vtype = f[2] if len(f)>2 else ''
            raw = f[5] if len(f)>5 else ''
            if vtype == 'NM':
                try: value = float(raw) if '.' in raw else int(raw)
                except: value = raw
            elif vtype == 'CE':
                value = coded(raw)
            else:
                value = raw
            results.append({
                'id': f[1] if len(f)>1 else '',
                'identifier': coded(f[3] if len(f)>3 else ''),
                'sub_id': f[4] if len(f)>4 else '',
                'value_type': vtype,
                'value': value,
                'units': f[6] if len(f)>6 else '',
                'ref_range': f[7] if len(f)>7 else '',
                'flag': f[8] if len(f)>8 else '',
                'status': f[11] if len(f)>11 else ''
            })
        observations.append({'order': order, 'results': results})

    return {'header': header, 'patient': patient, 'observations': observations}
```

## Abnormality Summary
```python
def summarize_abnormal(parsed):
    flags = {'H':0,'L':0,'HH':0,'LL':0,'A':0}
    for grp in parsed['observations']:
        for r in grp['results']:
            f = r['flag']
            if f in flags:
                flags[f] += 1
    return flags
```

## Tips
- Grouping matters: each OBR may have many OBX; keep results with their order.
- Value types: NM (numeric), ST/TX (text), CE (coded). Parse accordingly.
- Check `OBR.25`/`OBX.11` before acting on results (Final vs. Preliminary/Corrected).
- Use LOINC (`OBX.3`) to normalize tests across systems.

