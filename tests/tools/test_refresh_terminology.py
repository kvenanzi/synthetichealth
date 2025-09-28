from __future__ import annotations

import sys
from pathlib import Path

HELPER_DIR = Path(__file__).resolve().parent
helper_str = str(HELPER_DIR)
if helper_str not in sys.path:
    sys.path.insert(0, helper_str)

from terminology_helpers import (
    add_project_root,
    create_umls_archive,
    create_vsac_workbook,
    write_icd10_order_file,
    write_rxnorm_rrf,
    write_snomed_snapshot,
)

add_project_root()

from tools.refresh_terminology import refresh_terminology


def test_refresh_terminology_normalizes_available_sources(tmp_path):
    root = tmp_path / "terminology"

    # ICD-10
    write_icd10_order_file(root / "icd10/raw/icd10cm-order-2026.txt")

    # SNOMED snapshot structure
    snomed_snapshot = root / "snomed/raw/SnomedCT_Test/Snapshot/Terminology"
    write_snomed_snapshot(snomed_snapshot)

    # RxNorm
    write_rxnorm_rrf(root / "rxnorm/raw/RXNCONSO.RRF")

    # VSAC workbook
    vsac_raw = root / "vsac/raw"
    vsac_raw.mkdir(parents=True, exist_ok=True)
    create_vsac_workbook(vsac_raw / "valueset.xlsx")

    # UMLS archives
    umls_raw = root / "umls/raw"
    umls_raw.mkdir(parents=True, exist_ok=True)
    create_umls_archive(umls_raw / "2025aa-1-meta.nlm")

    summary = refresh_terminology(root, rebuild_db=False)

    assert summary["icd10"].startswith("normalized")
    assert summary["snomed"].startswith("normalized")
    assert summary["rxnorm"].startswith("normalized")
    assert summary["vsac"].startswith("normalized")
    assert summary["umls"].startswith("normalized")

    assert (root / "icd10/icd10_full.csv").exists()
    assert (root / "snomed/snomed_full.csv").exists()
    assert (root / "rxnorm/rxnorm_full.csv").exists()
    assert (root / "vsac/vsac_value_sets_full.csv").exists()
    assert (root / "umls/umls_concepts_full.csv").exists()
