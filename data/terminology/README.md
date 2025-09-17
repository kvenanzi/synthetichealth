# Terminology Datasets

Phase 2 introduces normalized clinical code sets sourced from the U.S. National Library of Medicine and related NCBI resources. Each subdirectory documents the authoritative download link and includes small CSV samples for local development. Larger extracts should be staged outside of version control and referenced via environment configuration.

| Code System | NCBI / NLM Reference | Local Layout |
|-------------|----------------------|--------------|
| ICD-10-CM   | https://www.cdc.gov/nchs/icd/icd10cm.htm | `icd10/icd10_conditions.csv` |
| LOINC       | https://loinc.org/downloads/loinc | `loinc/loinc_labs.csv` |
| SNOMED CT   | https://www.nlm.nih.gov/healthit/snomedct/us_edition.html | `snomed/snomed_conditions.csv` |
| RxNorm      | https://www.nlm.nih.gov/research/umls/rxnorm/docs/rxnormfiles.html | `rxnorm/rxnorm_medications.csv` |

> **Note:** Full distributions may require license or UMLS credentials. The loader utilities added in Phase 2 accept alternate filesystem paths or database connections for production-scale vocabularies.
