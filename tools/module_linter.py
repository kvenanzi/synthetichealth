#!/usr/bin/env python3
"""Lint clinical workflow modules for structural and terminology issues."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Iterable, List

import yaml

from src.core.lifecycle.modules.engine import ModuleDefinition
from src.core.lifecycle.modules.validation import validate_module_definition


def discover_modules(root: Path) -> List[str]:
    return sorted(p.stem for p in root.glob("*.yaml"))


def load_definition(root: Path, module_name: str) -> ModuleDefinition:
    path = root / f"{module_name}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Module '{module_name}' not found at {path}")
    with path.open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle)
    return ModuleDefinition.from_dict(payload)


def terminology_issues(definition: ModuleDefinition) -> List[str]:
    issues: List[str] = []
    for state in definition.states.values():
        data = state.data
        if state.type == "condition_onset":
            for idx, condition in enumerate(data.get("conditions", [])):
                if not (condition.get("icd10") or condition.get("snomed")):
                    issues.append(
                        f"state '{state.name}' condition #{idx + 1} missing icd10/snomed code"
                    )
        elif state.type == "medication_start":
            for idx, medication in enumerate(data.get("medications", [])):
                if not (medication.get("rxnorm") or medication.get("ndc")):
                    issues.append(
                        f"state '{state.name}' medication #{idx + 1} missing rxnorm/ndc code"
                    )
        elif state.type == "observation":
            for idx, observation in enumerate(data.get("observations", [])):
                if not observation.get("loinc"):
                    issues.append(
                        f"state '{state.name}' observation #{idx + 1} missing loinc code"
                    )
        elif state.type == "immunization":
            for idx, immunization in enumerate(data.get("immunizations", [])):
                if not immunization.get("cvx"):
                    issues.append(
                        f"state '{state.name}' immunization #{idx + 1} missing cvx code"
                    )
        elif state.type == "procedure":
            for idx, procedure in enumerate(data.get("procedures", [])):
                if not (procedure.get("code") and procedure.get("system")):
                    issues.append(
                        f"state '{state.name}' procedure #{idx + 1} missing code/system"
                    )
        elif state.type == "care_plan":
            for idx, plan in enumerate(data.get("care_plans", [])):
                if not plan.get("name"):
                    issues.append(
                        f"state '{state.name}' care plan #{idx + 1} missing name"
                    )
    return issues


def lint_module(root: Path, module_name: str) -> List[str]:
    definition = load_definition(root, module_name)
    issues = validate_module_definition(definition)
    issues.extend(terminology_issues(definition))
    return issues


def lint_modules(root: Path, module_names: Iterable[str]) -> List[tuple[str, List[str]]]:
    results: List[tuple[str, List[str]]] = []
    for name in module_names:
        issues = []
        try:
            issues = lint_module(root, name)
        except FileNotFoundError as exc:
            issues = [str(exc)]
        results.append((name, issues))
    return results


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Lint clinical workflow modules")
    parser.add_argument(
        "modules",
        metavar="MODULE",
        nargs="*",
        help="Module names to lint (omit extension)",
    )
    parser.add_argument(
        "--modules-root",
        type=Path,
        default=Path("modules"),
        help="Directory containing module YAML files",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Lint all modules discovered under the modules root",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = args.modules_root

    if args.all:
        module_names = discover_modules(root)
    else:
        module_names = list(args.modules)

    if not module_names:
        print("No modules specified. Use --all or provide module names.")
        return 1

    exit_code = 0
    for name, issues in lint_modules(root, module_names):
        if issues:
            exit_code = 2
            print(f"[FAIL] {name}")
            for issue in issues:
                print(f"  - {issue}")
        else:
            print(f"[ OK ] {name}")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())

