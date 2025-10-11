from __future__ import annotations

import math
import random
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set

import yaml

from .validation import ModuleValidationError, validate_module_definition
from .reference_utils import ParameterResolutionError, resolve_definition_parameters


MODULES_ROOT = Path("modules")


def _ensure_modules_root(root: Optional[Path]) -> Path:
    base = root or MODULES_ROOT
    return base if base.is_absolute() else Path.cwd() / base


def _coerce_transition(entry: Dict[str, Any]) -> Dict[str, Any]:
    target = entry.get("transition") or entry.get("to")
    result: Dict[str, Any] = {"to": target}
    if "probability" in entry:
        result["probability"] = entry.get("probability")
    if "distribution" in entry:
        result["probability"] = entry.get("distribution")
    if "condition" in entry:
        result["condition"] = entry.get("condition")
    return result


def _convert_to_days(quantity: Any, unit: str) -> float:
    try:
        value = float(quantity)
    except (TypeError, ValueError):
        return 0.0
    unit_lower = (unit or "days").lower()
    if unit_lower in {"day", "days"}:
        return value
    if unit_lower in {"hour", "hours"}:
        return value / 24.0
    if unit_lower in {"week", "weeks"}:
        return value * 7.0
    if unit_lower in {"month", "months"}:
        return value * 30.0
    if unit_lower in {"year", "years"}:
        return value * 365.0
    return value


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
    version: Optional[str] = None
    gmf_version: Optional[int] = None
    sources: List[str] = field(default_factory=list)
    remarks: List[str] = field(default_factory=list)

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
        version = payload.get("version")
        gmf_version = payload.get("gmf_version")
        sources = list(payload.get("sources") or [])
        remarks = list(payload.get("remarks") or [])
        return cls(
            name=name,
            description=description,
            categories=categories,
            states=states,
            version=version,
            gmf_version=gmf_version,
            sources=sources,
            remarks=remarks,
        )

    @staticmethod
    def _normalize_transitions(state_payload: Dict[str, Any]) -> List[Dict[str, Any]]:
        transitions = state_payload.pop("transitions", None)
        if transitions is not None:
            normalized: List[Dict[str, Any]] = []
            for item in transitions:
                if not isinstance(item, dict):
                    continue
                normalized.append(_coerce_transition(item))
            return normalized

        normalized: List[Dict[str, Any]] = []

        direct = state_payload.pop("direct_transition", None)
        if direct:
            normalized.append({"to": direct})

        distributed = state_payload.pop("distributed_transition", None)
        if distributed:
            for entry in distributed or []:
                if isinstance(entry, dict):
                    target = entry.get("transition") or entry.get("to")
                    probability = entry.get("distribution") or entry.get("probability")
                    normalized.append(
                        {"to": target, "probability": probability}
                    )

        conditional = state_payload.pop("conditional_transition", None)
        if conditional:
            for entry in conditional or []:
                if isinstance(entry, dict):
                    target = entry.get("transition") or entry.get("to")
                    condition = entry.get("condition")
                    normalized.append({"to": target, "condition": condition})

        branches = state_payload.pop("branches", None)
        if branches:
            for entry in branches or []:
                if isinstance(entry, dict):
                    normalized.append(_coerce_transition(entry))

        return normalized


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
    attributes: Dict[str, Any] = field(default_factory=dict)

    def merge(self, other: "ModuleExecutionResult") -> None:
        self.encounters.extend(other.encounters)
        self.conditions.extend(other.conditions)
        self.medications.extend(other.medications)
        self.observations.extend(other.observations)
        self.procedures.extend(other.procedures)
        self.immunizations.extend(other.immunizations)
        self.care_plans.extend(other.care_plans)
        self.replacements.update(other.replacements)
        self.attributes.update(other.attributes)


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
            try:
                resolve_definition_parameters(definition)
            except ParameterResolutionError as exc:
                raise ModuleValidationError(module_name, [str(exc)]) from exc
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
        self.attributes: Dict[str, Any] = {}
        self.condition_index: Dict[str, Dict[str, Any]] = {}
        self.medication_index: Dict[str, Dict[str, Any]] = {}
        self.care_plan_index: Dict[str, Dict[str, Any]] = {}
        self.encounter_index: Dict[str, Dict[str, Any]] = {}

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
        if self.attributes:
            self.output.attributes.update(self.attributes)
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
        days = self._resolve_delay_days(state.data)
        if days:
            self.current_time += timedelta(days=days)

    @staticmethod
    def _resolve_delay_days(config: Dict[str, Any]) -> float:
        if "duration_days" in config:
            try:
                return float(config.get("duration_days", 0))
            except (TypeError, ValueError):
                return 0.0
        if "exact" in config:
            exact = config.get("exact") or {}
            quantity = exact.get("quantity", 0)
            unit = exact.get("unit", "days")
            return _convert_to_days(quantity, unit)
        if "range" in config:
            range_cfg = config.get("range") or {}
            low = range_cfg.get("low", range_cfg.get("min", 0))
            high = range_cfg.get("high", range_cfg.get("max", low))
            unit = range_cfg.get("unit", "days")
            low_days = _convert_to_days(low, unit)
            high_days = _convert_to_days(high, unit)
            if high_days <= low_days:
                return low_days
            return random.uniform(low_days, high_days)
        return 0.0

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
        self.encounter_index[encounter_id] = entry
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
                "end_date": None,
            }
            self.output.conditions.append(entry)
            condition_id = entry["condition_id"]
            self.condition_index[condition_id] = entry
            attribute_name = state.data.get("assign_to_attribute")
            if attribute_name:
                self.attributes[attribute_name] = condition_id
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
                "status": medication.get("status", "active"),
            }
            if dose := medication.get("dose"):
                entry["dose"] = dose
            self.output.medications.append(entry)
            medication_id = entry["medication_id"]
            self.medication_index[medication_id] = entry
            attribute_name = state.data.get("assign_to_attribute")
            if attribute_name:
                self.attributes[attribute_name] = medication_id
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
                "status": plan.get("status", "active"),
                "end_date": None,
            }
            self.output.care_plans.append(entry)
            plan_id = entry["care_plan_id"]
            self.care_plan_index[plan_id] = entry
            attribute_name = plan.get("assign_to_attribute") or state.data.get("assign_to_attribute")
            if attribute_name:
                self.attributes[attribute_name] = plan_id
        self._advance_time(state.data.get("advance_days"))

    def _handle_care_plan_start(self, state: ModuleState) -> None:
        plan = {
            "name": state.data.get("name", state.data.get("care_plan_name", "Care Plan")),
            "category": state.data.get("category"),
            "goal": state.data.get("goal"),
            "activities": state.data.get("activities", []),
            "status": "active",
        }
        wrapper = ModuleState(name=state.name, type="care_plan", data={"care_plans": [plan]})
        self._handle_care_plan(wrapper)

    def _handle_care_plan_end(self, state: ModuleState) -> None:
        attribute_name = state.data.get("referenced_by_attribute")
        plan_id = self.attributes.get(attribute_name) if attribute_name else None
        if not plan_id:
            return
        entry = self.care_plan_index.get(plan_id)
        if entry:
            entry["status"] = state.data.get("status", "completed")
            entry["end_date"] = self.current_time.date().isoformat()

    def _handle_condition_end(self, state: ModuleState) -> None:
        attribute_name = state.data.get("referenced_by_attribute")
        condition_id = self.attributes.get(attribute_name) if attribute_name else None
        if not condition_id:
            return
        entry = self.condition_index.get(condition_id)
        if entry:
            entry["status"] = state.data.get("status", "resolved")
            entry["end_date"] = self.current_time.date().isoformat()

    def _handle_medication_end(self, state: ModuleState) -> None:
        attribute_name = state.data.get("referenced_by_attribute")
        medication_id = self.attributes.get(attribute_name) if attribute_name else None
        if not medication_id:
            return
        entry = self.medication_index.get(medication_id)
        if entry:
            entry["status"] = state.data.get("status", "completed")
            entry["end_date"] = self.current_time.date().isoformat()

    def _advance_time(self, advance_days: Optional[int], default_days: int = 0) -> None:
        days = advance_days if advance_days is not None else default_days
        if days:
            try:
                delta = float(days)
            except (TypeError, ValueError):
                delta = 0.0
            self.current_time += timedelta(days=delta)

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

    def _handle_symptom(self, state: ModuleState) -> None:
        symptom_name = state.data.get("symptom") or state.data.get("name", "Symptom")
        value = state.data.get("value")
        if value is None:
            value_range = state.data.get("range") or state.data.get("value_range") or {}
            low = float(value_range.get("low", value_range.get("min", 0)))
            high = float(value_range.get("high", value_range.get("max", low)))
            if high == low:
                value = low
            else:
                value = round(random.uniform(low, high), 2)
        entry = {
            "observation_id": str(uuid.uuid4()),
            "patient_id": self.patient["patient_id"],
            "encounter_id": self.last_encounter_id,
            "type": symptom_name,
            "value": str(value),
            "value_numeric": value,
            "units": state.data.get("units", ""),
            "status": state.data.get("status", "recorded"),
            "date": self.current_time.date().isoformat(),
            "panel": state.data.get("panel"),
        }
        self.output.observations.append(entry)
        self._advance_time(state.data.get("advance_days"))

    def _handle_set_attribute(self, state: ModuleState) -> None:
        attribute = state.data.get("attribute")
        value = state.data.get("value")
        if attribute:
            self.attributes[attribute] = value

    def _handle_encounter_end(self, state: ModuleState) -> None:
        if not self.last_encounter_id:
            return
        entry = self.encounter_index.get(self.last_encounter_id)
        if entry:
            entry["end_date"] = self.current_time.date().isoformat()
        self.last_encounter_id = None

    def _handle_decision(self, state: ModuleState) -> None:
        # decision nodes handled directly in _choose_transition
        return None

    # Transition handling -----------------------------------------------------

    def _choose_transition(self, transitions: List[Dict[str, Any]]) -> Optional[str]:
        if not transitions:
            return None

        eligible: List[Dict[str, Any]] = []
        for entry in transitions:
            target = entry.get("to")
            if not target:
                continue
            condition = entry.get("condition")
            if condition and not self._evaluate_condition(condition):
                continue
            eligible.append(entry)

        if not eligible:
            return None

        deterministic = [entry for entry in eligible if entry.get("probability") is None]
        if deterministic:
            target = deterministic[0].get("to")
            return None if target == "end" else target

        probabilistic = [entry for entry in eligible if entry.get("probability") is not None]
        if probabilistic:
            weights: List[float] = []
            total = 0.0
            for entry in probabilistic:
                try:
                    weight = max(float(entry.get("probability", 0.0)), 0.0)
                except (TypeError, ValueError):
                    weight = 0.0
                weights.append(weight)
                total += weight
            if total <= 0:
                target = probabilistic[-1].get("to")
                return None if target == "end" else target
            r = random.uniform(0.0, total)
            upto = 0.0
            for entry, weight in zip(probabilistic, weights):
                upto += weight
                if upto >= r:
                    target = entry.get("to")
                    return None if target == "end" else target
            target = probabilistic[-1].get("to")
            return None if target == "end" else target

        target = eligible[0].get("to")
        return None if target == "end" else target

    # Condition evaluation ---------------------------------------------------

    def _evaluate_condition(self, condition: Dict[str, Any]) -> bool:
        if not isinstance(condition, dict):
            return False
        condition_type = condition.get("condition_type") or condition.get("type")
        if not condition_type:
            return False
        condition_type = condition_type.lower()

        if condition_type == "attribute":
            attribute = condition.get("attribute")
            operator = (condition.get("operator") or "exists").lower()
            value = condition.get("value")
            current = self.attributes.get(attribute)
            if operator in {"==", "equals"}:
                return current == value
            if operator in {"!=", "ne"}:
                return current != value
            if operator in {"is not nil", "exists", "not null"}:
                return current is not None
            if operator in {"is nil", "is null", "not exists"}:
                return current is None
            return False

        if condition_type == "age":
            operator = condition.get("operator", ">=")
            quantity = condition.get("quantity", 0)
            unit = condition.get("unit", "years")
            value_days = _convert_to_days(quantity, unit)
            age_years = self._current_age_years()
            target_years = value_days / 365.0
            if operator == ">=":
                return age_years >= target_years
            if operator == ">":
                return age_years > target_years
            if operator == "<=":
                return age_years <= target_years
            if operator == "<":
                return age_years < target_years
            if operator == "==":
                return math.isclose(age_years, target_years, rel_tol=0.05, abs_tol=0.05)
            return False

        if condition_type == "demographic":
            field = condition.get("field") or condition.get("attribute")
            value = condition.get("value")
            if not field:
                return False
            patient_value = self.patient.get(field)
            if isinstance(patient_value, str) and isinstance(value, str):
                return patient_value.lower() == value.lower()
            return patient_value == value

        if condition_type == "hascondition":
            name = condition.get("name")
            return any(entry.get("name") == name for entry in self.output.conditions)

        if condition_type == "random":
            probability = condition.get("probability") or condition.get("value") or condition.get("p")
            try:
                prob = float(probability)
            except (TypeError, ValueError):
                prob = 0.0
            return random.random() < prob

        if condition_type == "and":
            sub_conditions = condition.get("conditions", [])
            return all(self._evaluate_condition(sub) for sub in sub_conditions)

        if condition_type == "or":
            sub_conditions = condition.get("conditions", [])
            return any(self._evaluate_condition(sub) for sub in sub_conditions)

        if condition_type == "not":
            sub_condition = condition.get("condition")
            return not self._evaluate_condition(sub_condition)

        return False

    def _current_age_years(self) -> float:
        birthdate = datetime.strptime(self.patient["birthdate"], "%Y-%m-%d")
        delta = self.current_time - birthdate
        return delta.days / 365.0 if delta.days > 0 else 0.0
