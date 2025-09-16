"""Utility to stage migration-related modules into a dedicated branch workspace.

The script copies the migration simulator code and supporting models into a target
folder so a legacy migration branch can retain the functionality while `main`
continues the simulator refactor.
"""
from __future__ import annotations

import argparse
import shutil
from pathlib import Path
from typing import Iterable

# Files that should live on the migration-only branch
MIGRATION_FILES = [
    Path("src/core/migration_models.py"),
    Path("src/core/migration_simulator.py"),
    Path("src/core/enhanced_migration_simulator.py"),
    Path("src/core/enhanced_migration_tracker.py"),
]


def copy_files(files: Iterable[Path], destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    for file_path in files:
        if not file_path.exists():
            print(f"Skipping missing file: {file_path}")
            continue
        target_path = destination / file_path
        target_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(file_path, target_path)
        print(f"Copied {file_path} -> {target_path}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Prepare migration-specific modules for a legacy branch split.",
    )
    parser.add_argument(
        "destination",
        type=Path,
        help="Target directory where migration files should be staged (e.g., ../migration_snapshot)",
    )
    args = parser.parse_args()

    copy_files(MIGRATION_FILES, args.destination)
    print("\nMigration modules staged successfully.\n"
          "Next steps:\n"
          "  1. Create the legacy branch (e.g., git checkout -b migration).\n"
          "  2. Commit the staged files and supporting documentation.\n"
          "  3. Remove migration imports from main once the branch is pushed.")


if __name__ == "__main__":
    main()
