# Synthetic Data Primers (New Series)

These primers are concise, task‑oriented guides for reading, understanding, and working with the synthetic healthcare data produced by this repo — covering FHIR bundles, HL7 v2 (ADT/ORU), validation strategies, and VistA MUMPS globals.

Primers:
- FHIR: `fhir_bundle_quickstart.md`
- HL7 ADT: `hl7_adt_quickstart.md`
- HL7 ORU: `hl7_oru_quickstart.md`
- HL7 Validation: `hl7_validation_playbook.md`
- VistA MUMPS: `vista_mumps_quickstart.md`

Notes:
- Examples assume Python 3.10+.
- Where possible, examples reference repo sample data (e.g., `fhir_bundle.json`).
- Keep parsing robust: check `resourceType`, segment presence, and handle missing fields.

