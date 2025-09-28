"""Shared helpers for terminology import tests."""
from __future__ import annotations

import gzip
from io import BytesIO
from pathlib import Path
import zipfile


def add_project_root() -> Path:
    """Ensure the repository root is on ``sys.path`` for importer tests."""

    import sys

    project_root = Path(__file__).resolve().parents[2]
    root_str = str(project_root)
    if root_str not in sys.path:
        sys.path.insert(0, root_str)
    return project_root


def create_vsac_workbook(path: Path) -> None:
    """Write a minimal VSAC Excel workbook containing one value set member."""

    worksheet_ns = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"

    def inline_cell(cell_ref: str, value: str) -> str:
        return (
            f"<c r=\"{cell_ref}\" t=\"inlineStr\">"
            f"<is><t>{value}</t></is>"
            "</c>"
        )

    header_cells = zip(
        ["A2", "B2", "C2", "D2", "E2", "F2", "G2", "H2", "I2"],
        [
            "Value Set OID",
            "Value Set Name",
            "Definition Version",
            "Expansion ID",
            "Purpose: Clinical Focus",
            "Code",
            "Description",
            "Code System",
            "Code System Version",
        ],
    )

    row_cells = zip(
        ["A3", "B3", "C3", "D3", "E3", "F3", "G3", "H3", "I3"],
        [
            "2.16.840.1.113883.3.526.3.1567",
            "Adolescent Depression Medications",
            "20210220",
            "20250508",
            "Concepts for adolescent depression management",
            "2951-2",
            "Sodium [Moles/volume] in Serum or Plasma",
            "LOINC",
            "2025-01",
        ],
    )

    sheet_xml = (
        "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>"
        f"<worksheet xmlns=\"{worksheet_ns}\">"
        "<sheetData>"
        "<row r=\"1\"/>"
        "<row r=\"2\">"
        + "".join(inline_cell(ref, val) for ref, val in header_cells)
        + "</row>"
        "<row r=\"3\">"
        + "".join(inline_cell(ref, val) for ref, val in row_cells)
        + "</row>"
        "</sheetData>"
        "</worksheet>"
    )

    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(
            "[Content_Types].xml",
            (
                "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>"
                "<Types xmlns=\"http://schemas.openxmlformats.org/package/2006/content-types\">"
                "<Default Extension=\"rels\" ContentType=\"application/vnd.openxmlformats-package.relationships+xml\"/>"
                "<Default Extension=\"xml\" ContentType=\"application/xml\"/>"
                "<Override PartName=\"/xl/workbook.xml\" ContentType=\"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml\"/>"
                "<Override PartName=\"/xl/worksheets/sheet1.xml\" ContentType=\"application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml\"/>"
                "</Types>"
            ),
        )
        archive.writestr(
            "_rels/.rels",
            (
                "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>"
                "<Relationships xmlns=\"http://schemas.openxmlformats.org/package/2006/relationships\">"
                "<Relationship Id=\"rId1\" Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument\" Target=\"xl/workbook.xml\"/>"
                "</Relationships>"
            ),
        )
        archive.writestr(
            "xl/workbook.xml",
            (
                "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>"
                "<workbook xmlns=\"http://schemas.openxmlformats.org/spreadsheetml/2006/main\" "
                "xmlns:r=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships\">"
                "<sheets><sheet name=\"Sheet1\" sheetId=\"1\" r:id=\"rId1\"/></sheets>"
                "</workbook>"
            ),
        )
        archive.writestr(
            "xl/_rels/workbook.xml.rels",
            (
                "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>"
                "<Relationships xmlns=\"http://schemas.openxmlformats.org/package/2006/relationships\">"
                "<Relationship Id=\"rId1\" Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet\" Target=\"worksheets/sheet1.xml\"/>"
                "</Relationships>"
            ),
        )
        archive.writestr("xl/worksheets/sheet1.xml", sheet_xml)


def create_umls_archive(path: Path) -> None:
    """Write a gzipped UMLS archive containing minimal MRCONSO/MRSTY segments."""

    mrconso = (
        "C0000005|ENG|P|L0000005|PF|S0000005|Y|A0000005|SA1|SC1|SD1|RXNORM|IN|12345|Sample Preferred Term|0|N|0|\n"
    )
    mrsty = "C0000005|T047||Disease or Syndrome|AT0000005|0|\n"

    def gzip_bytes(content: str) -> bytes:
        buffer = BytesIO()
        with gzip.GzipFile(fileobj=buffer, mode="wb") as handle:
            handle.write(content.encode("utf-8"))
        return buffer.getvalue()

    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("2025AA/META/MRCONSO.RRF.aa.gz", gzip_bytes(mrconso))
        archive.writestr("2025AA/META/MRSTY.RRF.gz", gzip_bytes(mrsty))


def write_icd10_order_file(path: Path) -> Path:
    """Generate a small ICD-10 order file following the fixed-width layout."""

    path.parent.mkdir(parents=True, exist_ok=True)
    order = "00001"
    code = "A00"
    level = "0"
    short_description = "Cholera"
    long_description = "Cholera due to Vibrio cholerae"
    line = f"{order} {code:<7}{level:<3}{short_description:<60}{long_description}\n"
    path.write_text(line, encoding="utf-8")
    return path


def write_snomed_snapshot(raw_dir: Path) -> tuple[Path, Path]:
    """Create minimal SNOMED concept and description snapshot files."""

    concept_header = "\t".join(
        [
            "id",
            "effectiveTime",
            "active",
            "moduleId",
            "definitionStatusId",
        ]
    )
    concept_row = "\t".join(
        [
            "123456",
            "20250901",
            "1",
            "900000000000207008",
            "900000000000073002",
        ]
    )

    description_header = "\t".join(
        [
            "id",
            "effectiveTime",
            "active",
            "moduleId",
            "conceptId",
            "languageCode",
            "typeId",
            "term",
            "caseSignificanceId",
        ]
    )
    description_row = "\t".join(
        [
            "999999",
            "20250901",
            "1",
            "900000000000207008",
            "123456",
            "en",
            "900000000000013009",
            "Sample SNOMED Concept",
            "900000000000448009",
        ]
    )

    concept_path = raw_dir / "sct2_Concept_Snapshot_Test.txt"
    description_path = raw_dir / "sct2_Description_Snapshot-en_Test.txt"
    concept_path.parent.mkdir(parents=True, exist_ok=True)
    concept_path.write_text(f"{concept_header}\n{concept_row}\n", encoding="utf-8")
    description_path.write_text(f"{description_header}\n{description_row}\n", encoding="utf-8")
    return concept_path, description_path


def write_rxnorm_rrf(path: Path) -> Path:
    """Create a minimal RXNCONSO.RRF file containing one preferred RxNorm concept."""

    path.parent.mkdir(parents=True, exist_ok=True)
    row = [
        "12345",  # RXCUI
        "ENG",
        "P",
        "L12345",
        "PF",
        "S12345",
        "Y",
        "A12345",
        "SA12345",
        "SC12345",
        "SD12345",
        "RXNORM",
        "IN",
        "12345",
        "Sample RxNorm Drug",
        "0",
        "N",
        "0",
    ]
    line = "|".join(row) + "|\n"
    path.write_text(line, encoding="utf-8")
    return path


__all__ = [
    "add_project_root",
    "create_vsac_workbook",
    "create_umls_archive",
    "write_icd10_order_file",
    "write_snomed_snapshot",
    "write_rxnorm_rrf",
]
