from __future__ import annotations

import random
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set

import yaml

from .validation import ModuleValidationError, validate_module_definition


MODULES_ROOT = Path("modules")


def _ensure_modules_root(root: Optional[Path]) -> Path:
    base = root or MODULES_ROOT
    return base if base.is_absolute() else Path.cwd() / base


@dataclass
class ModuleState:
    name: str
    type: str
    data: Dict[str, Any]
    transitions: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class ModuleDefinition:
    name: str
    description: str
    categories: Dict[str, str]
    states: Dict[str, ModuleState]

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "ModuleDefinition":
        name = payload.get("name")
        if not name:
            raise ValueError("Module must define a name")
        description = payload.get("description", "")
        categories = payload.get("categories", {})
        states_raw = payload.get("states") or {}
        if "start" not in states_raw:
            raise ValueError(f"Module '{name}' is missing a 'start' state")
        states: Dict[str, ModuleState] = {}
        for state_name, state_payload in states_raw.items():
            state_type = state_payload.get("type")
            if not state_type:
                raise ValueError(f"State '{state_name}' in module '{name}' is missing a type")
            transitions = cls._normalize_transitions(state_payload)
            states[state_name] = ModuleState(
                name=state_name,
                type=state_type,
                data={
                    k: v
                    for k, v in state_payload.items()
                    if k not in {"type", "transitions", "branches"}
                },
                transitions=transitions,
            )
        return cls(name=name, description=description, categories=categories, states=states)

    @staticmethod
    def _normalize_transitions(state_payload: Dict[str, Any]) -> List[Dict[str, Any]]:
        transitions = state_payload.get("transitions")
        if transitions is not None:
            return list(transitions)
        branches = state_payload.get("branches")
        if branches is not None:
            return list(branches)
        return []


@dataclass
class ModuleExecutionResult:
    encounters: List[Dict[str, Any]] = field(default_factory=list)
    conditions: List[Dict[str, Any]] = field(default_factory=list)
    medications: List[Dict[str, Any]] = field(default_factory=list)
    observations: List[Dict[str, Any]] = field(default_factory=list)
    procedures: List[Dict[str, Any]] = field(default_factory=list)
    immunizations: List[Dict[str, Any]] = field(default_factory=list)
    care_plans: List[Dict[str, Any]] = field(default_factory=list)
    replacements: Set[str] = field(default_factory=set)

    def merge(self, other: "ModuleExecutionResult") -> None:
        self.encounters.extend(other.encounters)
        self.conditions.extend(other.conditions)
        self.medications.extend(other.medications)
        self.observations.extend(other.observations)
        self.procedures.extend(other.procedures)
        self.immunizations.extend(other.immunizations)
        self.care_plans.extend(other.care_plans)
        self.replacements.update(other.replacements)


class ModuleEngine:
    """Interpret clinical workflow modules and generate structured patient events."""

    def __init__(
        self,
        module_names: Sequence[str],
        *,
        modules_root: Optional[Path] = None,
    ) -> None:
        self.modules_root = _ensure_modules_root(modules_root)
        self.definitions: List[ModuleDefinition] = []
        for module_name in module_names:
            definition = self._load_module(module_name)
            issues = validate_module_definition(definition)
            if issues:
                raise ModuleValidationError(module_name, issues)
            self.definitions.append(definition)
        self.replace_categories: Dict[str, Set[str]] = {}
        for definition in self.definitions:
            replace = {
                category
                for category, mode in definition.categories.items()
                if str(mode).lower() == "replace"
            }
            self.replace_categories[definition.name] = replace

    def _load_module(self, module_name: str) -> ModuleDefinition:
        path = self.modules_root / f"{module_name}.yaml"
        if not path.exists():
            raise FileNotFoundError(f"Module '{module_name}' not found at {path}")
        with path.open("r", encoding="utf-8") as handle:
            payload = yaml.safe_load(handle)
        return ModuleDefinition.from_dict(payload)

    def categories_replaced(self) -> Set[str]:
        categories: Set[str] = set()
        for replace in self.replace_categories.values():
            categories.update(replace)
        return categories

    def execute(self, patient: Dict[str, Any]) -> ModuleExecutionResult:
        if not self.definitions:
            return ModuleExecutionResult()

        result = ModuleExecutionResult()
        for definition in self.definitions:
            runner = _ModuleRunner(definition, patient)
            module_result = runner.run()
            module_result.replacements.update(
                self.replace_categories.get(definition.name, set())
            )
            result.merge(module_result)
        return result


