"""Domain models for the lifecycle-focused synthetic patient generator.

These dataclasses provide a structured representation of the clinical artifacts
produced by the generator so the legacy migration-oriented dictionaries can be
progressively retired.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from typing import Any, Dict, List, Optional


def _parse_date(value: Optional[str]) -> Optional[date]:
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        try:
            return datetime.fromisoformat(value).date()
        except ValueError:
            return None


def _parse_datetime(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        try:
            return datetime.strptime(value, "%Y-%m-%d").replace(hour=0, minute=0, second=0)
        except ValueError:
            return None


@dataclass
class ClinicalCode:
    system: str
    code: str
    display: str = ""


@dataclass
class Encounter:
    encounter_id: str
    patient_id: str
    encounter_type: str
    reason: str
    start_date: Optional[date]
    provider: Optional[str] = None
    location: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_legacy(cls, data: Dict[str, Any]) -> "Encounter":
        metadata = {
            key: value
            for key, value in data.items()
            if key not in {"encounter_id", "patient_id", "date", "type", "reason", "provider", "location"}
        }
        return cls(
            encounter_id=data.get("encounter_id", ""),
            patient_id=data.get("patient_id", ""),
            encounter_type=data.get("type", ""),
            reason=data.get("reason", ""),
            start_date=_parse_date(data.get("date")),
            provider=data.get("provider"),
            location=data.get("location"),
            metadata=metadata,
        )


@dataclass
class Condition:
    condition_id: str
    patient_id: str
    name: str
    clinical_status: str
    onset_date: Optional[date]
    icd10_code: Optional[str] = None
    snomed_code: Optional[str] = None
    category: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_legacy(cls, data: Dict[str, Any]) -> "Condition":
        metadata = {
            key: value
            for key, value in data.items()
            if key
            not in {
                "condition_id",
                "patient_id",
                "encounter_id",
                "name",
                "status",
                "onset_date",
                "icd10_code",
                "snomed_code",
                "condition_category",
            }
        }
        return cls(
            condition_id=data.get("condition_id", ""),
            patient_id=data.get("patient_id", ""),
            name=data.get("name", ""),
            clinical_status=data.get("status", "unknown"),
            onset_date=_parse_date(data.get("onset_date")),
            icd10_code=data.get("icd10_code"),
            snomed_code=data.get("snomed_code"),
            category=data.get("condition_category"),
            metadata=metadata,
        )


@dataclass
class MedicationOrder:
    medication_id: str
    patient_id: str
    name: str
    start_date: Optional[date]
    end_date: Optional[date]
    rxnorm_code: Optional[str]
    ndc_code: Optional[str]
    therapeutic_class: Optional[str]
    indication: Optional[str] = None
    therapy_category: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_legacy(cls, data: Dict[str, Any]) -> "MedicationOrder":
        metadata = {
            key: value
            for key, value in data.items()
            if key
            not in {
                "medication_id",
                "patient_id",
                "name",
                "start_date",
                "end_date",
                "rxnorm_code",
                "ndc_code",
                "therapeutic_class",
                "indication",
                "therapy_category",
            }
        }
        return cls(
            medication_id=data.get("medication_id", ""),
            patient_id=data.get("patient_id", ""),
            name=data.get("name", ""),
            start_date=_parse_date(data.get("start_date")),
            end_date=_parse_date(data.get("end_date")),
            rxnorm_code=data.get("rxnorm_code"),
            ndc_code=data.get("ndc_code"),
            therapeutic_class=data.get("therapeutic_class"),
            indication=data.get("indication"),
            therapy_category=data.get("therapy_category"),
            metadata=metadata,
        )


@dataclass
class Observation:
    observation_id: str
    patient_id: str
    name: str
    value: Any
    unit: Optional[str]
    status: Optional[str]
    effective_datetime: Optional[datetime]
    encounter_id: Optional[str] = None
    interpretation: Optional[str] = None
    reference_range: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_legacy(cls, data: Dict[str, Any]) -> "Observation":
        metadata = {
            key: value
            for key, value in data.items()
            if key
            not in {
                "observation_id",
                "patient_id",
                "encounter_id",
                "type",
                "value",
                "unit",
                "status",
                "status_category",
                "observation_date",
                "interpretation",
                "reference_range",
            }
        }
        ref_range = data.get("reference_range")
        if isinstance(ref_range, dict):
            range_payload = ref_range
        else:
            range_payload = None
        return cls(
            observation_id=data.get("observation_id", ""),
            patient_id=data.get("patient_id", ""),
            name=data.get("type", ""),
            value=data.get("value"),
            unit=data.get("unit"),
            status=data.get("status"),
            effective_datetime=_parse_datetime(data.get("observation_date")),
            encounter_id=data.get("encounter_id"),
            interpretation=data.get("interpretation"),
            reference_range=range_payload,
            metadata=metadata,
        )


@dataclass
class ImmunizationRecord:
    immunization_id: str
    patient_id: str
    name: str
    date_administered: Optional[date]
    cvx_code: Optional[str]
    rxnorm_code: Optional[str]
    lot_number: Optional[str]
    performer: Optional[str]
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_legacy(cls, data: Dict[str, Any]) -> "ImmunizationRecord":
        metadata = {
            key: value
            for key, value in data.items()
            if key
            not in {
                "immunization_id",
                "patient_id",
                "name",
                "date",
                "cvx_code",
                "rxnorm_code",
                "lot_number",
                "performer",
            }
        }
        return cls(
            immunization_id=data.get("immunization_id", ""),
            patient_id=data.get("patient_id", ""),
            name=data.get("name", ""),
            date_administered=_parse_date(data.get("date")),
            cvx_code=data.get("cvx_code"),
            rxnorm_code=data.get("rxnorm_code"),
            lot_number=data.get("lot_number"),
            performer=data.get("performer"),
            metadata=metadata,
        )


@dataclass
class CarePlanSummary:
    total: int = 0
    completed: int = 0
    overdue: int = 0
    scheduled: int = 0
    in_progress: int = 0


@dataclass
class FamilyHistoryEntry:
    family_history_id: str
    patient_id: str
    relation: str
    condition: str
    condition_display: Optional[str] = None
    relation_code: Optional[str] = None
    condition_code: Optional[str] = None
    condition_system: Optional[str] = None
    icd10_code: Optional[str] = None
    onset_age: Optional[int] = None
    recorded_date: Optional[date] = None
    risk_modifier: Optional[float] = None
    notes: Optional[str] = None
    source: Optional[str] = None
    genetic_marker: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_legacy(cls, data: Dict[str, Any]) -> "FamilyHistoryEntry":
        metadata = {
            key: value
            for key, value in data.items()
            if key
            not in {
                "family_history_id",
                "patient_id",
                "relation",
                "relation_code",
                "condition",
                "condition_display",
                "condition_code",
                "condition_system",
                "icd10_code",
                "onset_age",
                "recorded_date",
                "risk_modifier",
                "notes",
                "source",
                "genetic_marker",
            }
        }

        return cls(
            family_history_id=str(data.get("family_history_id", "")),
            patient_id=str(data.get("patient_id", "")),
            relation=data.get("relation", ""),
            condition=data.get("condition", ""),
            condition_display=data.get("condition_display"),
            relation_code=data.get("relation_code"),
            condition_code=data.get("condition_code"),
            condition_system=data.get("condition_system"),
            icd10_code=data.get("icd10_code"),
            onset_age=data.get("onset_age"),
            recorded_date=_parse_date(data.get("recorded_date")),
            risk_modifier=data.get("risk_modifier"),
            notes=data.get("notes"),
            source=data.get("source"),
            genetic_marker=data.get("genetic_marker"),
            metadata=metadata,
        )


@dataclass
class DeathRecord:
    patient_id: str
    death_date: Optional[date]
    age_at_death: Optional[int]
    primary_cause_code: str
    primary_cause_description: Optional[str] = None
    contributing_causes: Optional[str] = None
    manner_of_death: Optional[str] = None
    death_certificate_type: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_legacy(cls, data: Dict[str, Any]) -> "DeathRecord":
        metadata = {
            key: value
            for key, value in data.items()
            if key
            not in {
                "patient_id",
                "death_date",
                "age_at_death",
                "primary_cause_code",
                "primary_cause_description",
                "contributing_causes",
                "manner_of_death",
                "death_certificate_type",
            }
        }
        return cls(
            patient_id=str(data.get("patient_id", "")),
            death_date=_parse_date(data.get("death_date")),
            age_at_death=data.get("age_at_death"),
            primary_cause_code=data.get("primary_cause_code", ""),
            primary_cause_description=data.get("primary_cause_description"),
            contributing_causes=data.get("contributing_causes"),
            manner_of_death=data.get("manner_of_death"),
            death_certificate_type=data.get("death_certificate_type"),
            metadata=metadata,
        )


@dataclass
class Patient:
    patient_id: str
    first_name: str
    last_name: str
    birth_date: date
    gender: str
    race: str
    ethnicity: str
    middle_name: Optional[str] = None
    language: Optional[str] = None
    marital_status: Optional[str] = None
    contact: Dict[str, Any] = field(default_factory=dict)
    address: Dict[str, Any] = field(default_factory=dict)
    identifiers: Dict[str, Any] = field(default_factory=dict)
    sdoh: Dict[str, Any] = field(default_factory=dict)
    encounters: List[Encounter] = field(default_factory=list)
    conditions: List[Condition] = field(default_factory=list)
    medications: List[MedicationOrder] = field(default_factory=list)
    immunizations: List[ImmunizationRecord] = field(default_factory=list)
    observations: List[Observation] = field(default_factory=list)
    allergies: List[Dict[str, Any]] = field(default_factory=list)
    procedures: List[Dict[str, Any]] = field(default_factory=list)
    care_plans: List[Dict[str, Any]] = field(default_factory=list)
    care_plan: CarePlanSummary = field(default_factory=CarePlanSummary)
    metadata: Dict[str, Any] = field(default_factory=dict)
    family_history: List[FamilyHistoryEntry] = field(default_factory=list)
    death: Optional[DeathRecord] = None

    @classmethod
    def from_legacy(
        cls,
        patient: Dict[str, Any],
        *,
        encounters: List[Dict[str, Any]],
        conditions: List[Dict[str, Any]],
        medications: List[Dict[str, Any]],
        immunizations: List[Dict[str, Any]],
        observations: List[Dict[str, Any]],
        allergies: List[Dict[str, Any]],
        procedures: List[Dict[str, Any]],
        family_history: Optional[List[Dict[str, Any]]] = None,
        death: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> "Patient":
        birth_date = _parse_date(patient.get("birthdate")) or date.today()
        sdoh = {
            key: patient.get(key)
            for key in (
                "smoking_status",
                "alcohol_use",
                "education",
                "employment_status",
                "income",
                "housing_status",
                "sdoh_risk_score",
                "sdoh_risk_factors",
                "community_deprivation_index",
                "access_to_care_score",
                "transportation_access",
                "language_access_barrier",
                "social_support_score",
                "sdoh_care_gaps",
            )
            if key in patient
        }
        identifiers = {
            key: patient.get(key)
            for key in ("mrn", "vista_id", "ssn")
            if patient.get(key)
        }
        contact = {
            "phone": patient.get("phone"),
            "email": patient.get("email"),
            "insurance": patient.get("insurance"),
        }
        address = {
            "line": patient.get("address"),
            "city": patient.get("city"),
            "state": patient.get("state"),
            "postal_code": patient.get("zip"),
            "country": patient.get("country"),
        }
        care_plan = CarePlanSummary(
            total=patient.get("care_plan_total", 0),
            completed=patient.get("care_plan_completed", 0),
            overdue=patient.get("care_plan_overdue", 0),
            scheduled=patient.get("care_plan_scheduled", 0),
            in_progress=patient.get("care_plan_in_progress", 0),
        )
        care_plan_details = metadata.get("care_plan_details") if metadata else None
        if not care_plan_details:
            care_plan_details = patient.get("care_plans") or []
        family_history_payload: List[FamilyHistoryEntry] = []
        source_family_history = family_history if family_history is not None else patient.get("family_history") or patient.get("family_history_entries")
        if source_family_history:
            for entry in source_family_history:
                if isinstance(entry, FamilyHistoryEntry):
                    family_history_payload.append(entry)
                elif isinstance(entry, dict):
                    family_history_payload.append(FamilyHistoryEntry.from_legacy(entry))

        death_record: Optional[DeathRecord] = None
        source_death = death if death is not None else patient.get("death") or patient.get("death_record")
        if isinstance(source_death, DeathRecord):
            death_record = source_death
        elif isinstance(source_death, dict):
            death_record = DeathRecord.from_legacy(source_death)

        return cls(
            patient_id=patient.get("patient_id", ""),
            first_name=patient.get("first_name", ""),
            last_name=patient.get("last_name", ""),
            middle_name=patient.get("middle_name"),
            birth_date=birth_date,
            gender=patient.get("gender", ""),
            race=patient.get("race", ""),
            ethnicity=patient.get("ethnicity", ""),
            language=patient.get("language"),
            marital_status=patient.get("marital_status"),
            contact={k: v for k, v in contact.items() if v},
            address={k: v for k, v in address.items() if v},
            identifiers=identifiers,
            sdoh={k: v for k, v in sdoh.items() if v is not None},
            encounters=[Encounter.from_legacy(item) for item in encounters],
            conditions=[Condition.from_legacy(item) for item in conditions],
            medications=[MedicationOrder.from_legacy(item) for item in medications],
            immunizations=[ImmunizationRecord.from_legacy(item) for item in immunizations],
            observations=[Observation.from_legacy(item) for item in observations],
            allergies=allergies,
            procedures=procedures,
            care_plans=care_plan_details,
            care_plan=care_plan,
            metadata=metadata or {},
            family_history=family_history_payload,
            death=death_record,
        )

    def to_serializable_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["birth_date"] = self.birth_date.isoformat()
        for encounter in payload.get("encounters", []):
            if encounter.get("start_date"):
                encounter["start_date"] = encounter["start_date"].isoformat()
        for condition in payload.get("conditions", []):
            if condition.get("onset_date"):
                condition["onset_date"] = condition["onset_date"].isoformat()
        for medication in payload.get("medications", []):
            if medication.get("start_date"):
                medication["start_date"] = medication["start_date"].isoformat()
            if medication.get("end_date"):
                medication["end_date"] = medication["end_date"].isoformat()
        for immunization in payload.get("immunizations", []):
            if immunization.get("date_administered"):
                immunization["date_administered"] = immunization["date_administered"].isoformat()
        for observation in payload.get("observations", []):
            eff = observation.get("effective_datetime")
            if eff:
                observation["effective_datetime"] = eff.isoformat()
        for entry in payload.get("family_history", []):
            recorded = entry.get("recorded_date")
            if isinstance(recorded, date):
                entry["recorded_date"] = recorded.isoformat()
        death_record = payload.get("death")
        if isinstance(death_record, dict) and death_record.get("death_date"):
            if isinstance(death_record["death_date"], date):
                death_record["death_date"] = death_record["death_date"].isoformat()
        return payload
