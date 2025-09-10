# VistA MUMPS Globals Quickstart: Read, Decode, Modernize

## What You’ll Do
- Understand the `^GLOBAL(sub1,sub2,...)=value` pattern
- Parse patient demographics from `^DPT`
- Convert FileMan dates to standard date/time
- Produce simple extracts and optional FHIR Patient output

## Primer
- Globals are sparse, hierarchical key/value stores (VA VistA).
- Common patient data: `^DPT(IEN,field,...)=value` where `0` is a caret‑delimited main record.
- Frequent fields: `.02` sex (M/F), `.03` DOB (FileMan), `.09` SSN, `.11` address multi, `.131` phones.

## FileMan Date Conversion
```python
from datetime import datetime, date

def fm_date(d):
    # 7-digit: YYYMMDD where year = (century_offset+17)*100 + MM
    if not d: return None
    s = str(d).split('.')[0]
    if len(s) != 7: return None
    century = int(s[0]) + 17
    year = century*100 + int(s[1:3])
    return date(year, int(s[3:5]), int(s[5:7]))

def fm_datetime(dt):
    if not dt: return None
    parts = str(dt).split('.')
    d, t = parts[0], parts[1] if len(parts)>1 else '0000'
    dd = fm_date(d)
    if not dd: return None
    t = (t+'0000')[:6]
    h = int(t[:2]) if len(t)>=2 else 0
    m = int(t[2:4]) if len(t)>=4 else 0
    s = int(t[4:6]) if len(t)>=6 else 0
    return datetime(dd.year, dd.month, dd.day, h, m, s)
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
        demo['dob'] = fm_date(parts[2]) if len(parts)>2 and parts[2] else None
        demo['ssn'] = parts[3] if len(parts)>3 else ''
    if '.02' in node: demo['sex'] = node['.02']
    if '.03' in node: demo['dob'] = fm_date(node['.03'])
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
- Normalize FileMan date/times early to avoid downstream confusion.
- Use small dictionaries to map VA codes to modern vocabularies incrementally.

