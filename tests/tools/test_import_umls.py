from __future__ import annotations

import sys
from pathlib import Path

HELPER_DIR = Path(__file__).resolve().parent
helper_str = str(HELPER_DIR)
if helper_str not in sys.path:
    sys.path.insert(0, helper_str)

from terminology_helpers import add_project_root, create_umls_archive

add_project_root()

from tools import import_umls


def test_iter_umls_rows_streams_single_archive(tmp_path):
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    archive_path = raw_dir / "sample.nlm"
    create_umls_archive(archive_path)

    rows = list(
        import_umls.iter_umls_rows(
            raw_dir,
            languages=["ENG"],
            sab_whitelist=["RXNORM"],
        )
    )
    assert len(rows) == 1
    row = rows[0]
    assert row.cui == "C0000005"
    assert row.preferred_name == "Sample Preferred Term"
    assert row.semantic_type == "Disease or Syndrome"
    assert row.tui == "T047"
    assert row.sab == "RXNORM"
    assert row.code == "12345"
    assert row.tty == "IN"
    assert row.aui == "A0000005"
    assert row.source_atom_name == "Sample Preferred Term"
