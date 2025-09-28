from __future__ import annotations

import zipfile
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[2]
TOOLS_ROOT = PROJECT_ROOT / "tools"

for candidate in (PROJECT_ROOT, TOOLS_ROOT):
    candidate_str = str(candidate)
    if candidate_str not in sys.path:
        sys.path.insert(0, candidate_str)

import import_vsac


WORKSHEET_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"


def _inline_cell(cell_ref: str, value: str) -> str:
    return (
        f"<c r=\"{cell_ref}\" t=\"inlineStr\">"
        f"<is><t>{value}</t></is>"
        "</c>"
    )


def create_vsac_workbook(path: Path) -> None:
    sheet_xml = (
        "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>"
        f"<worksheet xmlns=\"{WORKSHEET_NS}\">"
        "<sheetData>"
        "<row r=\"1\"/>"
        "<row r=\"2\">"
        + "".join(
            _inline_cell(cell_ref, header)
            for cell_ref, header in zip(
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
        )
        + "</row>"
        "<row r=\"3\">"
        + "".join(
            _inline_cell(cell_ref, value)
            for cell_ref, value in zip(
                ["A3", "B3", "C3", "D3", "E3", "F3", "G3", "H3", "I3"],
                [
                    "1.2.3.4",
                    "Sample Value Set",
                    "20250101",
                    "20250215",
                    "Focus text",
                    "ABC",
                    "Display",
                    "SNOMEDCT",
                    "2024-09",
                ],
            )
        )
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


def test_iter_vsac_rows_parses_inline_strings(tmp_path):
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    workbook_path = raw_dir / "sample.xlsx"
    create_vsac_workbook(workbook_path)

    rows = list(import_vsac.iter_vsac_rows(raw_dir))
    assert len(rows) == 1
    row = rows[0]
    assert row.value_set_oid == "1.2.3.4"
    assert row.value_set_name == "Sample Value Set"
    assert row.value_set_version == "20250101"
    assert row.release_date == "20250215"
    assert row.clinical_focus == "Focus text"
    assert row.concept_status == "Active"
    assert row.code == "ABC"
    assert row.code_system == "SNOMEDCT"
    assert row.code_system_version == "2024-09"
    assert row.display_name == "Display"
