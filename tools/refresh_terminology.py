"""Orchestrate terminology normalization across all code systems.

This helper scans the canonical ``data/terminology`` layout, runs the
appropriate import utilities when raw source files are present, and optionally
rebuilds the DuckDB warehouse in a single command.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Dict, Iterable, Optional, Sequence

# Allow running the script via ``python tools/refresh_terminology.py`` by ensuring
# the project root is available on sys.path.
if __package__ is None or __package__ == "":
    PROJECT_ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(PROJECT_ROOT))

from tools import import_icd10, import_rxnorm, import_snomed, import_umls, import_vsac


DEFAULT_ROOT = Path("data/terminology")


def _find_first(directory: Path, patterns: Iterable[str]) -> Optional[Path]:
    for pattern in patterns:
        matches = sorted(directory.glob(pattern))
        if matches:
            return matches[0]
    return None


def refresh_terminology(
    root: Path,
    *,
    rebuild_db: bool = False,
    output_db: Optional[Path] = None,
    force: bool = False,
    umls_languages: Optional[Sequence[str]] = None,
    umls_sab: Optional[Sequence[str]] = None,
) -> Dict[str, str]:
    """Normalize all staged terminology sources under ``root``.

    Returns a mapping from code system name to a human-readable status string.
    """

    root = root.resolve()
    summary: Dict[str, str] = {}

    # ICD-10
    icd_root = root / "icd10"
    icd_raw = icd_root / "raw"
    order_file = _find_first(icd_raw, ["icd10cm-order-*.txt"])
    if order_file:
        output = icd_root / "icd10_full.csv"
        import_icd10.normalize_icd10(order_file, output)
        summary["icd10"] = f"normalized ({order_file.name})"
    else:
        summary["icd10"] = "skipped (no icd10cm-order-*.txt found)"

    # SNOMED
    snomed_root = root / "snomed"
    snomed_raw = snomed_root / "raw"
    concept_path = _find_first(
        snomed_raw,
        ["**/Snapshot/Terminology/sct2_Concept_Snapshot*.txt", "sct2_Concept_Snapshot*.txt"],
    )
    description_path = _find_first(
        snomed_raw,
        ["**/Snapshot/Terminology/sct2_Description_Snapshot*.txt", "sct2_Description_Snapshot*.txt"],
    )
    if concept_path and description_path:
        output = snomed_root / "snomed_full.csv"
        import_snomed.normalize_snomed(concept_path, description_path, output)
        summary["snomed"] = "normalized"
    else:
        summary["snomed"] = "skipped (concept/description snapshots not found)"

    # RxNorm
    rxnorm_root = root / "rxnorm"
    rxnorm_raw = rxnorm_root / "raw"
    rxnconso = _find_first(rxnorm_raw, ["**/RXNCONSO.RRF", "RXNCONSO.RRF"])
    if rxnconso:
        output = rxnorm_root / "rxnorm_full.csv"
        import_rxnorm.normalize_rxnorm(rxnconso, output)
        summary["rxnorm"] = "normalized"
    else:
        summary["rxnorm"] = "skipped (RXNCONSO.RRF not found)"

    # VSAC
    vsac_root = root / "vsac"
    vsac_raw = vsac_root / "raw"
    workbook_paths = sorted(vsac_raw.glob("*.xlsx"))
    if workbook_paths:
        output = vsac_root / "vsac_value_sets_full.csv"
        wrote = import_vsac.write_rows(import_vsac.iter_vsac_rows(vsac_raw), output)
        summary["vsac"] = "normalized" if wrote else "skipped (no value set members parsed)"
    else:
        summary["vsac"] = "skipped (no .xlsx exports found)"

    # UMLS
    umls_root = root / "umls"
    umls_raw = umls_root / "raw"
    umls_archives = sorted(umls_raw.glob("*.nlm"))
    if umls_archives:
        output = umls_root / "umls_concepts_full.csv"
        languages = umls_languages or ["ENG"]
        sab_whitelist = umls_sab
        wrote = import_umls.write_rows(
            import_umls.iter_umls_rows(
                umls_raw,
                languages=languages,
                sab_whitelist=sab_whitelist,
            ),
            output,
        )
        summary["umls"] = "normalized" if wrote else "skipped (no concepts parsed)"
    else:
        summary["umls"] = "skipped (no .nlm archives found)"

    if rebuild_db:
        from tools.build_terminology_db import build_database

        db_path = output_db or (root / "terminology.duckdb")
        build_database(root, db_path, force=force)
        summary["duckdb"] = f"rebuilt ({db_path})"

    return summary


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Normalize staged terminology datasets")
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT, help="Terminology directory root")
    parser.add_argument(
        "--rebuild-db",
        action="store_true",
        help="Rebuild the DuckDB warehouse after normalization",
    )
    parser.add_argument(
        "--output-db",
        type=Path,
        help="Override the output path for the DuckDB warehouse",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite the DuckDB warehouse when rebuilding",
    )
    parser.add_argument(
        "--umls-languages",
        nargs="*",
        help="Optional list of UMLS language codes (defaults to ENG)",
    )
    parser.add_argument(
        "--umls-sab",
        nargs="*",
        help="Optional list of UMLS source abbreviations to include",
    )
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> None:
    args = parse_args(argv)
    summary = refresh_terminology(
        args.root,
        rebuild_db=args.rebuild_db,
        output_db=args.output_db,
        force=args.force,
        umls_languages=args.umls_languages,
        umls_sab=args.umls_sab,
    )

    for system, status in summary.items():
        print(f"{system}: {status}")


if __name__ == "__main__":
    main()
