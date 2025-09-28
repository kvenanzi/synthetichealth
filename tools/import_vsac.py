"""Normalize VSAC value set Excel exports into a loader-friendly CSV.

Usage (run inside the project virtualenv):
    python3 tools/import_vsac.py \
        --raw-dir data/terminology/vsac/raw \
        --output data/terminology/vsac/vsac_value_sets_full.csv

The script scans a directory of VSAC CMS Excel workbooks (e.g., the eCQM
Update bundles) and flattens all value set members into a single CSV with the
columns expected by :mod:`tools.build_terminology_db`.

The parser operates directly on the OOXML files to avoid extra Excel
dependencies (`openpyxl`, `fastexcel`, etc.) in constrained environments. Only
cells present in the workbooks are read; empty rows and non-value-set metadata
tabs are skipped automatically.
"""
from __future__ import annotations

import argparse
import csv
import sys
import unicodedata
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, Iterator, List, Optional, Sequence, Tuple

XL_NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"


REQUIRED_COLUMNS = [
    "value_set_oid",
    "value_set_name",
    "value_set_version",
    "release_date",
    "clinical_focus",
    "concept_status",
    "code",
    "code_system",
    "code_system_version",
    "display_name",
]


@dataclass
class VsacRow:
    value_set_oid: str
    value_set_name: str
    value_set_version: str
    release_date: str
    clinical_focus: str
    concept_status: str
    code: str
    code_system: str
    code_system_version: str
    display_name: str

    def as_list(self) -> List[str]:
        return [
            self.value_set_oid,
            self.value_set_name,
            self.value_set_version,
            self.release_date,
            self.clinical_focus,
            self.concept_status,
            self.code,
            self.code_system,
            self.code_system_version,
            self.display_name,
        ]


def load_shared_strings(archive: zipfile.ZipFile) -> List[str]:
    import xml.etree.ElementTree as ET

    if "xl/sharedStrings.xml" not in archive.namelist():
        return []
    with archive.open("xl/sharedStrings.xml") as handle:
        root = ET.parse(handle).getroot()

    strings: List[str] = []
    for si in root.findall(f"{XL_NS}si"):
        # Shared strings can contain multiple <t> nodes (rich text). Concatenate
        # each fragment to preserve the rendered value.
        fragments = [
            node.text or ""
            for node in si.findall(f".//{XL_NS}t")
        ]
        strings.append("".join(fragments))
    return strings


def _column_index(cell_reference: str) -> int:
    # Cell references start with letters (column) followed by row digits.
    column_part = "".join(ch for ch in cell_reference if ch.isalpha()).upper()
    index = 0
    for char in column_part:
        index = index * 26 + (ord(char) - ord("A") + 1)
    return index - 1


def _cell_value(cell, strings: Sequence[str]) -> str:
    import xml.etree.ElementTree as ET

    value_node = cell.find(f"{XL_NS}v")
    if value_node is not None:
        value_text = value_node.text or ""
        if cell.attrib.get("t") == "s":
            try:
                return strings[int(value_text)]
            except (IndexError, ValueError):
                return ""
        return value_text

    inline_node = cell.find(f"{XL_NS}is")
    if inline_node is not None:
        fragments = [
            node.text or ""
            for node in inline_node.findall(f".//{XL_NS}t")
        ]
        return "".join(fragments)
    return ""


def _row_values(row, strings: Sequence[str]) -> List[str]:
    cells: Dict[int, str] = {}
    max_index = -1
    for cell in row.findall(f"{XL_NS}c"):
        ref = cell.attrib.get("r")
        if not ref:
            continue
        idx = _column_index(ref)
        cells[idx] = _cell_value(cell, strings)
        if idx > max_index:
            max_index = idx
    if max_index < 0:
        return []
    return [cells.get(i, "") for i in range(max_index + 1)]


def iter_sheet_rows(archive: zipfile.ZipFile, sheet_path: str, strings: Sequence[str]) -> Iterator[List[str]]:
    import xml.etree.ElementTree as ET

    with archive.open(f"xl/{sheet_path}") as handle:
        root = ET.parse(handle).getroot()

    sheet_data = root.find(f"{XL_NS}sheetData")
    if sheet_data is None:
        return

    for row in sheet_data.findall(f"{XL_NS}row"):
        values = _row_values(row, strings)
        if values:
            yield values


