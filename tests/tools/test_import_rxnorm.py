from __future__ import annotations

import sys
from pathlib import Path

HELPER_DIR = Path(__file__).resolve().parent
helper_str = str(HELPER_DIR)
if helper_str not in sys.path:
    sys.path.insert(0, helper_str)

from terminology_helpers import add_project_root, write_rxnorm_rrf

add_project_root()

from tools import import_rxnorm


def test_normalize_rxnorm_filters_preferred_terms(tmp_path):
    raw_path = write_rxnorm_rrf(tmp_path / "RXNCONSO.RRF")
    output_path = tmp_path / "rxnorm_full.csv"

    import_rxnorm.normalize_rxnorm(raw_path, output_path)

    lines = output_path.read_text(encoding="utf-8").splitlines()
    assert lines[0].startswith("rxnorm_cui,tty,ingredient_name")
    assert "Sample RxNorm Drug" in lines[1]
