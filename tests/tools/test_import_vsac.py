from __future__ import annotations

import sys
from pathlib import Path

HELPER_DIR = Path(__file__).resolve().parent
helper_str = str(HELPER_DIR)
if helper_str not in sys.path:
    sys.path.insert(0, helper_str)

from terminology_helpers import add_project_root, create_vsac_workbook

add_project_root()

from tools import import_vsac


def test_iter_vsac_rows_parses_inline_strings(tmp_path):
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    workbook_path = raw_dir / "sample.xlsx"
    create_vsac_workbook(workbook_path)

    rows = list(import_vsac.iter_vsac_rows(raw_dir))
    assert len(rows) == 1
    row = rows[0]
    assert row.value_set_oid == "2.16.840.1.113883.3.526.3.1567"
    assert row.value_set_name == "Adolescent Depression Medications"
    assert row.value_set_version == "20210220"
    assert row.release_date == "20250508"
    assert row.clinical_focus.startswith("Concepts for adolescent depression")
    assert row.concept_status == "Active"
    assert row.code == "2951-2"
    assert row.code_system == "LOINC"
    assert row.code_system_version == "2025-01"
    assert row.display_name.startswith("Sodium")
