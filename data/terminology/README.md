# Terminology Datasets

Phase 2 introduces normalized clinical code sets sourced from the U.S. National Library of Medicine and related NCBI resources. Each subdirectory documents the authoritative download link and includes small CSV samples for local development. Larger extracts should be staged outside of version control and referenced via environment configuration.

| Code System | NCBI / NLM Reference | Local Layout |
|-------------|----------------------|--------------|
| ICD-10-CM   | https://www.cdc.gov/nchs/icd/icd10cm.htm | `icd10/icd10_conditions.csv` (seed) / `icd10/raw/` (official) |
| LOINC       | https://loinc.org/downloads/loinc | `loinc/loinc_labs.csv` (seed) / `loinc/raw/` (official) |
| SNOMED CT   | https://www.nlm.nih.gov/healthit/snomedct/us_edition.html | `snomed/snomed_conditions.csv` (seed) / `snomed/raw/` (official) |
| RxNorm      | https://www.nlm.nih.gov/research/umls/rxnorm/docs/rxnormfiles.html | `rxnorm/rxnorm_medications.csv` (seed) / `rxnorm/raw/` (official) |
| VSAC        | https://vsac.nlm.nih.gov/ | `vsac/vsac_value_sets.csv` (optional seed) / `vsac/raw/` (official value set releases) |
| UMLS 2025AA | https://www.nlm.nih.gov/research/umls/licensedcontent/umlsknowledgesources.html | `umls/umls_concepts.csv` (optional seed) / `umls/raw/` (full UMLS release) |

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

### Normalizing VSAC Value Sets

Value set exports should be flattened into `vsac/vsac_value_sets_full.csv` with one row per concept membership. The DuckDB builder expects the following columns (additional metadata is safe to include and will be ignored):

| Column | Description |
|--------|-------------|
| `value_set_oid` | VSAC OID for the value set |
| `value_set_name` | Human readable title |
| `value_set_version` | Version label from the export |
| `release_date` | Publication date for the expansion |
| `clinical_focus` | Optional summary of the value set intent |
| `concept_status` | Active/inactive flag supplied by VSAC |
| `code` | Member concept code |
| `code_system` | Coding system name (e.g., SNOMEDCT, LOINC) |
| `code_system_version` | Version of the referenced code system |
| `display_name` | Display string for the concept |

When a normalized export is unavailable, `vsac/vsac_value_sets.csv` can hold a reduced seed with the same columns. If neither file exists the DuckDB builder will create an empty `vsac_value_sets` table so downstream queries remain stable.

### Normalizing UMLS Concepts

Flatten UMLS concept extracts into `umls/umls_concepts_full.csv` with the columns below. A smaller `umls/umls_concepts.csv` seed file can be used for ad hoc experimentation when the full release is not staged locally.

| Column | Description |
|--------|-------------|
| `cui` | Concept Unique Identifier |
| `preferred_name` | Preferred term for the CUI |
| `semantic_type` | Human readable semantic type |
| `tui` | Semantic type identifier |
| `sab` | Source abbreviation (RxNorm, SNOMEDCT, etc.) |
| `code` | Source-specific code |
| `tty` | Term type supplied by the source |
| `aui` | Atom Unique Identifier |
| `source_atom_name` | Exact string provided by the source |

### Building the DuckDB Terminology Warehouse

To consolidate the normalized CSVs into a single analytic store, run:

```bash
python3 tools/build_terminology_db.py \
  --root data/terminology \
  --output data/terminology/terminology.duckdb \
  --force
```

The `--force` flag makes the rebuild explicit when an existing warehouse is present. Regenerate the database whenever new releases are imported so analytics and runtime loaders stay in sync.

Set `TERMINOLOGY_DB_PATH` (or rely on the default `data/terminology/terminology.duckdb`) so loaders can read directly from DuckDB during high-volume generation while seeds remain available for lightweight scenarios. Exporters and loaders will automatically use the consolidated tables when the environment variable points to a valid DuckDB file.
