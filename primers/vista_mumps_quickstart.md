# VistA MUMPS Globals Quickstart: Read, Decode, Modernize

## What You’ll Do
- Understand the `^GLOBAL(sub1,sub2,...)=value` pattern
- Parse patient demographics from `^DPT`
- Convert generator-specific VistA date/datetime encodings to standard Python objects
- Produce simple extracts and optional FHIR Patient output

## Primer
- Globals are sparse, hierarchical key/value stores (VA VistA).
- Common patient data: `^DPT(IEN,field,...)=value` where `0` is a caret‑delimited main record.
- Phase 3 exporter detail: DOB values in the `0` node or `.03` node are **day offsets since 1841-01-01**, not legacy 7-digit FileMan dates.
- Frequent fields: `.02` sex (M/F), `.03` DOB (day offsets), `.09` SSN, `.11` address multi, `.131` phones.

## Date Conversion Helpers
```python
from datetime import datetime, date, timedelta

VISTA_EPOCH = date(1841, 1, 1)

def vista_days_to_date(value: str | int | None):
    """Convert day offsets (used in ^DPT) to a `date`."""
    if value in (None, ""):
        return None
    try:
        days = int(str(value).split('.')[0])
    except ValueError:
        return None
    return VISTA_EPOCH + timedelta(days=days)

def vista_timestamp_to_datetime(value: str | None):
    """Convert visit timestamps (YYYMMDD.HHMMSS with Y=years since 1700) to `datetime`."""
    if not value:
        return None
    chunk = str(value)
    date_part, _, time_part = chunk.partition('.')
    if len(date_part) < 5:
        return None
    try:
        years_since_1700 = int(date_part[:-4])
        month = int(date_part[-4:-2])
        day = int(date_part[-2:])
        year = 1700 + years_since_1700
    except ValueError:
        return None
    time_part = (time_part + "000000")[:6]
    try:
        hour = int(time_part[0:2])
        minute = int(time_part[2:4])
        second = int(time_part[4:6])
    except ValueError:
        hour = minute = second = 0
    try:
        return datetime(year, month, day, hour, minute, second)
    except ValueError:
        return None
```

## Minimal Global Parser
```python
import re
from typing import Dict, Any, List

gpat = re.compile(r'^\^([A-Z0-9]+)\((.*)\)$')

def parse_subscripts(s: str) -> List[str]:
    out, cur, q = [], '', False
    for ch in s:
        if ch == '"':
            q = not q
        elif ch == ',' and not q:
            out.append(cur.strip()); cur = ''
        else:
            cur += ch
    if cur.strip(): out.append(cur.strip())
    return out

def set_nested(root: Dict, keys: List[str], value: str):
    cur = root
    for k in keys[:-1]:
        cur = cur.setdefault(k, {})
    cur[keys[-1]] = value

def parse_globals_file(path: str) -> Dict[str, Any]:
    data: Dict[str, Any] = {}
    with open(path, 'r', encoding='utf-8') as f:
        for raw in f:
            line = raw.strip()
            if not line or '=' not in line: continue
            lhs, rhs = line.split('=', 1)
            m = gpat.match(lhs)
            if not m: continue
            name, subs = m.group(1), parse_subscripts(m.group(2))
            bucket = data.setdefault(name, {})
            set_nested(bucket, subs, rhs)
    return data
```

## Extract Patient Demographics (DPT)
```python
def parse_dpt_demographics(doc: Dict[str, Any], ien: str) -> Dict[str, Any]:
    node = (doc.get('DPT') or {}).get(ien) or {}
    demo = {}
    if '0' in node:
        parts = node['0'].split('^')
        demo['name'] = parts[0] if parts else ''
        demo['sex'] = parts[1] if len(parts)>1 else ''
        demo['dob'] = vista_days_to_date(parts[2]) if len(parts)>2 and parts[2] else None
        demo['ssn'] = parts[3] if len(parts)>3 else ''
    if '.02' in node: demo['sex'] = node['.02']
    if '.03' in node: demo['dob'] = vista_days_to_date(node['.03'])
    if '.09' in node: demo['ssn'] = node['.09']
    if '.11' in node:
        a = node['.11']
        demo['address'] = {
            'street1': a.get('1',''), 'street2': a.get('2',''),
            'city': a.get('3',''), 'state': a.get('4',''), 'zip': a.get('5','')
        }
    if '.131' in node:
        phones = []
        for k, v in (node['.131'] or {}).items():
            if isinstance(v, dict) and '0' in v:
                phones.append(v['0'].split('^')[0])
        demo['phones'] = phones
    return demo
```

## Optional: Convert to FHIR Patient
```python
def vista_to_fhir_patient(ien: str, demo: Dict[str, Any]) -> Dict[str, Any]:
    last, given = '', []
    if demo.get('name'):
        parts = demo['name'].split(',')
        last = parts[0]
        given = parts[1].strip().split() if len(parts)>1 else []
    gender = {'M':'male','F':'female'}.get(demo.get('sex',''), 'unknown')
    out = {
        'resourceType': 'Patient',
        'id': f'vista-{ien}',
        'identifier': [{
            'use': 'usual',
            'type': {'coding': [{'system':'http://terminology.hl7.org/CodeSystem/v2-0203','code':'MR'}]},
            'system': 'https://va.gov/vista-ien',
            'value': ien
        }],
        'name': [{'use': 'official','family': last,'given': given}],
        'gender': gender
    }
    if demo.get('ssn'):
        out['identifier'].append({
            'use':'official','type':{'coding':[{'system':'http://terminology.hl7.org/CodeSystem/v2-0203','code':'SS'}]},
            'system':'http://hl7.org/fhir/sid/us-ssn','value': demo['ssn']
        })
    if demo.get('dob'): out['birthDate'] = demo['dob'].isoformat()
    if demo.get('address'):
        a = demo['address']
        out['address'] = [{
            'use':'home','type':'physical','line':[x for x in [a.get('street1'), a.get('street2')] if x],
            'city': a.get('city',''),'state': a.get('state',''),'postalCode': a.get('zip','')
        }]
    if demo.get('phones'):
        out['telecom'] = [{'system':'phone','value':p,'use':'home'} for p in demo['phones']]
    return out
```

## Tips
- Keep IENs stable for lineage during migration.
- Expect sparsity and optional subtrees; always guard lookups.
- Normalize day-offset DOBs and FileMan-style visit timestamps early to avoid downstream confusion.
- Use small dictionaries to map VA codes to modern vocabularies incrementally.
