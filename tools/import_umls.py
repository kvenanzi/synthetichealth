"""Normalize UMLS Metathesaurus exports into a loader-friendly CSV.

Usage (run inside the project virtualenv):
    python3 tools/import_umls.py \
        --raw-dir data/terminology/umls/raw \
        --output data/terminology/umls/umls_concepts_full.csv

The script streams the official UMLS release archives (``*.nlm`` containers)
to build a flattened table covering each concept atom alongside its preferred
concept name and semantic type metadata. Only a minimal subset of the release
is read (``MRCONSO`` and ``MRSTY``) so the process can execute on laptops
without unpacking the entire distribution.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import io
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, Iterator, List, Optional, Sequence, Tuple

import unicodedata
import zipfile

MRCONSO_COLUMNS = [
    "CUI",
    "LAT",
    "TS",
    "LUI",
    "STT",
    "SUI",
    "ISPREF",
    "AUI",
    "SAUI",
    "SCUI",
    "SDUI",
    "SAB",
    "TTY",
    "CODE",
    "STR",
    "SRL",
    "SUPPRESS",
    "CVF",
]

MRSTY_COLUMNS = ["CUI", "TUI", "STN", "STY", "ATUI", "CVF"]

OUTPUT_COLUMNS = [
    "cui",
    "preferred_name",
    "semantic_type",
    "tui",
    "sab",
    "code",
    "tty",
    "aui",
    "source_atom_name",
]

DEFAULT_LANGUAGES = ("ENG",)
SUPPRESS_EXCLUDE = {"O", "E"}


@dataclass
class UmlsRow:
    cui: str
    preferred_name: str
    semantic_type: str
    tui: str
    sab: str
    code: str
    tty: str
    aui: str
    source_atom_name: str

    def as_list(self) -> List[str]:
        return [
            self.cui,
            self.preferred_name,
            self.semantic_type,
            self.tui,
            self.sab,
            self.code,
            self.tty,
            self.aui,
            self.source_atom_name,
        ]


def _collect_archive_members(raw_dir: Path, base_name: str) -> List[Tuple[Path, str]]:
    members: List[Tuple[Path, str]] = []
    for archive_path in sorted(raw_dir.glob("*.nlm")):
        with zipfile.ZipFile(archive_path) as archive:
            for info in archive.infolist():
                filename = Path(info.filename).name
                if not filename.startswith(base_name):
                    continue
                if not filename.endswith(".gz"):
                    continue
                members.append((archive_path, info.filename))
    members.sort(key=lambda item: item[1])
    return members


def _iter_rrf_lines(raw_dir: Path, base_name: str) -> Iterator[str]:
    members = _collect_archive_members(raw_dir, base_name)
    if not members:
        raise FileNotFoundError(
            f"Could not locate {base_name}*.gz inside {raw_dir}. Ensure the official UMLS archives are staged."
        )

    for archive_path, member in members:
        with zipfile.ZipFile(archive_path) as archive:
            with archive.open(member) as compressed:
                with gzip.GzipFile(fileobj=compressed) as gz:
                    with io.TextIOWrapper(gz, encoding="utf-8", errors="ignore") as handle:
                        for line in handle:
                            yield line.rstrip("\n")


def _parse_rrf_line(line: str, columns: Sequence[str]) -> Dict[str, str]:
    # RRF rows terminate with a trailing delimiter; drop the final empty column
    parts = line.split("|")
    if parts and parts[-1] == "":
        parts.pop()
    if len(parts) < len(columns):
        parts.extend([""] * (len(columns) - len(parts)))
    return {column: parts[idx] for idx, column in enumerate(columns)}


def load_semantic_types(raw_dir: Path) -> Dict[str, Tuple[str, str]]:
    sty_map: Dict[str, List[str]] = defaultdict(list)
    tui_map: Dict[str, List[str]] = defaultdict(list)

    for line in _iter_rrf_lines(raw_dir, "MRSTY.RRF"):
        record = _parse_rrf_line(line, MRSTY_COLUMNS)
        cui = record.get("CUI", "").strip()
        if not cui:
            continue
        tui = record.get("TUI", "").strip()
        sty = record.get("STY", "").strip()
        if tui and tui not in tui_map[cui]:
            tui_map[cui].append(tui)
        if sty and sty not in sty_map[cui]:
            sty_map[cui].append(sty)

    semantic_types: Dict[str, Tuple[str, str]] = {}
    for cui in sty_map.keys() | tui_map.keys():
        sty_value = "; ".join(sty_map.get(cui, []))
        tui_value = "; ".join(tui_map.get(cui, []))
        semantic_types[cui] = (sty_value, tui_value)
    return semantic_types


def _preferred_score(record: Dict[str, str]) -> int:
    score = 0
    if record.get("LAT") == "ENG":
        score += 8
    if record.get("TS") == "P":
        score += 4
    if record.get("STT") in {"PF", "P"}:
        score += 2
    if record.get("ISPREF") == "Y":
        score += 1
    return score


def compute_preferred_names(raw_dir: Path, languages: Sequence[str]) -> Dict[str, str]:
    preferred: Dict[str, Tuple[int, str]] = {}

    for line in _iter_rrf_lines(raw_dir, "MRCONSO.RRF"):
        record = _parse_rrf_line(line, MRCONSO_COLUMNS)
        cui = record.get("CUI", "").strip()
        if not cui:
            continue
        if languages and record.get("LAT") not in languages:
            continue

        candidate = unicodedata.normalize("NFKC", record.get("STR", "")).strip()
        if not candidate:
            continue

        score = _preferred_score(record)
        current = preferred.get(cui)
        if current is None or score > current[0]:
            preferred[cui] = (score, candidate)
    return {cui: value for cui, (score, value) in preferred.items()}


def iter_umls_rows(
    raw_dir: Path,
    *,
    languages: Sequence[str],
    sab_whitelist: Optional[Sequence[str]] = None,
) -> Iterator[UmlsRow]:
    sem_types = load_semantic_types(raw_dir)
    preferred = compute_preferred_names(raw_dir, languages)

    sab_filter = {sab.upper() for sab in sab_whitelist} if sab_whitelist else None

    for line in _iter_rrf_lines(raw_dir, "MRCONSO.RRF"):
        record = _parse_rrf_line(line, MRCONSO_COLUMNS)

        cui = record.get("CUI", "").strip()
        if not cui:
            continue
        if record.get("SUPPRESS") in SUPPRESS_EXCLUDE:
            continue
        if languages and record.get("LAT") not in languages:
            continue

        sab = record.get("SAB", "").strip()
        if sab_filter and sab.upper() not in sab_filter:
            continue

        semantic_type, tui = sem_types.get(cui, ("", ""))
        preferred_name = preferred.get(cui, "")
        if not preferred_name:
            preferred_name = unicodedata.normalize("NFKC", record.get("STR", "")).strip()

        yield UmlsRow(
            cui=cui,
            preferred_name=preferred_name,
            semantic_type=semantic_type,
            tui=tui,
            sab=sab,
            code=record.get("CODE", "").strip(),
            tty=record.get("TTY", "").strip(),
            aui=record.get("AUI", "").strip(),
            source_atom_name=unicodedata.normalize("NFKC", record.get("STR", "").strip()),
        )


def write_rows(rows: Iterable[UmlsRow], output_path: Path) -> bool:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(OUTPUT_COLUMNS)
        wrote_any = False
        for row in rows:
            writer.writerow(row.as_list())
            wrote_any = True
    return wrote_any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Normalize UMLS MRCONSO/MRSTY tables")
    parser.add_argument(
        "--raw-dir",
        type=Path,
        default=Path("data/terminology/umls/raw"),
        help="Directory containing *.nlm UMLS release archives",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/terminology/umls/umls_concepts_full.csv"),
        help="Destination for the flattened CSV",
    )
    parser.add_argument(
        "--languages",
        nargs="*",
        default=list(DEFAULT_LANGUAGES),
        help="Language codes to include (defaults to ENG). Use '--languages ALL' to include every language.",
    )
    parser.add_argument(
        "--sab",
        nargs="*",
        help="Optional list of source abbreviations (SAB) to retain. If omitted all SABs are included.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    languages = [] if args.languages == ["ALL"] else args.languages
    if languages:
        languages = [lang.upper() for lang in languages]

    wrote = write_rows(
        iter_umls_rows(
            args.raw_dir,
            languages=languages,
            sab_whitelist=args.sab,
        ),
        args.output,
    )
    if not wrote:
        raise SystemExit("No UMLS rows written. Check the raw directory or adjust language / SAB filters.")

    print(f"Wrote normalized UMLS concepts: {args.output}")


if __name__ == "__main__":
    main()
