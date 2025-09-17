# Terminology Datasets

Phase 2 introduces normalized clinical code sets sourced from the U.S. National Library of Medicine and related NCBI resources. Each subdirectory documents the authoritative download link and includes small CSV samples for local development. Larger extracts should be staged outside of version control and referenced via environment configuration.

| Code System | NCBI / NLM Reference | Local Layout |
|-------------|----------------------|--------------|
| ICD-10-CM   | https://www.ncbi.nlm.nih.gov/pmc/articles/PMC/ (CMS code set landing via NLM) | `icd10/icd10_conditions.csv` |
| LOINC       | https://www.ncbi.nlm.nih.gov/pmc/?term=LOINC | `loinc/loinc_labs.csv` |
| SNOMED CT   | https://www.ncbi.nlm.nih.gov/pmc/?term=SNOMED+CT | `snomed/snomed_conditions.csv` |
| RxNorm      | https://www.ncbi.nlm.nih.gov/books/NBK547852/ | `rxnorm/rxnorm_medications.csv` |

> **Note:** Full distributions may require license or UMLS credentials. The loader utilities added in Phase 2 accept alternate filesystem paths or database connections for production-scale vocabularies.
