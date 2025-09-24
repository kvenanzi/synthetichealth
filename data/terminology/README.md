# Terminology Datasets

Phase 2 introduces normalized clinical code sets sourced from the U.S. National Library of Medicine and related NCBI resources. Each subdirectory documents the authoritative download link and includes small CSV samples for local development. Larger extracts should be staged outside of version control and referenced via environment configuration.

| Code System | NCBI / NLM Reference | Local Layout |
|-------------|----------------------|--------------|
| ICD-10-CM   | https://www.cdc.gov/nchs/icd/icd10cm.htm | `icd10/icd10_conditions.csv` (seed) / `icd10/raw/` (official) |
| LOINC       | https://loinc.org/downloads/loinc | `loinc/loinc_labs.csv` (seed) / `loinc/raw/` (official) |
| SNOMED CT   | https://www.nlm.nih.gov/healthit/snomedct/us_edition.html | `snomed/snomed_conditions.csv` (seed) / `snomed/raw/` (official) |
| RxNorm      | https://www.nlm.nih.gov/research/umls/rxnorm/docs/rxnormfiles.html | `rxnorm/rxnorm_medications.csv` (seed) / `rxnorm/raw/` (official) |
| VSAC        | https://vsac.nlm.nih.gov/ | `vsac/raw/` (official value set releases) |
| UMLS 2025AA | https://www.nlm.nih.gov/research/umls/licensedcontent/umlsknowledgesources.html | `umls/raw/` (full UMLS release) |

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

### Normalizing Official SNOMED CT Tables

After extracting the SNOMED CT US Managed Service snapshot into `snomed/raw/`, run:

```bash
python3 tools/import_snomed.py \
  --concept data/terminology/snomed/raw/SnomedCT_ManagedServiceUS_PRODUCTION_US1000124_20250901T120000Z/Snapshot/Terminology/sct2_Concept_Snapshot_US1000124_20250901.txt \
  --description data/terminology/snomed/raw/SnomedCT_ManagedServiceUS_PRODUCTION_US1000124_20250901T120000Z/Snapshot/Terminology/sct2_Description_Snapshot-en_US1000124_20250901.txt \
  --output data/terminology/snomed/snomed_full.csv
```

`load_snomed_conditions` will automatically prefer `snomed_full.csv` when present.

### Normalizing Official RxNorm Tables

After extracting the RxNorm full release into `rxnorm/raw/`, run:

```bash
python3 tools/import_rxnorm.py \
  --rxnconso data/terminology/rxnorm/raw/rrf/RXNCONSO.RRF \
  --output data/terminology/rxnorm/rxnorm_full.csv
```

`load_rxnorm_medications` will automatically prefer `rxnorm_full.csv` when present.

### Building the DuckDB Terminology Warehouse

To consolidate the normalized CSVs into a single analytic store, run:

```bash
python3 tools/build_terminology_db.py \
  --root data/terminology \
  --output data/terminology/terminology.duckdb
```

Set `TERMINOLOGY_DB_PATH` (or rely on the default `data/terminology/terminology.duckdb`) so loaders can read directly from DuckDB during high-volume generation while seeds remain available for lightweight scenarios.

Normalization scripts for optional VSAC subsets will follow the same pattern; until then, keep their full distributions under the respective `raw/` folders while the loaders continue to rely on the committed seed tables.
