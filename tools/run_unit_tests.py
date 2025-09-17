"""Minimal test harness for environments without pytest."""
from __future__ import annotations

import importlib.util
import inspect
import sys
from pathlib import Path
from types import ModuleType
from typing import Iterable, List, Tuple

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

TEST_FILES: Tuple[Path, ...] = (
    PROJECT_ROOT / "tests" / "test_clinical_generation.py",
    PROJECT_ROOT / "tests" / "test_lifecycle_orchestrator.py",
    PROJECT_ROOT / "tests" / "test_scenario_loader.py",
    PROJECT_ROOT / "tests" / "test_patient_generation.py",
)


def load_module(module_path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(module_path.stem, module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load spec for {module_path}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def iter_test_callables(module: ModuleType) -> Iterable[Tuple[str, callable]]:
    for name, obj in inspect.getmembers(module):
        if name.startswith("test_") and callable(obj):
            yield name, obj


def main() -> int:
    failures: List[str] = []

    for file_path in TEST_FILES:
        module = load_module(file_path)
        for name, func in iter_test_callables(module):
            try:
                func()
            except Exception as exc:  # noqa: BLE001 - preserve assertion details
                failures.append(f"{file_path.name}:{name}: {exc}")

    if failures:
        print("\n".join(["Test failures detected:", *failures]))
        return 1

    print("All tests executed successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
