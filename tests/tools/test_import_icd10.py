from __future__ import annotations

import sys
from pathlib import Path

HELPER_DIR = Path(__file__).resolve().parent
helper_str = str(HELPER_DIR)
if helper_str not in sys.path:
    sys.path.insert(0, helper_str)

import csv

from terminology_helpers import add_project_root, write_icd10_order_file

add_project_root()

from tools import import_icd10


def test_normalize_icd10_generates_expected_columns(tmp_path):
    raw_path = write_icd10_order_file(tmp_path / "icd10cm-order-2026.txt")
    output_path = tmp_path / "icd10_full.csv"

    import_icd10.normalize_icd10(raw_path, output_path)

    with output_path.open(encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        row = next(reader)
    assert row["code"] == "A00"
    assert row["description"].startswith("Cholera")
