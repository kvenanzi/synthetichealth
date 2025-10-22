# VistA MUMPS Globals Quickstart: Read, Decode, Modernize

## What You’ll Do
- Understand the `^GLOBAL(sub1,sub2,...)=value` pattern
- Parse patient demographics from `^DPT`
- Convert generator-specific VistA date/datetime encodings to standard Python objects
- Produce simple extracts and optional FHIR Patient output

## Primer
- Globals are sparse, hierarchical key/value stores (VA VistA).
- Common patient data: `^DPT(IEN,field,...)=value` where `0` is a caret‑delimited main record.
- Default exporter detail (`--vista-mode fileman_internal`): DOB values are **FileMan dates** (`YYYMMDD` with `YYY = year-1700`), encounters use FileMan datetimes (`YYYMMDD.HHMMSS`).
- Legacy mode (`--vista-mode legacy`) retains the earlier day-offset encoding. Use only when reproducing historical artifacts.
- Frequent fields: `.02` sex (M/F/U), `.03` DOB (FileMan date), `.09` SSN, `.11` address (state stored as a pointer IEN), `.13` phone.
- VistA exporter now bundles clinical data:
  - `^AUPNVMED` (V Medication #9000010.14) ties patients to `^PSDRUG` entries and encounters, storing FileMan start/stop dates and standard `"B"/"V"/"AA"` xrefs.
  - `^AUPNVLAB` (V Laboratory #9000010.09) records lab values with `^LAB(60)` pointers, FileMan datetimes, units, and reference ranges along `"B"/"V"/"AE"` indexes.
  - `^GMR(120.8)` (Patient Allergies) references `^GMR(120.82)` allergen definitions and captures reaction/severity text with internal IENs only.
  - `^AUPNVCPT` (V CPT) stores CPT-coded procedures linked to visits and `^ICPT` stubs with `"B"/"V"/"C"` indices.
  - `^AUPNVMSR` (V Measurement) captures vitals (BP, pulse, resp, temp, SpO₂, height, weight, BMI) via `^AUTTMSR` measurement types.
  - `^AUPNVHF` (V Health Factor) records SDOH/behavioral/substance factors referencing `^AUTTHF`.
  - `^TIU(8925)` produces care-plan notes under the “Care Plan” title with visit linkage; title definitions land in `^TIU(8925.1)`.

## Minimal File Layout
- **Patients (`^DPT`)** – demographics, address (.11), phone (.13), with `"B"`, `"SSN"`, `"DOB"` cross-references.
- **Visits (`^AUPNVSIT`)** – zero node `DFN^FMDateTime^ServiceCategory^ClinicStop`, `.06` location pointer, and `"B"/"D"/"GUID"` indexes.
- **Problems (`^AUPNPROB`)** – problem record `DFN^NarrativeIEN^Status^FMOnset^ICDIEN`, `.05` narrative pointer, `"S"` status and `"ICD"` diagnosis indexes.
- **Medications (`^AUPNVMED`)** – `DFN^DrugIEN^VisitIEN^FMStart^Status` (optional stop date at node `5101`, indication at `13`) with `"B"` (patient), `"V"` (visit), and `"AA"` (drug) cross-references; minimal drug entries are emitted under `^PSDRUG(IEN,0)=<NAME>^<RxNorm>` with `"B"` index.
- **Labs (`^AUPNVLAB`)** – `DFN^TestIEN^VisitIEN^Value^Units^Status^FMDatetime` plus node `11` (reference range) and `12` (panel). Pointer stubs live at `^LAB(60,IEN,0)=<NAME>^<LOINC>` with `"B"` xrefs.
- **Allergies (`^GMR(120.8)`)** – `DFN^AllergenIEN^^o^FMRecorded` plus reaction node `1` and severity node `3`, with `"B"` (patient) and `"C"` (allergen) indices; supporting dictionary entries are added to `^GMR(120.82)`.
- **Procedures (`^AUPNVCPT`)** – `DFN^VisitIEN^CPT_IEN^FMDate^Quantity` with `"B"` (patient), `"V"` (visit), and `"C"` (CPT) cross-references; CPT stubs populate `^ICPT(IEN,0)=<CODE>^<DESC>`.
- **Measurements (`^AUPNVMSR`)** – `DFN^TypeIEN^VisitIEN^Value^Units^FMDatetime`; measurement types appear under `^AUTTMSR` (e.g., BLOOD PRESSURE, PULSE, RESPIRATION, HEIGHT, WEIGHT, BMI, OXYGEN SATURATION).
- **Health Factors (`^AUPNVHF`)** – `DFN^HF_IEN^VisitIEN^FMDatetime` for SDOH/behavioral risk entries. Dictionary stubs (`^AUTTHF`) include SDOH (Housing Instability, Food Insecurity, Transportation) and behavioral flags (PHQ-9 Moderate/Severe, Current/Former Smoker, Heavy Alcohol Use).
- **Care Plans (`^TIU(8925)`)** – TIU notes titled “Care Plan” summarizing pathway stage/status and outstanding activities. Note text is stored in the `"TEXT"` multiple and pointer definitions live at `^TIU(8925.1)`.

## Date Conversion Helpers
```python
from datetime import datetime, date

def fileman_date(value: str | int | None):
    """Convert FileMan dates (YYYMMDD where YYY = year-1700) to `date`."""
    if value in (None, ""):
        return None
    digits = str(value).split('.')[0]
    if len(digits) != 7:
        return None
    try:
        years_since_1700 = int(digits[:3])
        year = 1700 + years_since_1700
        month = int(digits[3:5])
        day = int(digits[5:7])
        return date(year, month, day)
    except ValueError:
        return None

def fileman_timestamp(value: str | None):
    """Convert FileMan datetimes (YYYMMDD.HHMMSS) to `datetime`."""
    if not value:
        return None
    chunk = str(value)
    date_part, _, time_part = chunk.partition('.')
    base = fileman_date(date_part)
    if not base:
        return None
    time_part = (time_part + "000000")[:6]
    try:
        hour = int(time_part[0:2])
        minute = int(time_part[2:4])
        second = int(time_part[4:6])
    except ValueError:
        hour = minute = second = 0
    return datetime(base.year, base.month, base.day, hour, minute, second)
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
            if line.startswith('S '):
                line = line[2:].lstrip()
            lhs, rhs = line.split('=', 1)
            m = gpat.match(lhs)
            if not m: continue
            name, subs = m.group(1), parse_subscripts(m.group(2))
            bucket = data.setdefault(name, {})
            value = rhs.strip('"')
            set_nested(bucket, subs, value)
    return data
```

## Extract Patient Demographics (DPT)
```python
def parse_dpt_demographics(doc: Dict[str, Any], ien: str) -> Dict[str, Any]:
    node = (doc.get('DPT') or {}).get(ien) or {}
    demo = {}
    if '0' in node:
        record = node['0'].strip('"') if isinstance(node['0'], str) else str(node['0'])
        parts = record.split('^')
        demo['name'] = parts[0] if parts else ''
        demo['sex'] = parts[1] if len(parts)>1 else ''
        demo['dob'] = fileman_date(parts[2]) if len(parts)>2 and parts[2] else None
        demo['ssn'] = parts[3] if len(parts)>3 else ''
    if '.02' in node: demo['sex'] = node['.02']
    if '.03' in node: demo['dob'] = fileman_date(node['.03'])
    if '.09' in node: demo['ssn'] = node['.09']
    if '.11' in node:
        parts = (node['.11'] or '').split('^')
        demo['address'] = {
            'street1': parts[0] if len(parts) > 0 else '',
            'street2': parts[1] if len(parts) > 1 else '',
            'city': parts[2] if len(parts) > 2 else '',
            'state': parts[3] if len(parts) > 3 else '',
            'zip': parts[4] if len(parts) > 4 else '',
        }
    if '.13' in node and node['.13']:
    demo['phones'] = [node['.13']]
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
- Normalize FileMan DOBs and datetimes immediately; fall back to legacy day-offset helper only if you generated with `--vista-mode legacy`.
- Use small dictionaries to map VA codes to modern vocabularies incrementally.