class _ModuleRunner:
    def __init__(self, definition: ModuleDefinition, patient: Dict[str, Any]) -> None:
        self.definition = definition
        self.patient = patient
        self.output = ModuleExecutionResult()
        self.current_time = self._initial_timestamp()
        self.last_encounter_id: Optional[str] = None
        self.visited = 0

    def _initial_timestamp(self) -> datetime:
        birthdate = datetime.strptime(self.patient["birthdate"], "%Y-%m-%d")
        age = max(self.patient.get("age", 30), 1)
        # Begin roughly one year before the current date, adjusted for patient age
        baseline_years = min(age - 1, 5)
        start_date = datetime.now() - timedelta(days=baseline_years * 365)
        return start_date

    def run(self) -> ModuleExecutionResult:
        state_name = "start"
        while state_name:
            if self.visited > 200:
                break
            state = self.definition.states.get(state_name)
            if state is None:
                break
            next_state = self._execute_state(state)
            if not next_state:
                break
            state_name = next_state
            self.visited += 1
        return self.output

    # State execution helpers -------------------------------------------------

    def _execute_state(self, state: ModuleState) -> Optional[str]:
        handler_name = f"_handle_{state.type}"
        handler = getattr(self, handler_name, None)
        if not handler:
            # Unknown state types are ignored but still follow transitions
            return self._choose_transition(state.transitions)
        handler(state)
        return self._choose_transition(state.transitions)

    def _handle_start(self, _: ModuleState) -> None:
        # no-op; transitions dictate next state
        return None

    def _handle_terminal(self, _: ModuleState) -> None:
        # Terminal state: stop execution by clearing transitions later
        return None

    def _handle_delay(self, state: ModuleState) -> None:
        days = int(state.data.get("duration_days", 0))
        self.current_time += timedelta(days=days)

    def _handle_encounter(self, state: ModuleState) -> None:
        encounter_id = str(uuid.uuid4())
        entry = {
            "encounter_id": encounter_id,
            "patient_id": self.patient["patient_id"],
            "date": self.current_time.date().isoformat(),
            "type": state.data.get("encounter_type", "Office Visit"),
            "reason": state.data.get("reason", "Encounter"),
            "provider": state.data.get("provider_role", "Primary Care"),
            "location": state.data.get("location", "Clinic"),
        }
        self.output.encounters.append(entry)
        self.last_encounter_id = encounter_id
        self._advance_time(state.data.get("advance_days"), default_days=1)

    def _handle_condition_onset(self, state: ModuleState) -> None:
        attach = bool(state.data.get("attach_to_last_encounter", False))
        for condition in state.data.get("conditions", []):
            entry = {
                "condition_id": str(uuid.uuid4()),
                "patient_id": self.patient["patient_id"],
                "encounter_id": self.last_encounter_id if attach else None,
                "name": condition.get("name", "Condition"),
                "status": "active",
                "onset_date": self.current_time.date().isoformat(),
                "icd10_code": condition.get("icd10"),
                "snomed_code": condition.get("snomed"),
                "condition_category": condition.get("category"),
            }
            self.output.conditions.append(entry)
        self._advance_time(state.data.get("advance_days"))

    def _handle_medication_start(self, state: ModuleState) -> None:
        attach = bool(state.data.get("attach_to_last_encounter", False))
        for medication in state.data.get("medications", []):
            start_date = self.current_time.date().isoformat()
            entry = {
                "medication_id": str(uuid.uuid4()),
                "patient_id": self.patient["patient_id"],
                "encounter_id": self.last_encounter_id if attach else None,
                "name": medication.get("name", "Medication"),
                "indication": medication.get("condition", ""),
                "therapy_category": medication.get("therapy_category", "module"),
                "start_date": start_date,
                "end_date": None,
                "rxnorm_code": medication.get("rxnorm"),
                "ndc_code": medication.get("ndc"),
                "therapeutic_class": medication.get("class"),
            }
            if dose := medication.get("dose"):
                entry["dose"] = dose
            self.output.medications.append(entry)
        self._advance_time(state.data.get("advance_days"))

    def _handle_procedure(self, state: ModuleState) -> None:
        attach = bool(state.data.get("attach_to_last_encounter", False))
        for procedure in state.data.get("procedures", []):
            entry = {
                "procedure_id": str(uuid.uuid4()),
                "patient_id": self.patient["patient_id"],
                "encounter_id": self.last_encounter_id if attach else None,
                "name": procedure.get("name", "Procedure"),
                "code": procedure.get("code"),
                "coding_system": procedure.get("system"),
                "reason": procedure.get("reason"),
                "date": self.current_time.date().isoformat(),
                "status": procedure.get("status", "completed"),
            }
            self.output.procedures.append(entry)
        self._advance_time(state.data.get("advance_days"))

    def _handle_immunization(self, state: ModuleState) -> None:
        attach = bool(state.data.get("attach_to_last_encounter", False))
        for immunization in state.data.get("immunizations", []):
            entry = {
                "immunization_id": str(uuid.uuid4()),
                "patient_id": self.patient["patient_id"],
                "encounter_id": self.last_encounter_id if attach else None,
                "vaccine": immunization.get("name", "Immunization"),
                "cvx_code": immunization.get("cvx"),
                "date": self.current_time.date().isoformat(),
                "status": immunization.get("status", "completed"),
                "dose_number": immunization.get("dose_number"),
            }
            if lot := immunization.get("lot_number"):
                entry["lot_number"] = lot
            if manufacturer := immunization.get("manufacturer"):
                entry["manufacturer"] = manufacturer
            self.output.immunizations.append(entry)
        self._advance_time(state.data.get("advance_days"))

    def _handle_care_plan(self, state: ModuleState) -> None:
        for plan in state.data.get("care_plans", []):
            entry = {
                "care_plan_id": str(uuid.uuid4()),
                "patient_id": self.patient["patient_id"],
                "name": plan.get("name", "Care Plan"),
                "category": plan.get("category"),
                "start_date": self.current_time.date().isoformat(),
                "goal": plan.get("goal"),
                "activities": plan.get("activities", []),
            }
            self.output.care_plans.append(entry)
        self._advance_time(state.data.get("advance_days"))

    def _advance_time(self, advance_days: Optional[int], default_days: int = 0) -> None:
        days = advance_days if advance_days is not None else default_days
        if days:
            self.current_time += timedelta(days=int(days))

    def _handle_observation(self, state: ModuleState) -> None:
        attach = bool(state.data.get("attach_to_last_encounter", False))
        for observation in state.data.get("observations", []):
            value = observation.get("value")
            if value is None and "value_range" in observation:
                bounds = observation["value_range"]
                low = float(bounds.get("min", 0))
                high = float(bounds.get("max", low + 1))
                value = round(random.uniform(low, high), 2)
            entry = {
                "observation_id": str(uuid.uuid4()),
                "patient_id": self.patient["patient_id"],
                "encounter_id": self.last_encounter_id if attach else None,
                "type": observation.get("name", "Observation"),
                "loinc_code": observation.get("loinc"),
                "value": str(value) if value is not None else "",
                "value_numeric": value,
                "units": observation.get("units", ""),
                "reference_range": observation.get("reference_range", ""),
                "status": observation.get("status", "final"),
                "date": self.current_time.date().isoformat(),
                "panel": observation.get("panel"),
            }
            self.output.observations.append(entry)
        self._advance_time(state.data.get("advance_days"))

    def _handle_decision(self, state: ModuleState) -> None:
        # decision nodes handled directly in _choose_transition
        return None

    # Transition handling -----------------------------------------------------

    def _choose_transition(self, transitions: List[Dict[str, Any]]) -> Optional[str]:
        if not transitions:
            return None
        options = []
        for transition in transitions:
            target = transition.get("to")
            if not target:
                continue
            probability = float(transition.get("probability", 1.0))
            options.append((target, probability))
        if not options:
            return None
        total = sum(prob for _, prob in options)
        if total <= 0:
            return options[-1][0]
        r = random.random() * total
        upto = 0.0
        for target, prob in options:
            upto += prob
            if upto >= r:
                if target == "end":
                    return None
                return target
        target = options[-1][0]
        if target == "end":
            return None
        return target
