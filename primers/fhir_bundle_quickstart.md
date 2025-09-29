# FHIR Bundle Quickstart: Read, Explore, and Use R4 Data

## What You’ll Do
- Load a FHIR R4 Bundle (JSON)
- Identify common resources (Patient, Condition, MedicationRequest, Observation)
- Safely traverse references and extract coded data
- Convert to tabular (CSV) or validate with a library

Repo sample: `fhir_bundle.json` (produced by the Phase 3 generator with module-driven workflows and terminology enrichments such as VSAC/UMLS extensions).

## Core Concepts
- Resource basics: every object has `resourceType`, optional `id`, `meta`, and resource‑specific fields.
- Bundle: a container with `type` and `entry[]` where `entry[i].resource` is the FHIR resource.
- References: e.g., `{ "reference": "Patient/123" }` link resources.
- CodeableConcept: carries codes across systems (SNOMED, LOINC, ICD‑10, RxNorm) via `coding[]`.

## Minimal Reader (Python)
```python
import json
from collections import defaultdict

with open('fhir_bundle.json', 'r', encoding='utf-8') as f:
    bundle = json.load(f)

entries = bundle.get('entry', [])
by_type = defaultdict(list)

for e in entries:
    r = e.get('resource', {})
    by_type[r.get('resourceType', 'Unknown')].append(r)

print('Bundle type:', bundle.get('type'))
for t, rs in by_type.items():
    print(f"{t}: {len(rs)}")
```

## Extract Essentials
- Patients
```python
def patient_name(patient):
    try:
        n = patient['name'][0]
        return f"{' '.join(n.get('given', []))} {n.get('family','')}".strip()
    except Exception:
        return 'Unknown'

patients = by_type.get('Patient', [])
for p in patients[:5]:
    print(p.get('id'), patient_name(p), p.get('gender'), p.get('birthDate'))
```

- Conditions per Patient (module-enabled cohorts emit cardiometabolic, oncology, CKD, COPD, and behavioral pathways)
```python
def resolve_ref_text(ref):
    # returns ('ResourceType', 'id') or (None, None)
    if not ref or 'reference' not in ref:
        return (None, None)
    parts = ref['reference'].split('/')
    return (parts[0], parts[1]) if len(parts) == 2 else (None, None)

conditions = by_type.get('Condition', [])
from collections import defaultdict
conds_by_patient = defaultdict(list)
for c in conditions:
    rt, rid = resolve_ref_text(c.get('subject'))
    if rt == 'Patient' and rid:
        conds_by_patient[rid].append(c)

for pid, cs in list(conds_by_patient.items())[:3]:
    labels = [c.get('code', {}).get('text') for c in cs]
    print(pid, labels)
```

- Extract codes from CodeableConcept
```python
def codes(cc):
    out = {}
    for coding in cc.get('coding', []):
        system = coding.get('system', '')
        code = coding.get('code')
        if not code:
            continue
        if 'snomed' in system:
            out['SNOMED'] = code
        elif 'loinc' in system or coding.get('system') == 'http://loinc.org':
            out['LOINC'] = code
        elif 'icd-10' in system:
            out['ICD10'] = code
        elif 'rxnorm' in system:
            out['RXCUI'] = code
    return out
```

## To CSV (Patients)
```python
import csv

rows = []
for p in patients:
    name = patient_name(p)
    addr = (p.get('address') or [{}])[0]
    rows.append({
        'id': p.get('id', ''),
        'name': name,
        'gender': p.get('gender',''),
        'birthDate': p.get('birthDate',''),
        'city': addr.get('city',''),
        'state': addr.get('state',''),
        'postalCode': addr.get('postalCode','')
    })

if rows:
    with open('patients.csv', 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys())
        w.writeheader(); w.writerows(rows)
    print('Wrote patients.csv')
else:
    print('No Patient resources found')
```

## Optional: Validate with `fhir.resources`
```bash
pip install fhir.resources
```
```python
from fhir.resources.bundle import Bundle
b = Bundle.parse_file('fhir_bundle.json')
print('Validated entries:', len(b.entry or []))
```

## Tips
- Always branch on `resourceType` before accessing fields.
- Prefer `.get()` and defaults; real data is often sparse.
- Keep original IDs and references intact for traceability.
- Code systems vary; fall back to `.text` when codings are missing.
