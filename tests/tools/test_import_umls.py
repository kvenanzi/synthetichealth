from __future__ import annotations

import gzip
from io import BytesIO
from pathlib import Path
import sys
import zipfile


PROJECT_ROOT = Path(__file__).resolve().parents[2]
TOOLS_ROOT = PROJECT_ROOT / "tools"

for candidate in (PROJECT_ROOT, TOOLS_ROOT):
    candidate_str = str(candidate)
    if candidate_str not in sys.path:
        sys.path.insert(0, candidate_str)

import import_umls


def _gzip_bytes(content: str) -> bytes:
    buffer = BytesIO()
    with gzip.GzipFile(fileobj=buffer, mode="wb") as handle:
        handle.write(content.encode("utf-8"))
    return buffer.getvalue()


def create_umls_archive(path: Path) -> None:
    mrconso = (
        "C0000005|ENG|P|L0000005|PF|S0000005|Y|A0000005|SA1|SC1|SD1|RXNORM|PT|12345|Sample Preferred Term|0|N|0|\n"
    )
    mrsty = "C0000005|T047||Disease or Syndrome|AT0000005|0|\n"

    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("2025AA/META/MRCONSO.RRF.aa.gz", _gzip_bytes(mrconso))
        archive.writestr("2025AA/META/MRSTY.RRF.gz", _gzip_bytes(mrsty))


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
    assert row.tty == "PT"
    assert row.aui == "A0000005"
    assert row.source_atom_name == "Sample Preferred Term"
