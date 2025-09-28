from __future__ import annotations

import sys
from pathlib import Path

HELPER_DIR = Path(__file__).resolve().parent
helper_str = str(HELPER_DIR)
if helper_str not in sys.path:
    sys.path.insert(0, helper_str)

from terminology_helpers import add_project_root, write_snomed_snapshot

add_project_root()

from tools import import_snomed


def test_normalize_snomed_merges_preferred_terms(tmp_path):
    raw_dir = tmp_path / "raw"
    concept_path, description_path = write_snomed_snapshot(raw_dir)
    output_path = tmp_path / "snomed_full.csv"

    import_snomed.normalize_snomed(concept_path, description_path, output_path)

    rows = output_path.read_text(encoding="utf-8").splitlines()
    assert rows[0].startswith("snomed_id,pt_name,definition_status_id")
    assert "Sample SNOMED Concept" in rows[1]
