# HL7 v2 Validation Playbook: From Syntax to Business Rules

## Goals
- Catch malformed messages early (syntax/encoding)
- Validate core datatypes (DT, TS, NM, XPN, CE)
- Apply pragmatic business rules for ADT/ORU flows
- Produce actionable, compact reports

## Layered Approach
1) Syntax (Level 1): segment order, separators, minimal required segments present.
2) Datatypes (Level 2): field content constraints (date, number, name, coded element).
3) Business Rules (Level 3): domain checks (e.g., age/test pairing, critical values).

## Level 1: Syntax Check (Python)
```python
def l1_syntax(message: str):
    lines = [ln for ln in message.split('\n') if ln.strip()]
    errs, warns = [], []
    if not lines or not lines[0].startswith('MSH'):
        return {'valid': False, 'errors': ['Missing MSH'], 'warnings': []}
    msh = lines[0]
    if len(msh) < 8: errs.append('MSH too short')
    fs = msh[3] if len(msh)>3 else '|'
    enc = msh[4:8] if len(msh)>=8 else '^~\\&'
    if fs != '|': errs.append(f"Invalid field sep: {fs}")
    if enc != '^~\\&': warns.append(f"Non-standard enc: {enc}")
    for i, ln in enumerate(lines, 1):
        if len(ln) < 3 or not ln[:3].isalpha():
            errs.append(f"Line {i}: invalid segment id")
        if fs not in ln:
            warns.append(f"Line {i}: missing field sep")
    return {'valid': not errs, 'errors': errs, 'warnings': warns}
```

## Level 2: Datatypes
```python
from datetime import datetime

def is_date(s):
    if not s or len(s)!=8 or not s.isdigit(): return False
    try: datetime.strptime(s, '%Y%m%d'); return True
    except: return False

def is_ts(s):
    if not s or len(s)<8: return False
    if not is_date(s[:8]): return False
    if len(s) >= 14 and not s[8:14].isdigit(): return False
    return True

def is_number(s):
    if s is None or s=='': return True
    try: float(s); return True
    except: return False

def valid_name(xpn):
    return True if xpn is None else len(xpn.split('^')) <= 14

def valid_ce(ce):
    # code^text^system
    if not ce: return True
    parts = ce.split('^')
    return len(parts) >= 3 and parts[0] != ''
```

## Level 3: Business Rules (Examples)
```python
def br_critical_glucose(obx):
    # obx: dict with keys {'value_type','value','flag','identifier':{'text':...}}
    name = (obx.get('identifier',{}).get('text') or '').upper()
    vtype = obx.get('value_type')
    val = obx.get('value')
    if 'GLUCOSE' in name and vtype=='NM' and isinstance(val, (int,float)):
        if val < 50:  return ('error', f'Critical low glucose {val}')
        if val > 400: return ('error', f'Critical high glucose {val}')
    if obx.get('flag') in ('HH','LL') and obx.get('status')!='F':
        return ('warn', 'Critical flag not final')
    return None
```

## Putting It Together
```python
def validate_message(parsed):
    # parsed: output of your ADT/ORU parser with header/patient/observations
    errors, warnings = [], []

    # Datatype spot checks (example for ORU)
    hdr = parsed.get('header', {})
    if hdr.get('timestamp') is None:
        warnings.append('MSH.7 timestamp missing/invalid')

    pat = parsed.get('patient', {})
    bd = pat.get('birth_date')
    if bd and not is_date(bd):
        errors.append('PID.7 invalid date')

    for grp in parsed.get('observations', []):
        for r in grp.get('results', []):
            if r.get('value_type')=='NM' and not is_number(str(r.get('value'))):
                errors.append('OBX.5 not numeric for NM')
            out = br_critical_glucose(r)
            if out:
                (warnings if out[0]=='warn' else errors).append(out[1])

    return {'valid': not errors, 'errors': errors, 'warnings': warnings}
```

## Output: Compact Report
```python
def report(results):
    status = 'VALID' if results['valid'] else 'INVALID'
    lines = [f"Status: {status}"]
    if results['errors']:
        lines.append('Errors:'); lines += [f"- {e}" for e in results['errors']]
    if results['warnings']:
        lines.append('Warnings:'); lines += [f"- {w}" for w in results['warnings']]
    return '\n'.join(lines)
```

## Tips
- Fail fast on missing MSH; warn on non‑standard encoding unless it breaks parsing.
- Keep validation layered; skip downstream checks if syntax fails.
- Record segment/field context in messages to ease triage.
- For production, back validation with official profiles/specs or `hl7apy`.

