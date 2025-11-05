#!/usr/bin/env python3
"""Lint clinical workflow modules for structural and terminology issues."""

from __future__ import annotations

import argparse
import sys
from functools import lru_cache
from pathlib import Path
from typing import Dict, Iterable, List, Set

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.core.lifecycle.modules.engine import ModuleDefinition, ModuleState
from src.core.lifecycle.modules.validation import validate_module_definition
from src.core.lifecycle.modules.reference_utils import (
    ParameterResolutionError,
    resolve_definition_parameters,
    resolve_use_token,
)


def discover_modules(root: Path) -> List[str]:
    return sorted(p.stem for p in root.glob("*.yaml"))


def load_definition(root: Path, module_name: str) -> ModuleDefinition:
    path = root / f"{module_name}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Module '{module_name}' not found at {path}")
    with path.open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle)
    return ModuleDefinition.from_dict(payload)


SOURCES_PATH = PROJECT_ROOT / "docs" / "sources.yml"


@lru_cache(maxsize=1)
def load_source_catalog() -> Set[str]:
    if not SOURCES_PATH.exists():
        return set()
    with SOURCES_PATH.open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle) or {}
    entries = payload.get("sources", []) or []
    catalog: Set[str] = set()
    for entry in entries:
        if isinstance(entry, dict) and entry.get("id"):
            catalog.add(entry["id"])
    return catalog


def module_metadata_issues(definition: ModuleDefinition) -> List[str]:
    issues: List[str] = []
    if definition.gmf_version == 2:
        if not definition.version:
            issues.append(
                f"module '{definition.name}' (gmf_version=2) missing top-level 'version'"
            )
        if not definition.sources:
            issues.append(
                f"module '{definition.name}' (gmf_version=2) must declare at least one source"
            )
    catalog = load_source_catalog()
    for source_id in definition.sources or []:
        if source_id not in catalog:
            issues.append(
                f"module '{definition.name}' references unknown source '{source_id}'"
            )
    return issues


def state_requires_provenance(state: ModuleState) -> bool:
    if state.type == "decision":
        for transition in state.transitions or []:
            probability = transition.get("probability")
            if probability is None:
                continue
            try:
                value = float(probability)
            except (TypeError, ValueError):
                return True
            if value not in (0.0, 1.0):
                return True
        return False
    if state.type == "delay":
        data = state.data or {}
        if any(key in data for key in ("exact", "range")):
            return True
        if data.get("duration_days"):
            return True
    return False


def provenance_issues(
    definition: ModuleDefinition, parameter_usage: Dict[str, Set[str]]
) -> List[str]:
    issues: List[str] = []
    if definition.gmf_version != 2:
        return issues
    catalog = load_source_catalog()
    for state_name, state in definition.states.items():
        raw_sources = state.data.get("sources")
        if raw_sources is None:
            state_sources: List[str] = []
        elif isinstance(raw_sources, list):
            state_sources = raw_sources
        else:
            issues.append(f"state '{state_name}' sources must be a list if provided")
            state_sources = []

        for source_id in state_sources:
            if source_id not in catalog:
                issues.append(
                    f"state '{state_name}' references unknown source '{source_id}'"
                )

        tokens = parameter_usage.get(state_name, set())
        parameter_has_sources = False
        for token in tokens:
            try:
                _, metadata = resolve_use_token(token)
            except ParameterResolutionError as exc:
                issues.append(f"state '{state_name}' references invalid parameter: {exc}")
                continue
            if metadata.source_id:
                parameter_has_sources = True
                if metadata.source_id not in catalog:
                    issues.append(
                        f"state '{state_name}' parameter '{token}' cites unknown source '{metadata.source_id}'"
                    )
            else:
                issues.append(
                    f"state '{state_name}' parameter '{token}' missing source_id in parameter registry"
                )

        needs_provenance = state_requires_provenance(state)
        has_state_sources = bool(state_sources)
        if needs_provenance and not (has_state_sources or parameter_has_sources):
            issues.append(
                f"state '{state_name}' defines probabilities/delays without sources or parameter references"
            )

    return issues


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
        elif state.type == "call_submodule":
            if not data.get("module"):
                issues.append(
                    f"state '{state.name}' call_submodule missing required 'module'"
                )
    return issues


def submodule_issues(root: Path, definition: ModuleDefinition) -> List[str]:
    issues: List[str] = []
    for state in definition.states.values():
        if state.type != "call_submodule":
            continue
        module_name = state.data.get("module")
        if not module_name:
            continue
        path = root / f"{module_name}.yaml"
        if not path.exists():
            issues.append(
                f"state '{state.name}' references missing submodule '{module_name}'"
            )
    return issues


def lint_module(root: Path, module_name: str) -> List[str]:
    definition = load_definition(root, module_name)
    try:
        parameter_usage = resolve_definition_parameters(definition)
    except ParameterResolutionError as exc:
        return [str(exc)]

    issues = []
    issues.extend(module_metadata_issues(definition))
    issues.extend(provenance_issues(definition, parameter_usage))
    issues.extend(validate_module_definition(definition))
    issues.extend(terminology_issues(definition))
    issues.extend(submodule_issues(root, definition))
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