def iter_workbook_records(workbook_path: Path) -> Iterator[Dict[str, str]]:
    with zipfile.ZipFile(workbook_path) as archive:
        strings = load_shared_strings(archive)

        import xml.etree.ElementTree as ET

        with archive.open("xl/workbook.xml") as handle:
            workbook_root = ET.parse(handle).getroot()

        relations: Dict[str, str] = {}
        with archive.open("xl/_rels/workbook.xml.rels") as handle:
            rels_root = ET.parse(handle).getroot()
        for rel in rels_root:
            rel_id = rel.attrib.get("Id")
            target = rel.attrib.get("Target")
            if rel_id and target:
                relations[rel_id] = target

        sheets = workbook_root.find(f"{XL_NS}sheets")
        if sheets is None:
            return

        for sheet in sheets.findall(f"{XL_NS}sheet"):
            rel_id = sheet.attrib.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id")
            if not rel_id:
                continue
            target = relations.get(rel_id)
            if not target:
                continue

            header: Optional[List[str]] = None
            for values in iter_sheet_rows(archive, target, strings):
                normalized = [unicodedata.normalize("NFKC", value).strip() for value in values]
                if not header:
                    if "Value Set OID" in normalized and "Code" in normalized:
                        header = normalized
                    continue
                if not any(normalized):
                    continue
                if header:
                    record = {header[i]: normalized[i] for i in range(min(len(header), len(normalized)))}
                    yield record


def _coalesce(record: Dict[str, str], candidates: Sequence[str]) -> str:
    for key in candidates:
        value = record.get(key)
        if value:
            return value
    return ""


def normalize_record(record: Dict[str, str]) -> Optional[VsacRow]:
    oid = _coalesce(record, ["Value Set OID", "Value Set Oid", "OID"]).strip()
    code = _coalesce(record, ["Code", "Concept Code", "Member Code"]).strip()
    if not oid or not code:
        return None

    return VsacRow(
        value_set_oid=oid,
        value_set_name=_coalesce(record, ["Value Set Name", "Name"]).strip(),
        value_set_version=_coalesce(record, ["Definition Version", "Value Set Version", "Version"]).strip(),
        release_date=_coalesce(record, ["Expansion ID", "Release Date", "Expansion Version"]).strip(),
        clinical_focus=_coalesce(
            record,
            [
                "Purpose: Clinical Focus",
                "Clinical Focus",
                "Clinical Focus Description",
            ],
        ).strip(),
        concept_status=_coalesce(record, ["Concept Status", "Status"]).strip() or "Active",
        code=code,
        code_system=_coalesce(record, ["Code System", "CodeSystem", "Code System Name"]).strip(),
        code_system_version=_coalesce(
            record,
            ["Code System Version", "Code System Version Number", "Version Number"],
        ).strip(),
        display_name=_coalesce(record, ["Description", "Display Name", "Concept Name"]).strip(),
    )


def iter_vsac_rows(raw_dir: Path) -> Iterator[VsacRow]:
    workbooks = sorted(path for path in raw_dir.glob("*.xlsx") if path.is_file())
    for workbook in workbooks:
        if workbook.name.endswith(".crdownload"):
            continue
        for record in iter_workbook_records(workbook):
            row = normalize_record(record)
            if row:
                yield row


def write_rows(rows: Iterable[VsacRow], output_path: Path) -> bool:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(REQUIRED_COLUMNS)
        wrote_any = False
        for row in rows:
            writer.writerow(row.as_list())
            wrote_any = True
    return wrote_any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Normalize VSAC CMS value set exports")
    parser.add_argument(
        "--raw-dir",
        type=Path,
        default=Path("data/terminology/vsac/raw"),
        help="Directory containing VSAC Excel workbooks",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/terminology/vsac/vsac_value_sets_full.csv"),
        help="Destination for the normalized CSV",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    wrote = write_rows(iter_vsac_rows(args.raw_dir), args.output)
    if not wrote:
        raise SystemExit(
            "No VSAC value set members found. Ensure the raw directory contains the eCQM workbooks."
        )
    print(f"Wrote normalized VSAC value sets: {args.output}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(1)
