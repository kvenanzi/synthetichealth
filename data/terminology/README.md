# Terminology Datasets

Phase 2 introduces normalized clinical code sets sourced from the U.S. National Library of Medicine and related NCBI resources. Each subdirectory documents the authoritative download link and includes small CSV samples for local development. Larger extracts should be staged outside of version control and referenced via environment configuration.

| Code System | NCBI / NLM Reference | Local Layout |
|-------------|----------------------|--------------|
| ICD-10-CM   | https://www.cdc.gov/nchs/icd/icd10cm.htm | `icd10/icd10_conditions.csv` (seed) / `icd10/raw/` (official) |
| LOINC       | https://loinc.org/downloads/loinc | `loinc/loinc_labs.csv` (seed) / `loinc/raw/` (official) |
| SNOMED CT   | https://www.nlm.nih.gov/healthit/snomedct/us_edition.html | `snomed/snomed_conditions.csv` (seed) / `snomed/raw/` (official) |
| RxNorm      | https://www.nlm.nih.gov/research/umls/rxnorm/docs/rxnormfiles.html | `rxnorm/rxnorm_medications.csv` (seed) / `rxnorm/raw/` (official) |
| VSAC        | https://vsac.nlm.nih.gov/ | `vsac/raw/` (official value set releases) |

> **Note:** Full distributions may require license or UMLS credentials. The loader utilities added in Phase 2 accept alternate filesystem paths or database connections for production-scale vocabularies.

### Normalizing Official LOINC Tables

After extracting the official LOINC zip into `loinc/raw/`, generate a normalized table aligned with the loader schema via:

```bash
python tools/import_loinc.py \
  --raw data/terminology/loinc/raw/LoincTable/Loinc.csv \
  --output data/terminology/loinc/loinc_full.csv
```

`load_loinc_labs` will automatically prefer `loinc_full.csv` when it exists while retaining the lightweight seed file for quick tests.

### Normalizing Official ICD-10-CM Tables

After extracting `icd10cm-order-YYYY.txt` into `icd10/raw/`, run:

```bash
python3 tools/import_icd10.py \
  --raw data/terminology/icd10/raw/icd10cm-order-2026.txt \
  --output data/terminology/icd10/icd10_full.csv
```

`load_icd10_conditions` will automatically prefer `icd10_full.csv` when present.

Normalization scripts for SNOMED CT and RxNorm will follow the same pattern; until then, keep their full distributions under the respective `raw/` folders while the loaders continue to rely on the committed seed tables.
