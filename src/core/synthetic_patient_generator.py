import polars as pl
from faker import Faker
import random
import concurrent.futures
import sys
import argparse
import os
import yaml
import json
import re
from datetime import date, datetime, timedelta
import uuid
from collections import defaultdict, Counter
from functools import partial
from pathlib import Path
from typing import List, Dict, Optional, Any, Tuple, Union, Iterable, Callable, Set
from tqdm import tqdm

from .terminology_catalogs import LAB_CODES
from .lifecycle import (
    Patient as LifecyclePatient,
    Condition as LifecycleCondition,
    Observation as LifecycleObservation,
    Encounter as LifecycleEncounter,
    MedicationOrder as LifecycleMedicationOrder,
    ImmunizationRecord,
     FamilyHistoryEntry,
    PatientRecord,
)
from .lifecycle.constants import (
    GENDERS,
    RACES,
    ETHNICITIES,
    MARITAL_STATUSES,
    LANGUAGES,
    INSURANCES,
    ENCOUNTER_TYPES,
    ENCOUNTER_REASONS,
    CONDITION_STATUSES,
    SDOH_SMOKING,
    SDOH_ALCOHOL,
    SDOH_EDUCATION,
    SDOH_EMPLOYMENT,
    SDOH_HOUSING,
    AGE_BINS,
    AGE_BIN_LABELS,
)
from .lifecycle.generation.clinical import (
    CONDITION_CATALOG,
    MEDICATION_CATALOG,
    IMMUNIZATION_CATALOG,
    generate_allergies,
    plan_allergy_followups,
    generate_care_plans,
    generate_conditions,
    generate_death,
    generate_encounters,
    generate_family_history,
    generate_immunizations,
    generate_medications,
    generate_observations,
    generate_procedures,
    assign_conditions,
    parse_distribution,
)
from .lifecycle.generation.patient import generate_patient_profile_for_index
from .lifecycle.loader import load_scenario_config
from .lifecycle.orchestrator import LifecycleOrchestrator
from .lifecycle.scenarios import list_scenarios
from .terminology import (
    TerminologyEntry,
    ValueSetMember,
    UmlsConcept,
    load_loinc_labs,
    load_rxnorm_medications,
)
from .lifecycle.modules import ModuleEngine, ModuleExecutionResult
from .migration_simulator import run_migration_phase

# Local faker instance for legacy generator utilities
fake = Faker()

# Terminology mapping lookup (Phase 5)
def build_default_terminology_mappings() -> Dict[str, Dict[str, Optional[str]]]:
    return {
        'conditions': {
            name: {
                'icd10': data.get('icd10'),
                'snomed': data.get('snomed')
            }
            for name, data in CONDITION_CATALOG.items()
        },
        'medications': {
            name: {
                'rxnorm': data.get('rxnorm'),
                'ndc': data.get('ndc')
            }
            for name, data in MEDICATION_CATALOG.items()
        },
        'immunizations': {
            name: {
                'cvx': data.get('cvx'),
                'snomed': data.get('snomed')
            }
            for name, data in IMMUNIZATION_CATALOG.items()
        }
    }


def list_available_modules(modules_root: Optional[Union[str, Path]] = None) -> List[str]:
    """Return available module filenames (without extension)."""

    root = Path(modules_root) if modules_root else Path("modules")
    if not root.exists():
        return []
    return sorted(p.stem for p in root.glob("*.yaml"))


def build_terminology_lookup(
    context: Optional[Dict[str, object]],
    root_override: Optional[str] = None,
) -> Dict[str, Dict[str, TerminologyEntry]]:
    """Normalize terminology context into dictionaries keyed by code.

    Scenario terminology details can supply a mixture of :class:`TerminologyEntry`
    instances (ICD-10, LOINC, SNOMED, RxNorm) as well as VSAC value set members
    and UMLS concept rows. This helper coerces each payload into a
    :class:`TerminologyEntry` so downstream exporters can consume a consistent
    structure regardless of the upstream source.
    """

    if not context:
        return {}

    def _coerce(entry: object) -> TerminologyEntry:
        if isinstance(entry, TerminologyEntry):
            return entry
        if isinstance(entry, ValueSetMember):
            metadata = {**entry.metadata}
            metadata.setdefault("value_set_oid", entry.value_set_oid)
            metadata.setdefault("value_set_name", entry.value_set_name)
            return TerminologyEntry(code=entry.code, display=entry.display, metadata=metadata)
        if isinstance(entry, UmlsConcept):
            metadata = {**entry.metadata}
            metadata.setdefault("semantic_type", entry.semantic_type)
            metadata.setdefault("tui", entry.tui)
            metadata.setdefault("sab", entry.sab)
            metadata.setdefault("code", entry.code)
            metadata.setdefault("tty", entry.tty)
            return TerminologyEntry(code=entry.cui, display=entry.preferred_name, metadata=metadata)
        raise TypeError(f"Unsupported terminology entry type: {type(entry)!r}")

    def _flatten(value: object) -> List[object]:
        if isinstance(value, list):
            return value
        if isinstance(value, dict):
            items: List[object] = []
            for nested in value.values():
                items.extend(_flatten(nested))
            return items
        if value is None:
            return []
        return [value]

    lookup: Dict[str, Dict[str, TerminologyEntry]] = {}
    for system, raw_entries in context.items():
        flattened = _flatten(raw_entries)
        if not flattened:
            continue
        system_lookup: Dict[str, TerminologyEntry] = {}
        for raw_entry in flattened:
            try:
                entry = _coerce(raw_entry)
            except TypeError:
                continue
            key = entry.code or entry.metadata.get("code") or entry.metadata.get("value_set_oid")
            if not key:
                continue
            if system == "vsac":
                value_set_oid = entry.metadata.get("value_set_oid")
                if value_set_oid:
                    key = f"{value_set_oid}|{entry.code}"
            system_lookup[str(key)] = entry
        if system_lookup:
            lookup[system] = system_lookup
    return lookup


TERMINOLOGY_MAPPINGS = build_default_terminology_mappings()

# Migration Simulation Classes

class FHIRFormatter:
    """FHIR R4 formatter that can annotate codes with NCBI references."""

    def __init__(self, terminology_lookup: Optional[Dict[str, Dict[str, TerminologyEntry]]] = None):
        self.terminology_lookup = terminology_lookup or {}
        self.rxnorm_lookup = self.terminology_lookup.get("rxnorm", {})
        self.loinc_lookup = self.terminology_lookup.get("loinc", {})
        vsac_entries = self.terminology_lookup.get("vsac", {})
        self.vsac_by_code: Dict[str, List[TerminologyEntry]] = {}
        for entry in vsac_entries.values():
            self.vsac_by_code.setdefault(entry.code, []).append(entry)

        umls_entries = self.terminology_lookup.get("umls", {})
        self.umls_by_source: Dict[Tuple[str, str], List[TerminologyEntry]] = {}
        for entry in umls_entries.values():
            sab = entry.metadata.get("sab")
            source_code = entry.metadata.get("code")
            if not sab or not source_code:
                continue
            key = (sab.upper(), source_code)
            self.umls_by_source.setdefault(key, []).append(entry)

    def create_patient_resource(self, patient_record: Union[PatientRecord, LifecyclePatient]) -> Dict[str, Any]:
        """Create basic FHIR R4 Patient resource"""

        if isinstance(patient_record, LifecyclePatient):
            identifiers = patient_record.identifiers
            mrn = identifiers.get("mrn") or identifiers.get("vista_id") or patient_record.patient_id
            ssn = identifiers.get("ssn")
            address = patient_record.address
            address_lines = [address.get("line")] if address.get("line") else []
            birthdate = patient_record.birth_date.isoformat()
            given_names = [name for name in [patient_record.first_name, patient_record.middle_name] if name]
            phone = patient_record.contact.get("phone")
            death_record = patient_record.death
        else:
            mrn = patient_record.mrn or patient_record.generate_mrn()
            ssn = patient_record.ssn
            address_lines = [patient_record.address] if patient_record.address else []
            birthdate = patient_record.birthdate
            given_names = [patient_record.first_name]
            phone = getattr(patient_record, "phone", None)
            death_record = patient_record.metadata.get("death_record") if hasattr(patient_record, "metadata") else None

        identifiers_payload = [
            {
                "use": "usual",
                "type": {
                    "coding": [{"system": "http://terminology.hl7.org/CodeSystem/v2-0203", "code": "MR"}]
                },
                "value": mrn,
            }
        ]
        if ssn:
            identifiers_payload.append(
                {
                    "use": "official",
                    "type": {
                        "coding": [{"system": "http://terminology.hl7.org/CodeSystem/v2-0203", "code": "SS"}]
                    },
                    "system": "http://hl7.org/fhir/sid/us-ssn",
                    "value": ssn,
                }
            )

        address_payload = []
        if address_lines:
            if isinstance(patient_record, LifecyclePatient):
                address_payload.append(
                    {
                        "use": "home",
                        "line": address_lines,
                        "city": patient_record.address.get("city"),
                        "state": patient_record.address.get("state"),
                        "postalCode": patient_record.address.get("postal_code"),
                        "country": patient_record.address.get("country"),
                    }
                )
            else:
                address_payload.append(
                    {
                        "use": "home",
                        "line": address_lines,
                        "city": patient_record.city,
                        "state": patient_record.state,
                        "postalCode": patient_record.zip,
                        "country": patient_record.country,
                    }
                )

        resource = {
            "resourceType": "Patient",
            "id": patient_record.patient_id,
            "identifier": identifiers_payload,
            "active": True,
            "telecom": ([{"system": "phone", "value": phone}] if phone else []),
            "name": [
                {
                    "use": "official",
                    "family": patient_record.last_name,
                    "given": given_names,
                }
            ],
            "gender": patient_record.gender,
            "birthDate": birthdate,
            "address": address_payload,
        }

        if death_record:
            if isinstance(death_record, dict):
                death_date_value = death_record.get("death_date")
            else:
                death_date_value = death_record.death_date.isoformat() if death_record.death_date else None
            if death_date_value:
                resource["deceasedDateTime"] = death_date_value
                resource["active"] = False

        return resource
    
    def create_condition_resource(
        self,
        patient_id: str,
        condition: Union[Dict[str, Any], LifecycleCondition],
    ) -> Dict[str, Any]:
        """Create basic FHIR R4 Condition resource with terminology mappings"""

        if isinstance(condition, LifecycleCondition):
            condition_name = condition.name
            onset_date = condition.onset_date.isoformat() if condition.onset_date else None
            status = condition.clinical_status or "active"
            condition_id = condition.condition_id or str(uuid.uuid4())
            metadata = condition.metadata or {}
        else:
            condition_name = condition.get("name", "")
            onset_date = condition.get("onset_date")
            status = condition.get("status", "active")
            condition_id = condition.get("condition_id", str(uuid.uuid4()))
            metadata = condition.get("metadata") or {}

        codes = TERMINOLOGY_MAPPINGS["conditions"].get(condition_name, {})

        coding = []
        if "icd10" in codes:
            coding.append(self._build_coding("http://hl7.org/fhir/sid/icd-10-cm", codes["icd10"], condition_name))
        if "snomed" in codes:
            coding.append(self._build_coding("http://snomed.info/sct", codes["snomed"], condition_name))

        # Fallback if no coding found
        if not coding:
            coding.append(
                {
                    "system": "http://terminology.hl7.org/CodeSystem/data-absent-reason",
                    "code": "unknown",
                    "display": condition_name,
                }
            )

        resource: Dict[str, Any] = {
            "resourceType": "Condition",
            "id": condition_id,
            "subject": {"reference": f"Patient/{patient_id}"},
            "code": {"coding": coding},
            "clinicalStatus": {
                "coding": [
                    {
                        "system": "http://terminology.hl7.org/CodeSystem/condition-clinical",
                        "code": status,
                    }
                ]
            },
            "verificationStatus": {
                "coding": [
                    {
                        "system": "http://terminology.hl7.org/CodeSystem/condition-ver-status",
                        "code": "confirmed",
                    }
                ]
            },
            "onsetDateTime": onset_date,
        }

        def _as_dict(value: Any) -> Optional[Dict[str, Any]]:
            if value is None or value == "":
                return None
            if isinstance(value, dict):
                return value
            if isinstance(value, str):
                try:
                    parsed = json.loads(value)
                    return parsed if isinstance(parsed, dict) else None
                except json.JSONDecodeError:
                    return None
            return None

        stage_detail = (
            _as_dict(metadata.get("stage_detail"))
            or _as_dict(condition.get("stage_detail") if isinstance(condition, dict) else None)
        )
        severity_detail = (
            _as_dict(metadata.get("severity_detail"))
            or _as_dict(condition.get("severity_detail") if isinstance(condition, dict) else None)
        )

        category_text: Optional[str] = None
        if isinstance(condition, LifecycleCondition) and condition.category:
            category_text = condition.category
        elif isinstance(condition, dict):
            category_text = condition.get("condition_category")

        category_entry: Dict[str, Any] = {
            "coding": [
                {
                    "system": "http://terminology.hl7.org/CodeSystem/condition-category",
                    "code": "problem-list-item",
                    "display": "Problem List Item",
                }
            ]
        }
        if category_text:
            category_entry["text"] = str(category_text).replace("_", " ").title()
        resource.setdefault("category", []).append(category_entry)

        if stage_detail:
            stage_entry: Dict[str, Any] = {}
            summary_coding: Dict[str, Any] = {}
            stage_system = stage_detail.get("system") or stage_detail.get("code_system")
            stage_code = stage_detail.get("code")
            stage_display = stage_detail.get("display") or stage_detail.get("text")
            if stage_system:
                summary_coding["system"] = stage_system
            if stage_code:
                summary_coding["code"] = stage_code
            if stage_display:
                summary_coding["display"] = stage_display

            if summary_coding:
                stage_entry["summary"] = {"coding": [summary_coding]}
            elif stage_display:
                stage_entry["summary"] = {"text": stage_display}

            stage_type = stage_detail.get("type")
            if stage_type:
                stage_entry["type"] = {"text": stage_type.replace("_", " ").title()}

            if stage_entry:
                resource.setdefault("stage", []).append(stage_entry)

        if severity_detail:
            severity_coding: Dict[str, Any] = {}
            severity_system = severity_detail.get("system") or severity_detail.get("code_system")
            severity_code = severity_detail.get("code")
            severity_display = severity_detail.get("display") or severity_detail.get("text")
            if severity_system:
                severity_coding["system"] = severity_system
            if severity_code:
                severity_coding["code"] = severity_code
            if severity_display:
                severity_coding["display"] = severity_display

            if severity_coding:
                resource["severity"] = {"coding": [severity_coding]}
            elif severity_display:
                resource["severity"] = {"text": severity_display}

        return resource

    def _build_coding(self, system: str, code: Optional[str], display: str) -> Dict[str, Any]:
        coding_entry = {
            "system": system,
            "code": code,
            "display": display,
        }
        if not code:
            return coding_entry

        lookup_key = None
        if system.endswith("icd-10-cm"):
            lookup_key = "icd10"
        elif "snomed" in system:
            lookup_key = "snomed"

        def _system_to_sab(value: str) -> Optional[str]:
            if "icd-10" in value:
                return "ICD10CM"
            if "snomed" in value:
                return "SNOMEDCT_US"
            return None

        if lookup_key and code in self.terminology_lookup.get(lookup_key, {}):
            entry = self.terminology_lookup[lookup_key][code]
            ncbi_url = entry.metadata.get("ncbi_url")
            if ncbi_url:
                coding_entry.setdefault("extension", []).append(
                    {
                        "url": "https://www.ncbi.nlm.nih.gov/",
                        "valueUri": ncbi_url,
                    }
                )

        sab = _system_to_sab(system)
        if sab:
            for concept in self.umls_by_source.get((sab, code), []):
                extensions = coding_entry.setdefault("extension", [])
                extensions.append(
                    {
                        "url": "http://example.org/fhir/StructureDefinition/umls-concept",
                        "extension": [
                            {"url": "cui", "valueCode": concept.code},
                            {"url": "preferredName", "valueString": concept.display},
                            {
                                "url": "semanticType",
                                "valueString": concept.metadata.get("semantic_type", ""),
                            },
                        ],
                    }
                )
        return coding_entry

    def create_allergy_intolerance_resource(
        self,
        patient_id: str,
        allergy: Dict[str, Any],
    ) -> Dict[str, Any]:
        allergy_id = allergy.get("allergy_id", str(uuid.uuid4()))
        substance_display = allergy.get("substance", "Unknown Allergen")
        substance_coding: List[Dict[str, Any]] = []

        rxnorm_code = allergy.get("rxnorm_code")
        if rxnorm_code:
            substance_coding.append(
                self._build_coding(
                    "http://www.nlm.nih.gov/research/umls/rxnorm",
                    rxnorm_code,
                    substance_display,
                )
            )

        snomed_substance = allergy.get("snomed_code")
        if snomed_substance:
            substance_coding.append(
                self._build_coding(
                    "http://snomed.info/sct",
                    snomed_substance,
                    substance_display,
                )
            )

        if not substance_coding:
            substance_coding.append(
                {
                    "system": "http://terminology.hl7.org/CodeSystem/data-absent-reason",
                    "code": "unknown",
                    "display": substance_display,
                }
            )

        category_map = {
            "drug": "medication",
            "food": "food",
            "environment": "environment",
            "insect": "biologic",
        }
        category_value = None
        category = allergy.get("category")
        if category:
            category_value = category_map.get(category)

        reaction_entry: Dict[str, Any] = {"manifestation": []}
        reaction_text = allergy.get("reaction")
        reaction_code = allergy.get("reaction_code")
        reaction_system = allergy.get("reaction_system", "http://snomed.info/sct")
        if reaction_code:
            reaction_entry["manifestation"].append(
                {
                    "coding": [
                        self._build_coding(
                            reaction_system,
                            reaction_code,
                            reaction_text or "Allergic reaction",
                        )
                    ],
                    "text": reaction_text or "Allergic reaction",
                }
            )
        else:
            reaction_entry["manifestation"].append(
                {"text": reaction_text or "Allergic reaction"}
            )

        severity = allergy.get("severity")
        if severity:
            reaction_entry["severity"] = severity.lower()

        clinical_status = {
            "coding": [
                {
                    "system": "http://terminology.hl7.org/CodeSystem/allergyintolerance-clinical",
                    "code": "active",
                }
            ]
        }
        verification_status = {
            "coding": [
                {
                    "system": "http://terminology.hl7.org/CodeSystem/allergyintolerance-verification",
                    "code": "confirmed",
                }
            ]
        }

        severity_code = allergy.get("severity_code")
        severity_system = allergy.get("severity_system", "http://snomed.info/sct")
        criticality = None
        if severity:
            severity_lower = severity.lower()
            if severity_lower == "severe":
                criticality = "high"
            elif severity_lower in {"moderate", "mild"}:
                criticality = "low"

        resource: Dict[str, Any] = {
            "resourceType": "AllergyIntolerance",
            "id": allergy_id,
            "patient": {"reference": f"Patient/{patient_id}"},
            "code": {
                "coding": substance_coding,
                "text": substance_display,
            },
            "clinicalStatus": clinical_status,
            "verificationStatus": verification_status,
            "reaction": [reaction_entry],
        }

        recorded_date = allergy.get("recorded_date")
        if recorded_date:
            resource["recordedDate"] = recorded_date
        if category_value:
            resource["category"] = [category_value]
        if criticality:
            resource["criticality"] = criticality
        if severity_code:
            resource.setdefault("extension", []).append(
                {
                    "url": "http://hl7.org/fhir/StructureDefinition/allergyintolerance-severity",
                    "valueCodeableConcept": {
                        "coding": [
                            {
                                "system": severity_system,
                                "code": severity_code,
                                "display": severity,
                            }
                        ]
                    },
                }
            )

        return resource

    def create_medication_statement_resource(
        self,
        patient_id: str,
        medication: Union[Dict[str, Any], LifecycleMedicationOrder],
    ) -> Dict[str, Any]:
        medication_id = getattr(medication, "medication_id", None) or str(uuid.uuid4())
        medication_name = getattr(medication, "name", None) or medication.get("name", medication.get("medication", "Unknown Medication"))

        start_date_obj = getattr(medication, "start_date", None)
        end_date_obj = getattr(medication, "end_date", None)
        if not isinstance(medication, LifecycleMedicationOrder):
            if start_date_obj is None:
                start_date_obj = medication.get("start_date")
            if end_date_obj is None:
                end_date_obj = medication.get("end_date")

        def _to_datetime_string(value: Any) -> Optional[str]:
            if value is None:
                return None
            if isinstance(value, datetime):
                return value.isoformat()
            if isinstance(value, date):
                return datetime.combine(value, datetime.min.time()).isoformat()
            if isinstance(value, str):
                return value
            return None

        start_iso = _to_datetime_string(start_date_obj) or datetime.now().isoformat()
        end_iso = _to_datetime_string(end_date_obj)

        rxnorm_code = None
        if isinstance(medication, LifecycleMedicationOrder):
            rxnorm_code = medication.rxnorm_code
        else:
            rxnorm_code = medication.get("rxnorm_code") or medication.get("rxnorm")

        medication_coding: List[Dict[str, Any]] = []
        if rxnorm_code:
            rxnorm_entry = self.rxnorm_lookup.get(str(rxnorm_code))
            display = rxnorm_entry.display if rxnorm_entry else medication_name
            coding_entry = {
                "system": "http://www.nlm.nih.gov/research/umls/rxnorm",
                "code": str(rxnorm_code),
                "display": display,
            }
            umls_concepts = self.umls_by_source.get(("RXNORM", str(rxnorm_code)), [])
            if umls_concepts:
                coding_entry.setdefault("extension", []).extend(
                    [
                        {
                            "url": "http://example.org/fhir/StructureDefinition/umls-concept",
                            "extension": [
                                {"url": "cui", "valueCode": concept.code},
                                {"url": "preferredName", "valueString": concept.display},
                                {
                                    "url": "semanticType",
                                    "valueString": concept.metadata.get("semantic_type", ""),
                                },
                            ],
                        }
                        for concept in umls_concepts
                    ]
                )
            medication_coding.append(coding_entry)

        medication_codeable = (
            {"coding": medication_coding}
            if medication_coding
            else {"text": medication_name}
        )

        status = "active"
        if isinstance(medication, LifecycleMedicationOrder):
            status = "completed" if medication.end_date else "active"
        else:
            status = medication.get("status") or ("completed" if medication.get("end_date") else "active")

        resource: Dict[str, Any] = {
            "resourceType": "MedicationStatement",
            "id": medication_id,
            "status": status,
            "medicationCodeableConcept": medication_codeable,
            "subject": {"reference": f"Patient/{patient_id}"},
        }

        if end_iso:
            resource["effectivePeriod"] = {
                "start": start_iso,
                "end": end_iso,
            }
        else:
            resource["effectiveDateTime"] = start_iso

        reason = None
        if isinstance(medication, LifecycleMedicationOrder):
            reason = medication.indication
        else:
            reason = medication.get("indication")
        if reason:
            resource["reasonCode"] = [{"text": reason}]

        therapeutic_class = None
        route = None
        monitoring_panels: List[str] = []
        if isinstance(medication, LifecycleMedicationOrder):
            therapeutic_class = medication.therapeutic_class
            metadata = medication.metadata or {}
            route = metadata.get("route")
            panels = metadata.get("monitoring_panels") or []
            if isinstance(panels, list):
                monitoring_panels = panels
        else:
            therapeutic_class = medication.get("therapeutic_class")
            route = medication.get("route")
            panels = medication.get("monitoring_panels", [])
            if isinstance(panels, list):
                monitoring_panels = panels
        extensions = []
        if therapeutic_class:
            extensions.append(
                {
                    "url": "http://example.org/fhir/StructureDefinition/therapeutic-class",
                    "valueString": therapeutic_class,
                }
            )
        if monitoring_panels:
            extensions.append(
                {
                    "url": "http://example.org/fhir/StructureDefinition/medication-monitoring",
                    "valueString": ",".join(sorted(set(monitoring_panels))),
                }
            )
        if extensions:
            resource.setdefault("extension", []).extend(extensions)

        dosage_entry: Dict[str, Any] = {}
        dosage_text = None
        if isinstance(medication, LifecycleMedicationOrder):
            dosage_text = medication.metadata.get("dosage")
        else:
            dosage_text = medication.get("dosage")
        if dosage_text:
            dosage_entry["text"] = dosage_text
        if route:
            dosage_entry["route"] = {"text": route}
        if dosage_entry:
            resource["dosage"] = [dosage_entry]

        return resource

    def create_immunization_resource(
        self,
        patient_id: str,
        immunization: Union[Dict[str, Any], ImmunizationRecord],
    ) -> Dict[str, Any]:
        if isinstance(immunization, ImmunizationRecord):
            metadata = dict(immunization.metadata)
            vaccine_name = immunization.name or metadata.get("vaccine", "Vaccine")
            occurrence = (
                immunization.date_administered.isoformat()
                if immunization.date_administered
                else datetime.now().isoformat()
            )
            cvx_code = immunization.cvx_code or metadata.get("cvx_code")
            rxnorm_code = immunization.rxnorm_code or metadata.get("rxnorm_code")
            lot_number = immunization.lot_number or metadata.get("lot_number")
            performer = immunization.performer or metadata.get("provider")
        else:
            metadata = immunization
            vaccine_name = metadata.get("vaccine") or metadata.get("name", "Vaccine")
            occurrence = metadata.get("date", datetime.now().isoformat())
            cvx_code = metadata.get("cvx_code")
            rxnorm_code = metadata.get("rxnorm_code") or metadata.get("rxnorm")
            lot_number = metadata.get("lot_number")
            performer = metadata.get("provider") or metadata.get("performer")

        coding: List[Dict[str, Any]] = []
        if cvx_code:
            coding.append(
                {
                    "system": "http://hl7.org/fhir/sid/cvx",
                    "code": cvx_code,
                    "display": vaccine_name,
                }
            )
        snomed_code = metadata.get("snomed_code")
        if snomed_code:
            coding.append(
                {
                    "system": "http://snomed.info/sct",
                    "code": snomed_code,
                    "display": vaccine_name,
                }
            )
        if rxnorm_code:
            coding.append(
                {
                    "system": "http://www.nlm.nih.gov/research/umls/rxnorm",
                    "code": str(rxnorm_code),
                    "display": vaccine_name,
                }
            )
        if not coding:
            coding.append(
                {
                    "system": "http://terminology.hl7.org/CodeSystem/data-absent-reason",
                    "code": "unknown",
                    "display": vaccine_name,
                }
            )

        route_text = metadata.get("route", "intramuscular")
        route_code_map = {
            "intramuscular": "IM",
            "subcutaneous": "SC",
            "intranasal": "NASAL",
            "oral": "PO",
        }
        route_element = None
        if route_text:
            route_element = {
                "coding": [
                    {
                        "system": "http://terminology.hl7.org/CodeSystem/v3-RouteOfAdministration",
                        "code": route_code_map.get(route_text.lower(), "IM"),
                        "display": route_text.title(),
                    }
                ],
                "text": route_text.title(),
            }

        site_text = metadata.get("site")
        site_element = None
        if site_text:
            site_element = {
                "coding": [
                    {
                        "system": "http://terminology.hl7.org/CodeSystem/v3-ParticipationTargetBodySite",
                        "code": site_text.lower().replace(" ", "-"),
                        "display": site_text.title(),
                    }
                ],
                "text": site_text.title(),
            }

        resource: Dict[str, Any] = {
            "resourceType": "Immunization",
            "id": metadata.get("immunization_id", str(uuid.uuid4())),
            "status": metadata.get("status", "completed"),
            "vaccineCode": {"coding": coding, "text": vaccine_name},
            "patient": {"reference": f"Patient/{patient_id}"},
            "occurrenceDateTime": occurrence,
            "primarySource": True,
        }

        if lot_number:
            resource["lotNumber"] = lot_number
        if performer:
            resource["performer"] = [{"actor": {"display": performer}}]
        if route_element:
            resource["route"] = route_element
        if site_element:
            resource["site"] = site_element

        dose_number = metadata.get("dose_number")
        series_total = metadata.get("series_total")
        series_id = metadata.get("series_id")
        if dose_number or series_total or series_id:
            protocol_entry: Dict[str, Any] = {}
            if series_id:
                protocol_entry["series"] = str(series_id)
            if dose_number:
                protocol_entry["doseNumberPositiveInt"] = int(dose_number)
            if series_total:
                protocol_entry["seriesDosesPositiveInt"] = int(series_total)
            resource["protocolApplied"] = [protocol_entry]

        return resource

    def create_care_plan_resource(
        self,
        patient_id: str,
        care_plan: Dict[str, Any],
    ) -> Dict[str, Any]:
        status_map = {
            "completed": "completed",
            "overdue": "active",
            "scheduled": "draft",
            "in-progress": "active",
        }
        status = status_map.get(str(care_plan.get("status", "scheduled")).lower(), "draft")
        title = f"{care_plan.get('condition', 'Care Plan')} - {care_plan.get('pathway_stage', 'Stage')}"
        period: Dict[str, Any] = {}
        start_date = care_plan.get("scheduled_date")
        if start_date:
            period["start"] = start_date
        due_date = care_plan.get("due_date")
        if due_date:
            period["end"] = due_date

        resource: Dict[str, Any] = {
            "resourceType": "CarePlan",
            "id": care_plan.get("care_plan_id", str(uuid.uuid4())),
            "status": status,
            "intent": "plan",
            "title": title,
            "subject": {"reference": f"Patient/{patient_id}"},
        }
        if period:
            resource["period"] = period

        condition_reference = care_plan.get("condition_id")
        if condition_reference:
            resource["addresses"] = [
                {
                    "reference": f"Condition/{condition_reference}",
                    "display": care_plan.get("condition"),
                }
            ]
        else:
            resource["addresses"] = [
                {
                    "display": care_plan.get("condition"),
                }
            ]

        category_text = care_plan.get("condition") or "Condition-focused"
        resource["category"] = [
            {
                "coding": [
                    {
                        "system": "http://terminology.hl7.org/CodeSystem/care-plan-category",
                        "code": "condition",
                        "display": "Condition-focused",
                    }
                ],
                "text": category_text,
            }
        ]

        notes = care_plan.get("notes") or ""
        if notes:
            resource.setdefault("note", []).append({"text": notes})

        quality_metric = care_plan.get("quality_metric")
        if quality_metric:
            resource.setdefault("extension", []).append(
                {
                    "url": "http://example.org/fhir/StructureDefinition/careplan-quality-metric",
                    "valueString": quality_metric,
                }
            )
        metric_status = care_plan.get("metric_status")
        if metric_status:
            resource.setdefault("extension", []).append(
                {
                    "url": "http://example.org/fhir/StructureDefinition/careplan-metric-status",
                    "valueString": metric_status,
                }
            )

        activities_source = care_plan.get("activities")
        activity_status_map = {
            "completed": "completed",
            "pending": "scheduled",
            "in-progress": "in-progress",
        }
        if isinstance(activities_source, list):
            for activity in activities_source:
                if isinstance(activity, dict):
                    detail_status = activity_status_map.get(activity.get("status", "pending"), "scheduled")
                    description = activity.get("display") or activity.get("code") or activity.get("type") or "Activity"
                    detail: Dict[str, Any] = {
                        "status": detail_status,
                        "description": description,
                    }
                    if activity.get("planned_date"):
                        detail["scheduledString"] = activity["planned_date"]
                    if activity.get("actual_date"):
                        detail["performedDateTime"] = activity["actual_date"]
                    resource.setdefault("activity", []).append({"detail": detail})
                else:
                    resource.setdefault("activity", []).append(
                        {
                            "detail": {
                                "status": "scheduled",
                                "description": str(activity),
                            }
                        }
                    )
        elif isinstance(activities_source, str) and activities_source:
            resource.setdefault("activity", []).append(
                {
                    "detail": {
                        "status": "scheduled",
                        "description": activities_source,
                    }
                }
            )

        care_team = care_plan.get("responsible_roles") or []
        if care_team:
            resource["contributor"] = [{"display": role} for role in care_team]

        return resource

    def create_observation_resource(
        self,
        patient_id: str,
        observation: LifecycleObservation,
    ) -> Dict[str, Any]:
        observation_id = observation.observation_id or str(uuid.uuid4())
        status = observation.status.lower() if observation.status else "final"
        if status not in {"registered", "preliminary", "final", "amended", "cancelled", "entered-in-error", "unknown"}:
            status = "final"

        loinc_code = observation.metadata.get("loinc_code") or observation.metadata.get("loinc")
        loinc_entry = self.loinc_lookup.get(str(loinc_code)) if loinc_code else None
        display = loinc_entry.display if loinc_entry else observation.name

        coding = {
            "system": "http://loinc.org" if loinc_code else "http://terminology.hl7.org/CodeSystem/data-absent-reason",
            "code": loinc_code or "unknown",
            "display": display,
        }

        if loinc_entry and loinc_entry.metadata.get("ncbi_url"):
            coding.setdefault("extension", []).append(
                {
                    "url": "https://www.ncbi.nlm.nih.gov/",
                    "valueUri": loinc_entry.metadata["ncbi_url"],
                }
            )

        observation_resource: Dict[str, Any] = {
            "resourceType": "Observation",
            "id": observation_id,
            "status": status,
            "code": {"coding": [coding]},
            "subject": {"reference": f"Patient/{patient_id}"},
        }

        if observation.effective_datetime:
            observation_resource["effectiveDateTime"] = observation.effective_datetime.isoformat()

        value_numeric = observation.metadata.get("value_numeric")
        if value_numeric is not None:
            try:
                numeric_value = float(value_numeric)
                value_payload: Dict[str, Any] = {"value": numeric_value}
                if observation.unit:
                    value_payload["unit"] = observation.unit
                    value_payload["system"] = "http://unitsofmeasure.org"
                observation_resource["valueQuantity"] = value_payload
            except (TypeError, ValueError):
                observation_resource["valueString"] = str(observation.value)
        elif observation.value is not None:
            observation_resource["valueString"] = str(observation.value)

        if observation.interpretation:
            observation_resource["interpretation"] = [
                {
                    "coding": [
                        {
                            "system": "http://terminology.hl7.org/CodeSystem/v3-ObservationInterpretation",
                            "code": observation.interpretation,
                        }
                    ]
                }
            ]

        if observation.reference_range:
            observation_resource["referenceRange"] = [observation.reference_range]

        if loinc_code and str(loinc_code) in self.vsac_by_code:
            for member in self.vsac_by_code[str(loinc_code)]:
                value_set_oid = member.metadata.get("value_set_oid")
                canonical = f"urn:oid:{value_set_oid}" if value_set_oid else None
                extensions = observation_resource.setdefault("extension", [])
                extension_payload = {
                    "url": "http://hl7.org/fhir/StructureDefinition/valueset-reference",
                }
                if canonical:
                    extension_payload["valueCanonical"] = canonical
                else:
                    extension_payload["valueString"] = member.metadata.get("value_set_name", "")
                extensions.append(extension_payload)

        return observation_resource

    def create_family_history_resource(
        self,
        patient_id: str,
        entry: FamilyHistoryEntry,
    ) -> Dict[str, Any]:
        resource_id = entry.family_history_id or str(uuid.uuid4())
        relation = entry.relation or "Unknown"
        recorded_date = entry.recorded_date.isoformat() if entry.recorded_date else datetime.now().date().isoformat()

        relationship_coding: List[Dict[str, Any]] = []
        if entry.relation_code:
            relationship_coding.append(
                {
                    "system": "http://terminology.hl7.org/CodeSystem/v3-RoleCode",
                    "code": entry.relation_code,
                    "display": relation,
                }
            )

        resource: Dict[str, Any] = {
            "resourceType": "FamilyMemberHistory",
            "id": resource_id,
            "status": "completed",
            "patient": {"reference": f"Patient/{patient_id}"},
            "date": recorded_date,
            "name": relation,
            "relationship": {
                "text": relation,
                "coding": relationship_coding,
            },
        }

        condition_component: Dict[str, Any] = {}
        if entry.condition_code:
            condition_component["code"] = {
                "coding": [
                    {
                        "system": entry.condition_system or "http://hl7.org/fhir/sid/icd-10-cm",
                        "code": entry.condition_code,
                        "display": entry.condition_display or entry.condition,
                    }
                ]
            }
        elif entry.condition or entry.condition_display:
            condition_component["code"] = {
                "text": entry.condition_display or entry.condition,
            }

        if entry.onset_age is not None:
            condition_component["onsetAge"] = {"value": entry.onset_age, "unit": "years"}

        notes: List[str] = []
        if entry.notes:
            notes.append(str(entry.notes))
        if entry.genetic_marker:
            notes.append(f"Genetic marker: {entry.genetic_marker}")
        if entry.risk_modifier is not None:
            notes.append(f"Risk modifier: {entry.risk_modifier}")
        if notes:
            condition_component["note"] = [{"text": "; ".join(notes)}]

        if condition_component:
            resource["condition"] = [condition_component]

        return resource

class HL7v2Formatter:
    """HL7 v2.x message formatter for Phase 2"""
    
    @staticmethod
    def _format_provider(provider: Optional[str]) -> str:
        if not provider:
            return "UNKNOWN^PROVIDER"
        cleaned = provider.replace("Dr.", "").replace("DR.", "").strip()
        if not cleaned:
            return "UNKNOWN^PROVIDER"
        parts = cleaned.split()
        if len(parts) == 1:
            return f"{parts[0].upper()}^"
        first = parts[0].upper()
        last = parts[-1].upper()
        return f"{last}^{first}"

    @staticmethod
    def create_adt_message(
        patient_record: Union[PatientRecord, LifecyclePatient],
        encounter: Dict[str, Any] = None,
        message_type: str = "A04",
    ) -> str:
        """Create HL7 v2 ADT (Admit/Discharge/Transfer) message"""
        from datetime import datetime

        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        message_control_id = f"MSG{random.randint(100000, 999999)}"

        segments = []

        if isinstance(patient_record, LifecyclePatient):
            identifiers = patient_record.identifiers
            mrn = identifiers.get("mrn") or identifiers.get("vista_id") or patient_record.patient_id
            ssn = identifiers.get("ssn", "")
            birthdate = patient_record.birth_date.strftime("%Y%m%d") if patient_record.birth_date else ""
            gender = patient_record.gender.upper()[:1] if patient_record.gender else "U"
            address_line = patient_record.address.get("line", "")
            address_city = patient_record.address.get("city", "")
            address_state = patient_record.address.get("state", "")
            address_zip = patient_record.address.get("postal_code", "")
            phone = patient_record.contact.get("phone", "")
            language = patient_record.language or ""
            marital_status = patient_record.marital_status or ""
            middle_name = patient_record.middle_name or ""
            death_record = patient_record.death
        else:
            mrn = patient_record.mrn or patient_record.generate_mrn()
            ssn = patient_record.ssn or ""
            birthdate = patient_record.birthdate.replace("-", "") if patient_record.birthdate else ""
            gender = patient_record.gender.upper()[0] if patient_record.gender else "U"
            address_line = patient_record.address
            address_city = patient_record.city
            address_state = patient_record.state
            address_zip = patient_record.zip
            phone = getattr(patient_record, "phone", "") or ""
            language = getattr(patient_record, "language", "")
            marital_status = getattr(patient_record, "marital_status", "")
            middle_name = getattr(patient_record, "middle_name", "")
            metadata = getattr(patient_record, "metadata", {})
            death_record = metadata.get("death_record") if isinstance(metadata, dict) else None

        death_indicator = "N"
        death_date_field = ""
        if death_record:
            if isinstance(death_record, dict):
                death_value = death_record.get("death_date")
            else:
                death_value = death_record.death_date.isoformat() if death_record.death_date else None
            if death_value:
                death_indicator = "Y"
                if isinstance(death_value, str):
                    cleaned = death_value.replace("-", "").replace(":", "").replace("T", "")
                    death_date_field = cleaned[:8]
                else:
                    death_date_field = death_value.strftime("%Y%m%d")

        # MSH - Message Header
        msh = (f"MSH|^~\\&|VistA|VA_FACILITY|Oracle|ORACLE_FACILITY|{timestamp}||"
               f"ADT^{message_type}|{message_control_id}|P|2.5")
        segments.append(msh)

        # EVN - Event Type  
        evn = f"EVN|{message_type}|{timestamp}|||"
        segments.append(evn)
        
        # PID - Patient Identification
        pid_segments = [
            "PID",
            "1",  # Set ID
            "",   # External ID
            f"{mrn}^^^VA^MR~{ssn}^^^USA^SS" if ssn else f"{mrn}^^^VA^MR",
            "",   # Alternate Patient ID
            f"{patient_record.last_name}^{patient_record.first_name}^{middle_name}",
            "",   # Mother's Maiden Name
            birthdate,
            gender,
            "",   # Patient Alias
            HL7v2Formatter._get_hl7_race_code(patient_record.race),
            f"{address_line}^^{address_city}^{address_state}^{address_zip}",
            "",   # County Code
            phone,
            "",   # Business Phone
            HL7v2Formatter._get_hl7_language_code(language),
            HL7v2Formatter._get_hl7_marital_code(marital_status),
            "",   # Religion
            f"{patient_record.patient_id}^^^VA^AN",  # Account Number
            ssn,
            "",   # Driver's License
            "",   # Mother's Identifier
            HL7v2Formatter._get_hl7_ethnicity_code(patient_record.ethnicity),
            "",   # Birth Place
            "",   # Multiple Birth Indicator
            "",   # Birth Order
            "",   # Citizenship
            "",   # Veterans Military Status
            "",   # Nationality
            death_date_field,
            death_indicator,
            "",   # Identity Unknown
            "",   # Identity Reliability
            "",   # Last Update Date
            "",   # Last Update Facility
            "",   # Species Code
            "",   # Breed Code
            "",   # Strain
            "",   # Production Class Code
            ""    # Tribal Citizenship
        ]
        
        pid = "|".join(pid_segments)
        segments.append(pid)

        allergies: List[Dict[str, Any]] = []
        if isinstance(patient_record, LifecyclePatient):
            allergies = getattr(patient_record, "allergies", []) or []
        else:
            allergies = getattr(patient_record, "allergies", []) or []

        type_map = {"drug": "DA", "food": "FA", "environment": "EA", "insect": "EA"}
        for idx, allergy in enumerate(allergies, start=1):
            severity = (allergy.get("severity") or "").upper()
            reaction = allergy.get("reaction", "")
            substance = allergy.get("substance", "")
            rx_code = allergy.get("rxnorm_code") or allergy.get("snomed_code") or ""
            coding_system = "RXN" if allergy.get("rxnorm_code") else "SCT" if allergy.get("snomed_code") else "TEXT"
            if not rx_code:
                rx_code = substance[:12].upper() if substance else "UNKNOWN"
            allergen_type = allergy.get("category", "")
            allergen_type_code = type_map.get(allergen_type, "MA")
            al1 = f"AL1|{idx}|{allergen_type_code}|{rx_code}^{substance}^{coding_system}|{severity}|{reaction}|"
            segments.append(al1)

        # PV1 - Patient Visit (if encounter provided)
        if encounter:
            service_category = encounter.get('service_category')
            if not service_category:
                encounter_class = encounter.get('encounter_class')
                if encounter_class == "emergency":
                    service_category = "E"
                elif encounter_class == "inpatient":
                    service_category = "I"
                else:
                    service_category = "A"

            patient_class = {
                "I": "I",
                "E": "E",
            }.get(service_category, "O")

            stop_code = encounter.get('clinic_stop') or "CLINIC"
            department = encounter.get('department') or encounter.get('clinic_stop_description') or "Clinic"
            assigned_location = f"{stop_code}^^^{department[:20]}"

            provider_field = HL7v2Formatter._format_provider(encounter.get('provider'))

            pv1_segments = [
                "PV1",
                "1",  # Set ID
                patient_class,
                assigned_location,
                "",   # Admission Type
                "",   # Preadmit Number
                "",   # Prior Patient Location
                provider_field,
                "",   # Referring Doctor
                "",   # Consulting Doctor
                stop_code,
                "",   # Temporary Location
                "",   # Preadmit Test Indicator
                "",   # Re-admission Indicator
                "",   # Admit Source
                "",   # Ambulatory Status
                "",   # VIP Indicator
                "",   # Admitting Doctor
                "",   # Patient Type
                "",   # Visit Number
                "",   # Financial Class
                "",   # Charge Price Indicator
                "",   # Courtesy Code
                "",   # Credit Rating
                "",   # Contract Code
                "",   # Contract Effective Date
                "",   # Contract Amount
                "",   # Contract Period
                "",   # Interest Code
                "",   # Transfer to Bad Debt Code
                "",   # Transfer to Bad Debt Date
                "",   # Bad Debt Agency Code
                "",   # Bad Debt Transfer Amount
                "",   # Bad Debt Recovery Amount
                "",   # Delete Account Indicator
                "",   # Delete Account Date
                "",   # Discharge Disposition
                "",   # Discharged to Location
                "",   # Diet Type
                "",   # Servicing Facility
                "",   # Bed Status
                "",   # Account Status
                "",   # Pending Location
                "",   # Prior Temporary Location
                encounter.get('date', '').replace('-', '') if encounter.get('date') else timestamp[:8],  # Admit Date/Time
                "",   # Discharge Date/Time
                "",   # Current Patient Balance
                "",   # Total Charges
                "",   # Total Adjustments
                "",   # Total Payments
                "",   # Alternate Visit ID
                "",   # Visit Indicator
                ""    # Other Healthcare Provider
            ]
            
            pv1 = "|".join(pv1_segments)
            segments.append(pv1)
        
        return "\r".join(segments)
    
    @staticmethod
    def create_oru_message(
        patient_record: Union[PatientRecord, LifecyclePatient], observations: list
    ) -> str:
        """Create HL7 v2 ORU (Observation Result) message for lab results"""
        from datetime import datetime

        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        message_control_id = f"LAB{random.randint(100000, 999999)}"

        segments = []

        if isinstance(patient_record, LifecyclePatient):
            identifiers = patient_record.identifiers
            mrn = identifiers.get("mrn") or identifiers.get("vista_id") or patient_record.patient_id
            ssn = identifiers.get("ssn", "")
            middle_name = patient_record.middle_name or ""
            birthdate = (
                patient_record.birth_date.strftime("%Y%m%d") if patient_record.birth_date else ""
            )
            gender = patient_record.gender.upper()[:1] if patient_record.gender else "U"
            address_line = patient_record.address.get("line", "")
            address_city = patient_record.address.get("city", "")
            address_state = patient_record.address.get("state", "")
            address_zip = patient_record.address.get("postal_code", "")
        else:
            mrn = patient_record.mrn or patient_record.generate_mrn()
            ssn = patient_record.ssn or ""
            middle_name = getattr(patient_record, "middle_name", "")
            birthdate = patient_record.birthdate.replace("-", "") if patient_record.birthdate else ""
            gender = patient_record.gender.upper()[0] if patient_record.gender else "U"
            address_line = patient_record.address
            address_city = patient_record.city
            address_state = patient_record.state
            address_zip = patient_record.zip

        # MSH - Message Header
        msh = (f"MSH|^~\\&|VistA|VA_FACILITY|LAB|LAB_FACILITY|{timestamp}||"
               f"ORU^R01|{message_control_id}|P|2.5")
        segments.append(msh)

        # PID - Patient Identification (same as ADT)
        identifier = f"{mrn}^^^VA^MR"
        if ssn:
            identifier = f"{identifier}~{ssn}^^^USA^SS"

        pid = (
            f"PID|1||{identifier}||{patient_record.last_name}^"
            f"{patient_record.first_name}^{middle_name}||{birthdate}|{gender}|||"
            f"{address_line}^^{address_city}^{address_state}^{address_zip}"
        )
        segments.append(pid)
        
        # OBR - Observation Request
        obr = (f"OBR|1|{random.randint(100000, 999999)}|{random.randint(100000, 999999)}|"
               f"CBC^Complete Blood Count^L|||{timestamp}||||||||||DOE^JOHN^A")
        segments.append(obr)
        
        # OBX - Observation/Result segments
        for i, obs in enumerate(observations[:5], 1):  # Limit to 5 observations
            obs_type = obs.get('type', 'Unknown')
            obs_value = obs.get('value', '')
            
            # Map observation types to LOINC codes
            loinc_code = HL7v2Formatter._get_loinc_code(obs_type)
            data_type = HL7v2Formatter._get_hl7_data_type(obs_type)
            units = HL7v2Formatter._get_observation_units(obs_type)
            
            obx = (f"OBX|{i}|{data_type}|{loinc_code}^{obs_type}^LN||{obs_value}|{units}||||F|||"
                   f"{timestamp}")
            segments.append(obx)
        
        return "\r".join(segments)
    
    @staticmethod
    def _get_hl7_race_code(race: str) -> str:
        """Map race to HL7 codes"""
        race_mapping = {
            "White": "2106-3^White^HL70005",
            "Black": "2054-5^Black or African American^HL70005", 
            "Asian": "2028-9^Asian^HL70005",
            "Hispanic": "2131-1^Other Race^HL70005",
            "Native American": "1002-5^American Indian or Alaska Native^HL70005",
            "Other": "2131-1^Other Race^HL70005"
        }
        return race_mapping.get(race, "2131-1^Other Race^HL70005")
    
    @staticmethod
    def _get_hl7_ethnicity_code(ethnicity: str) -> str:
        """Map ethnicity to HL7 codes"""
        return "2135-2^Hispanic or Latino^HL70189" if ethnicity == "Hispanic or Latino" else "2186-5^Not Hispanic or Latino^HL70189"
    
    @staticmethod
    def _get_hl7_language_code(language: str) -> str:
        """Map language to HL7 codes"""
        lang_mapping = {
            "English": "en^English^ISO639",
            "Spanish": "es^Spanish^ISO639",
            "Chinese": "zh^Chinese^ISO639",
            "French": "fr^French^ISO639",
            "German": "de^German^ISO639",
            "Vietnamese": "vi^Vietnamese^ISO639"
        }
        return lang_mapping.get(language, "en^English^ISO639")
    
    @staticmethod
    def _get_hl7_marital_code(marital_status: str) -> str:
        """Map marital status to HL7 codes"""
        marital_mapping = {
            "Never Married": "S^Single^HL70002",
            "Married": "M^Married^HL70002",
            "Divorced": "D^Divorced^HL70002",
            "Widowed": "W^Widowed^HL70002",
            "Separated": "A^Separated^HL70002"
        }
        return marital_mapping.get(marital_status, "U^Unknown^HL70002")
    
    @staticmethod
    def _get_loinc_code(observation_type: str) -> str:
        """Map observation types to LOINC codes"""
        loinc_mapping = {
            "Height": "8302-2",
            "Weight": "29463-7", 
            "Blood Pressure": "85354-9",
            "Heart Rate": "8867-4",
            "Temperature": "8310-5",
            "Hemoglobin A1c": "4548-4",
            "Cholesterol": "2093-3"
        }
        return loinc_mapping.get(observation_type, "8310-5")  # Default to temperature
    
    @staticmethod
    def _get_hl7_data_type(observation_type: str) -> str:
        """Get HL7 data type for observation"""
        if observation_type in ["Blood Pressure"]:
            return "ST"  # String
        else:
            return "NM"  # Numeric
    
    @staticmethod
    def _get_observation_units(observation_type: str) -> str:
        """Get units for observation values"""
        units_mapping = {
            "Height": "cm",
            "Weight": "kg",
            "Blood Pressure": "mmHg",
            "Heart Rate": "bpm",
            "Temperature": "Cel",
            "Hemoglobin A1c": "%",
            "Cholesterol": "mg/dL"
        }
        return units_mapping.get(observation_type, "")


class VistaReferenceRegistry:
    """Minimal in-memory registry for FileMan pointer lookups."""

    DEFAULT_STATE = "MA"
    STATE_IEN_MAP: Dict[str, int] = {
        "AL": 1,
        "AK": 2,
        "AZ": 3,
        "AR": 4,
        "CA": 5,
        "CO": 6,
        "CT": 7,
        "DE": 8,
        "DC": 9,
        "FL": 10,
        "GA": 11,
        "HI": 12,
        "ID": 13,
        "IL": 14,
        "IN": 15,
        "IA": 16,
        "KS": 17,
        "KY": 18,
        "LA": 19,
        "ME": 20,
        "MD": 21,
        "MA": 22,
        "MI": 23,
        "MN": 24,
        "MS": 25,
        "MO": 26,
        "MT": 27,
        "NE": 28,
        "NV": 29,
        "NH": 30,
        "NJ": 31,
        "NM": 32,
        "NY": 33,
        "NC": 34,
        "ND": 35,
        "OH": 36,
        "OK": 37,
        "OR": 38,
        "PA": 39,
        "RI": 40,
        "SC": 41,
        "SD": 42,
        "TN": 43,
        "TX": 44,
        "UT": 45,
        "VT": 46,
        "VA": 47,
        "WA": 48,
        "WV": 49,
        "WI": 50,
        "WY": 51,
        "PR": 52,
        "VI": 53,
        "GU": 54,
        "AS": 55,
        "MP": 56,
    }

    def __init__(self) -> None:
        self.icd10_lookup: Dict[str, str] = {}
        self.narrative_lookup: Dict[str, str] = {}
        self.location_lookup: Dict[str, str] = {}
        self.stop_code_lookup: Dict[str, str] = {}
        self.drug_lookup: Dict[str, Dict[str, str]] = {}
        self.lab_lookup: Dict[str, Dict[str, str]] = {}
        self.allergen_lookup: Dict[str, Dict[str, str]] = {}
        self.immunization_lookup: Dict[str, Dict[str, str]] = {}
        self.family_relation_lookup: Dict[str, str] = {}
        self._icd_counter = 400000
        self._narrative_counter = 500000
        self._location_counter = 600000
        self._drug_counter = 700000
        self._lab_counter = 800000
        self._allergen_counter = 900000
        self._immunization_counter = 950000
        self._relation_counter = 980000

    def _allocate(self, counter_attr: str) -> str:
        value = getattr(self, counter_attr)
        setattr(self, counter_attr, value + 1)
        return str(value)

    def get_state_ien(self, state: Optional[str]) -> str:
        key = (state or self.DEFAULT_STATE).upper()
        if key not in self.STATE_IEN_MAP:
            key = self.DEFAULT_STATE
        return str(self.STATE_IEN_MAP.get(key, ""))

    def get_icd10_ien(self, code: Optional[str]) -> str:
        if not code:
            return ""
        if code not in self.icd10_lookup:
            self.icd10_lookup[code] = self._allocate("_icd_counter")
        return self.icd10_lookup[code]

    def get_narrative_ien(self, narrative: Optional[str]) -> str:
        if not narrative:
            return ""
        if narrative not in self.narrative_lookup:
            self.narrative_lookup[narrative] = self._allocate("_narrative_counter")
        return self.narrative_lookup[narrative]

    def get_location_ien(self, name: Optional[str]) -> str:
        if not name:
            return ""
        if name not in self.location_lookup:
            self.location_lookup[name] = self._allocate("_location_counter")
        return self.location_lookup[name]

    def register_stop_code(self, code: Optional[str], description: str) -> str:
        if not code:
            return ""
        normalized = str(code)
        if normalized not in self.stop_code_lookup:
            self.stop_code_lookup[normalized] = description
        return normalized

    def get_drug_ien(self, name: Optional[str], rxnorm: Optional[str] = None) -> str:
        if not name and not rxnorm:
            return ""
        display_name = name or (f"Drug {rxnorm}" if rxnorm else "Unknown Drug")
        key = (rxnorm or display_name).upper()
        entry = self.drug_lookup.get(key)
        if entry is None:
            ien = self._allocate("_drug_counter")
            self.drug_lookup[key] = {
                "ien": ien,
                "name": display_name,
                "rxnorm": rxnorm or "",
            }
            return ien
        if name and not entry.get("name"):
            entry["name"] = name
        return entry["ien"]

    def get_lab_test_ien(self, name: Optional[str], loinc: Optional[str] = None) -> str:
        if not name and not loinc:
            return ""
        display_name = name or (f"LOINC {loinc}" if loinc else "Unknown Test")
        key = (loinc or display_name).upper()
        entry = self.lab_lookup.get(key)
        if entry is None:
            ien = self._allocate("_lab_counter")
            self.lab_lookup[key] = {
                "ien": ien,
                "name": display_name,
                "loinc": loinc or "",
            }
            return ien
        if name and not entry.get("name"):
            entry["name"] = name
        return entry["ien"]

    def get_allergen_ien(
        self,
        name: Optional[str],
        rxnorm: Optional[str] = None,
        unii: Optional[str] = None,
    ) -> str:
        if not name and not rxnorm and not unii:
            return ""
        display_name = name or rxnorm or unii or "Unknown Allergen"
        key = "|".join(filter(None, [rxnorm, unii, display_name])).upper()
        entry = self.allergen_lookup.get(key)
        if entry is None:
            ien = self._allocate("_allergen_counter")
            self.allergen_lookup[key] = {
                "ien": ien,
                "name": display_name,
                "rxnorm": rxnorm or "",
                "unii": unii or "",
            }
            return ien
        if name and not entry.get("name"):
            entry["name"] = name
        return entry["ien"]

    def get_immunization_ien(
        self,
        name: Optional[str],
        cvx_code: Optional[str] = None,
        rxnorm_code: Optional[str] = None,
    ) -> str:
        if not name and not cvx_code and not rxnorm_code:
            return ""
        key = (cvx_code or rxnorm_code or name or "").upper()
        entry = self.immunization_lookup.get(key)
        if entry is None:
            ien = self._allocate("_immunization_counter")
            self.immunization_lookup[key] = {
                "ien": ien,
                "name": name or f"IMM {ien}",
                "cvx": cvx_code or "",
                "rxnorm": rxnorm_code or "",
            }
            return ien
        if name and not entry.get("name"):
            entry["name"] = name
        if cvx_code and not entry.get("cvx"):
            entry["cvx"] = cvx_code
        if rxnorm_code and not entry.get("rxnorm"):
            entry["rxnorm"] = rxnorm_code
        return entry["ien"]

    def get_family_relation_ien(self, relation: Optional[str]) -> str:
        if not relation:
            return ""
        key = relation.strip()
        if not key:
            return ""
        if key not in self.family_relation_lookup:
            self.family_relation_lookup[key] = self._allocate("_relation_counter")
        return self.family_relation_lookup[key]

    def build_reference_globals(self, sanitize: Callable[[str], str]) -> Dict[str, str]:
        globals_dict: Dict[str, str] = {}
        for code, ien in self.icd10_lookup.items():
            globals_dict[f"^ICD9({ien},0)"] = code
        for narrative, ien in self.narrative_lookup.items():
            globals_dict[f"^AUTNPOV({ien},0)"] = sanitize(narrative)
        for name, ien in self.location_lookup.items():
            globals_dict[f"^AUTTLOC({ien},0)"] = sanitize(name)
        for code, description in self.stop_code_lookup.items():
            sanitized = sanitize(description) or "Unknown Clinic"
            globals_dict[f"^DIC(40.7,{code},0)"] = f"{code}^{sanitized}"
            globals_dict[f'^DIC(40.7,"B","{sanitized}",{code})'] = ""
        for entry in self.drug_lookup.values():
            ien = entry["ien"]
            name = sanitize(entry.get("name", "")) or f"DRUG {ien}"
            node_value = f"{name}^{entry.get('rxnorm', '')}"
            globals_dict[f"^PSDRUG({ien},0)"] = node_value
            globals_dict[f'^PSDRUG("B","{name}",{ien})'] = ""
        for entry in self.lab_lookup.values():
            ien = entry["ien"]
            name = sanitize(entry.get("name", "")) or f"LAB {ien}"
            node_value = f"{name}^{entry.get('loinc', '')}"
            globals_dict[f"^LAB(60,{ien},0)"] = node_value
            globals_dict[f'^LAB(60,"B","{name}",{ien})'] = ""
        for entry in self.allergen_lookup.values():
            ien = entry["ien"]
            name = sanitize(entry.get("name", "")) or f"ALLERGEN {ien}"
            metadata = entry.get("rxnorm") or entry.get("unii") or ""
            node_value = f"{name}^{metadata}"
            globals_dict[f"^GMR(120.82,{ien},0)"] = node_value
            globals_dict[f'^GMR(120.82,"B","{name}",{ien})'] = ""
        for entry in self.immunization_lookup.values():
            ien = entry["ien"]
            name = sanitize(entry.get("name", "")) or f"IMMUNIZATION {ien}"
            cvx = entry.get("cvx", "")
            rxnorm = entry.get("rxnorm", "")
            node_value = f"{name}^{cvx}"
            if rxnorm:
                node_value = f"{node_value}^{rxnorm}"
            globals_dict[f"^AUTTIMM({ien},0)"] = node_value
            globals_dict[f'^AUTTIMM("B","{name}",{ien})'] = ""
        for relation, ien in self.family_relation_lookup.items():
            name = sanitize(relation) or relation or f"RELATION {ien}"
            globals_dict[f"^AUTTRLSH({ien},0)"] = name
            globals_dict[f'^AUTTRLSH("B","{name}",{ien})'] = ""
        return globals_dict

    def header_entries(self, fm_date: str) -> Dict[str, str]:
        headers: Dict[str, str] = {}
        if self.icd10_lookup:
            headers["^ICD9(0)"] = f"ICD DIAGNOSIS^80^{max(int(v) for v in self.icd10_lookup.values())}^{fm_date}"
        if self.narrative_lookup:
            headers["^AUTNPOV(0)"] = f"PROVIDER NARRATIVE^9999999.27^{max(int(v) for v in self.narrative_lookup.values())}^{fm_date}"
        if self.location_lookup:
            headers["^AUTTLOC(0)"] = f"LOCATION^9999999.06^{max(int(v) for v in self.location_lookup.values())}^{fm_date}"
        if self.stop_code_lookup:
            numeric_codes = [int(code) for code in self.stop_code_lookup.keys() if str(code).isdigit()]
            if numeric_codes:
                headers["^DIC(40.7,0)"] = f"CLINIC STOP^40.7^{max(numeric_codes)}^{fm_date}"
        if self.drug_lookup:
            headers["^PSDRUG(0)"] = f"DRUG^50^{max(int(entry['ien']) for entry in self.drug_lookup.values())}^{fm_date}"
        if self.lab_lookup:
            headers["^LAB(60,0)"] = f"LAB TEST^60^{max(int(entry['ien']) for entry in self.lab_lookup.values())}^{fm_date}"
        if self.allergen_lookup:
            headers["^GMR(120.82,0)"] = f"ALLERGEN^120.82^{max(int(entry['ien']) for entry in self.allergen_lookup.values())}^{fm_date}"
        if self.immunization_lookup:
            headers["^AUTTIMM(0)"] = f"IMMUNIZATION^9999999.14^{max(int(entry['ien']) for entry in self.immunization_lookup.values())}^{fm_date}"
        if self.family_relation_lookup:
            headers["^AUTTRLSH(0)"] = f"RELATION^9999999.05^{max(int(ien) for ien in self.family_relation_lookup.values())}^{fm_date}"
        return headers


class VistaFormatter:
    """VistA MUMPS global formatter for Phase 3 - Production accurate VA migration simulation"""

    LEGACY_MODE = "legacy"
    FILEMAN_INTERNAL_MODE = "fileman_internal"

    ICD_FALLBACKS: Dict[str, str] = {
        "Stroke": "I63.9",
        "Cerebrovascular Accident": "I63.9",
        "Heart Attack": "I21.3",
        "Myocardial Infarction": "I21.3",
    }
    
    @staticmethod
    def vista_date_format(date_str: str) -> str:
        """Convert ISO date to VistA internal date format (days since 1841-01-01)"""
        if not date_str:
            return ""
        
        try:
            from datetime import date
            if isinstance(date_str, str):
                input_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            else:
                input_date = date_str
            
            # VistA uses days since 1841-01-01 (FileMan date format)
            vista_epoch = date(1841, 1, 1)
            days_since_epoch = (input_date - vista_epoch).days
            return str(days_since_epoch)
        except:
            return ""
    
    @staticmethod
    def vista_datetime_format(date_str: str, time_str: str = None) -> str:
        """Convert to VistA datetime format (YYYMMDD.HHMMSS where YYY is years since 1700)"""
        if not date_str:
            return ""
            
        try:
            if isinstance(date_str, str):
                input_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            else:
                input_date = date_str
            
            # VistA datetime: years since 1700 + MMDD.HHMMSS
            years_since_1700 = input_date.year - 1700
            month_day = f"{input_date.month:02d}{input_date.day:02d}"
            
            if time_str:
                time_part = time_str.replace(":", "")
            else:
                # Default to noon for encounters
                time_part = "120000"
            
            return f"{years_since_1700}{month_day}.{time_part}"
        except:
            return ""
    
    @staticmethod
    def sanitize_mumps_string(text: str) -> str:
        """Sanitize string for MUMPS global storage - handle special characters"""
        if not text:
            return ""

        # Remove or replace characters that would break MUMPS syntax
        sanitized = str(text).replace("^", " ").replace('"', "'").replace("\r", "").replace("\n", " ")
        # Limit length for FileMan fields
        return sanitized[:30] if len(sanitized) > 30 else sanitized

    @staticmethod
    def format_phone_number(text: Optional[str]) -> str:
        if not text:
            return ""
        digits = re.sub(r"\D", "", str(text))
        formatted = str(text)
        if len(digits) == 10:
            formatted = f"{digits[:3]}-{digits[3:6]}-{digits[6:]}"
        elif len(digits) == 11:
            formatted = f"+{digits[0]}-{digits[1:4]}-{digits[4:7]}-{digits[7:]}"
        return VistaFormatter.sanitize_mumps_string(formatted)

    @staticmethod
    def generate_vista_ien() -> str:
        """Generate VistA Internal Entry Number (IEN)"""
        return str(random.randint(1, 999999))

    @staticmethod
    def fileman_date_format(date_str: Optional[str]) -> str:
        if not date_str:
            return ""
        try:
            if isinstance(date_str, str):
                dt = datetime.strptime(date_str, "%Y-%m-%d").date()
            else:
                dt = date_str
            years = dt.year - 1700
            return f"{years}{dt.month:02d}{dt.day:02d}"
        except Exception:
            return ""

    @staticmethod
    def fileman_datetime_format(date_str: Optional[str], time_str: Optional[str] = None) -> str:
        if not date_str:
            return ""
        try:
            if isinstance(date_str, str):
                dt = datetime.strptime(date_str, "%Y-%m-%d").date()
            else:
                dt = date_str
            years = dt.year - 1700
            digits = time_str.replace(":", "") if time_str else "120000"
            digits = (digits + "000000")[:6]
            return f"{years}{dt.month:02d}{dt.day:02d}.{digits}"
        except Exception:
            return ""

    @staticmethod
    def _normalize_sex(value: Optional[str]) -> str:
        normalized = (value or "").strip().lower()
        if normalized in {"male", "m"}:
            return "M"
        if normalized in {"female", "f"}:
            return "F"
        return "F"

    @staticmethod
    def create_dpt_global(patient_record: PatientRecord) -> Dict[str, str]:
        """Create ^DPT Patient File #2 global structure"""
        vista_ien = patient_record.vista_id or VistaFormatter.generate_vista_ien()
        
        # Patient name in LAST,FIRST MIDDLE format
        full_name = f"{patient_record.last_name.upper()},{patient_record.first_name.upper()}"
        if patient_record.middle_name:
            full_name += f" {patient_record.middle_name.upper()}"
        full_name = VistaFormatter.sanitize_mumps_string(full_name)
        
        # Convert gender to VistA format
        vista_sex = "M" if patient_record.gender.lower() in ["male", "m"] else "F"
        
        # Convert date of birth to VistA format
        vista_dob = VistaFormatter.vista_date_format(patient_record.birthdate)
        
        # Sanitize SSN (remove dashes)
        vista_ssn = patient_record.ssn.replace("-", "") if patient_record.ssn else ""
        
        # Convert marital status to VistA codes
        marital_mapping = {
            "Never Married": "S",
            "Married": "M", 
            "Divorced": "D",
            "Widowed": "W",
            "Separated": "A"
        }
        vista_marital = marital_mapping.get(patient_record.marital_status, "U")
        
        # Convert race to VistA codes (simplified)
        race_mapping = {
            "White": "5",
            "Black": "3",
            "Asian": "6", 
            "Hispanic": "7",
            "Native American": "1",
            "Other": "8"
        }
        vista_race = race_mapping.get(patient_record.race, "8")
        
        globals_dict = {}
        
        # Main patient record - ^DPT(IEN,0)
        # Format: NAME^SEX^DOB^EMPLOYMENT^MARITAL^RACE^OCCUPATION^RELIGION^SSN
        zero_node = f"{full_name}^{vista_sex}^{vista_dob}^^^{vista_race}^^{vista_ssn}"
        globals_dict[f"^DPT({vista_ien},0)"] = zero_node
        
        # Address information - ^DPT(IEN,.11)
        if patient_record.address:
            address_node = f"{VistaFormatter.sanitize_mumps_string(patient_record.address)}^{VistaFormatter.sanitize_mumps_string(patient_record.city)}^{patient_record.state}^{patient_record.zip}"
            globals_dict[f"^DPT({vista_ien},.11)"] = address_node
        
        # Phone number - ^DPT(IEN,.13)
        if patient_record.phone:
            globals_dict[f"^DPT({vista_ien},.13)"] = VistaFormatter.format_phone_number(patient_record.phone)
        
        # Cross-reference: "B" index for name lookup
        globals_dict[f'^DPT("B","{full_name}",{vista_ien})'] = ""
        
        # Cross-reference: SSN index
        if vista_ssn:
            globals_dict[f'^DPT("SSN","{vista_ssn}",{vista_ien})'] = ""
        
        # Cross-reference: DOB index  
        if vista_dob:
            globals_dict[f'^DPT("DOB",{vista_dob},{vista_ien})'] = ""
        
        return globals_dict
    
    @staticmethod
    def create_aupnvsit_global(patient_record: PatientRecord, encounter: Dict[str, Any]) -> Dict[str, str]:
        """Create ^AUPNVSIT Visit File #9000010 global structure"""
        visit_ien = VistaFormatter.generate_vista_ien()
        patient_ien = patient_record.vista_id or VistaFormatter.generate_vista_ien()
        
        # Visit date/time in VistA format
        visit_datetime = VistaFormatter.vista_datetime_format(encounter.get('date', ''))
        
        # Map encounter types to VistA stop codes (simplified)
        stop_code = encounter.get('clinic_stop')
        stop_description = encounter.get('clinic_stop_description') or encounter.get('department') or encounter.get('type', 'Unknown Clinic')
        if not stop_code:
            stop_code_mapping = {
                "Wellness Visit": "323",
                "Emergency": "130",
                "Follow-up": "323",
                "Specialist": "301",
                "Lab": "175",
                "Surgery": "162",
            }
            stop_code = stop_code_mapping.get(encounter.get('type', ''), "323")

        # Service category mapping
        service_category = encounter.get('service_category')
        if not service_category:
            encounter_class = encounter.get('encounter_class')
            if encounter_class == "emergency":
                service_category = "E"
            elif encounter_class == "inpatient":
                service_category = "I"
            else:
                service_category = "A"

        globals_dict = {}

        # Main visit record - ^AUPNVSIT(IEN,0)
        # Format: PATIENT_IEN^VISIT_DATE^VISIT_TYPE^STOP_CODE^SERVICE_CATEGORY
        zero_node = f"{patient_ien}^{visit_datetime}^{service_category}^{stop_code}^{encounter.get('encounter_id', '')}"
        globals_dict[f"^AUPNVSIT({visit_ien},0)"] = zero_node
        
        # Visit location - ^AUPNVSIT(IEN,.06)
        if encounter.get('location'):
            globals_dict[f"^AUPNVSIT({visit_ien},.06)"] = VistaFormatter.sanitize_mumps_string(encounter.get('location', ''))

        # Cross-reference: "B" index by patient and date
        globals_dict[f'^AUPNVSIT("B",{patient_ien},{visit_datetime},{visit_ien})'] = ""

        # Cross-reference: Date index
        globals_dict[f'^AUPNVSIT("D",{visit_datetime},{visit_ien})'] = ""

        # Cross-reference: stop code
        if stop_code:
            globals_dict[f'^AUPNVSIT("AE",{stop_code},{visit_ien})'] = ""

        return globals_dict
    
    @staticmethod 
    def create_aupnprob_global(patient_record: PatientRecord, condition: Dict[str, Any]) -> Dict[str, str]:
        """Create ^AUPNPROB Problem List File #9000011 global structure"""
        problem_ien = VistaFormatter.generate_vista_ien()
        patient_ien = patient_record.vista_id or VistaFormatter.generate_vista_ien()
        
        # Problem onset date
        onset_date = VistaFormatter.vista_date_format(condition.get('onset_date', ''))
        
        # Problem status mapping
        status_mapping = {
            "active": "A",
            "resolved": "I",  # Inactive
            "remission": "A"
        }
        problem_status = status_mapping.get(condition.get('status', 'active'), "A")
        
        # Get ICD codes from existing mappings
        condition_name = condition.get('name', '')
        icd_code = ""
        if condition_name in TERMINOLOGY_MAPPINGS.get('conditions', {}):
            icd_code = TERMINOLOGY_MAPPINGS['conditions'][condition_name].get('icd10', '')
        
        globals_dict = {}
        
        # Main problem record - ^AUPNPROB(IEN,0)
        # Format: PATIENT_IEN^PROBLEM_TEXT^STATUS^ONSET_DATE^ICD_CODE
        problem_text = VistaFormatter.sanitize_mumps_string(condition_name)
        zero_node = f"{patient_ien}^{problem_text}^{problem_status}^{onset_date}^{icd_code}"
        globals_dict[f"^AUPNPROB({problem_ien},0)"] = zero_node
        
        # Problem narrative - ^AUPNPROB(IEN,.05)
        if condition_name:
            globals_dict[f"^AUPNPROB({problem_ien},.05)"] = problem_text
        
        # Cross-reference: "B" index by patient
        globals_dict[f'^AUPNPROB("B",{patient_ien},{problem_ien})'] = ""
        
        # Cross-reference: Status index
        globals_dict[f'^AUPNPROB("S","{problem_status}",{patient_ien},{problem_ien})'] = ""
        
        # Cross-reference: ICD index
        if icd_code:
            globals_dict[f'^AUPNPROB("ICD","{icd_code}",{patient_ien},{problem_ien})'] = ""
        
        return globals_dict
    
    @staticmethod
    def _export_legacy(patients: List[PatientRecord], encounters: List[Dict], conditions: List[Dict], output_file: str):
        """Legacy export using string pointers for cross-system compatibility."""
        all_globals = {}
        
        print(f"Generating VistA MUMPS globals for {len(patients)} patients...")
        
        # Process patients
        for patient in tqdm(patients, desc="Creating VistA patient globals", unit="patients"):
            patient_globals = VistaFormatter.create_dpt_global(patient)
            all_globals.update(patient_globals)
        
        # Process encounters
        encounter_map = {}
        for encounter in encounters:
            patient_id = encounter.get('patient_id')
            if patient_id not in encounter_map:
                encounter_map[patient_id] = []
            encounter_map[patient_id].append(encounter)
        
        for patient in tqdm(patients, desc="Creating VistA encounter globals", unit="patients"):
            patient_encounters = encounter_map.get(patient.patient_id, [])
            for encounter in patient_encounters:
                visit_globals = VistaFormatter.create_aupnvsit_global(patient, encounter)
                all_globals.update(visit_globals)
        
        # Process conditions
        condition_map = {}
        for condition in conditions:
            patient_id = condition.get('patient_id')
            if patient_id not in condition_map:
                condition_map[patient_id] = []
            condition_map[patient_id].append(condition)
        
        for patient in tqdm(patients, desc="Creating VistA condition globals", unit="patients"):
            patient_conditions = condition_map.get(patient.patient_id, [])
            for condition in patient_conditions:
                problem_globals = VistaFormatter.create_aupnprob_global(patient, condition)
                all_globals.update(problem_globals)
        
        # Write to file in proper MUMPS global syntax
        with open(output_file, 'w') as f:
            f.write(";; VistA MUMPS Global Export for Synthetic Patient Data\n")
            f.write(f";; Generated on {datetime.now().isoformat()}\n")
            f.write(f";; Total global nodes: {len(all_globals)}\n")
            f.write(";;\n")
            
            # Sort globals for consistent output
            sorted_globals = sorted(all_globals.items())
            
            for global_ref, value in sorted_globals:
                if value:
                    f.write(f'S {global_ref}="{value}"\n')
                else:
                    f.write(f'S {global_ref}=""\n')
        
        print(f"VistA MUMPS globals exported to {output_file} ({len(all_globals)} global nodes)")
        
        # Generate summary statistics
        dpt_count = sum(1 for k in all_globals.keys() if k.startswith("^DPT(") and ",0)" in k)
        visit_count = sum(1 for k in all_globals.keys() if k.startswith("^AUPNVSIT(") and ",0)" in k)
        problem_count = sum(1 for k in all_globals.keys() if k.startswith("^AUPNPROB(") and ",0)" in k)
        
        return {
            "total_globals": len(all_globals),
            "patient_records": dpt_count,
            "visit_records": visit_count, 
            "problem_records": problem_count,
            "cross_references": len(all_globals) - dpt_count - visit_count - problem_count
        }

    @staticmethod
    def _export_fileman_internal(
        patients: List[PatientRecord],
        encounters: List[Dict],
        conditions: List[Dict],
        medications: List[Dict],
        observations: List[Dict],
        allergies: List[Dict],
        immunizations: List[Dict],
        family_history: List[Dict],
        deaths: List[Dict],
        output_file: str,
    ) -> Dict[str, int]:
        print(f"Generating VistA MUMPS globals for {len(patients)} patients (FileMan mode)...")

        registry = VistaReferenceRegistry()
        all_globals: Dict[str, str] = {}

        patient_iens: Set[int] = set()
        visit_iens: Set[int] = set()
        problem_iens: Set[int] = set()
        visit_map: Dict[str, str] = {}
        problem_map: Dict[str, str] = {}
        medication_iens: Set[int] = set()
        lab_iens: Set[int] = set()
        allergy_iens: Set[int] = set()
        immunization_iens: Set[int] = set()
        family_history_iens: Set[int] = set()
        medication_map: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        observation_map: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        allergy_map: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        immunization_map: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        family_history_map: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        medication_vista_map: Dict[str, str] = {}
        lab_vista_map: Dict[str, str] = {}
        allergy_vista_map: Dict[str, str] = {}
        immunization_vista_map: Dict[str, str] = {}
        family_history_vista_map: Dict[str, str] = {}

        def _ensure_unique_ien(target_set: Set[int]) -> str:
            candidate = VistaFormatter.generate_vista_ien()
            while int(candidate) in target_set:
                candidate = VistaFormatter.generate_vista_ien()
            target_set.add(int(candidate))
            return candidate

        for medication in medications or []:
            patient_id = medication.get('patient_id')
            if patient_id:
                medication_map[patient_id].append(medication)

        for observation in observations or []:
            patient_id = observation.get('patient_id')
            if patient_id:
                observation_map[patient_id].append(observation)

        for allergy in allergies or []:
            patient_id = allergy.get('patient_id')
            if patient_id:
                allergy_map[patient_id].append(allergy)

        for immunization in immunizations or []:
            patient_id = immunization.get('patient_id')
            if patient_id:
                immunization_map[patient_id].append(immunization)

        for entry in family_history or []:
            patient_id = entry.get('patient_id')
            if patient_id:
                family_history_map[patient_id].append(entry)

        # Patient structures
        for patient in tqdm(patients, desc="Creating VistA patient globals", unit="patients"):
            vista_ien = patient.generate_vista_id()
            try:
                patient_iens.add(int(vista_ien))
            except ValueError:
                pass

            full_name = f"{patient.last_name.upper()},{patient.first_name.upper()}"
            if patient.middle_name:
                full_name += f" {patient.middle_name.upper()}"
            full_name = VistaFormatter.sanitize_mumps_string(full_name)

            vista_sex = VistaFormatter._normalize_sex(patient.gender)
            vista_dob = VistaFormatter.fileman_date_format(patient.birthdate)
            vista_ssn = patient.ssn.replace("-", "") if patient.ssn else ""

            race_mapping = {
                "White": "5",
                "Black": "3",
                "Asian": "6",
                "Hispanic": "7",
                "Native American": "1",
                "Other": "8",
            }
            vista_race = race_mapping.get(patient.race, "8")

            zero_node = f"{full_name}^{vista_sex}^{vista_dob}^^^{vista_race}^^{vista_ssn}"
            all_globals[f"^DPT({vista_ien},0)"] = zero_node

            if patient.address:
                state_piece = registry.get_state_ien(patient.state)
                address_node = (
                    f"{VistaFormatter.sanitize_mumps_string(patient.address)}^"
                    f"{VistaFormatter.sanitize_mumps_string(patient.city)}^"
                    f"{state_piece}^{patient.zip}"
                )
                all_globals[f"^DPT({vista_ien},.11)"] = address_node

            if patient.phone:
                all_globals[f"^DPT({vista_ien},.13)"] = VistaFormatter.format_phone_number(patient.phone)

            all_globals[f'^DPT("B","{full_name}",{vista_ien})'] = ""
            if vista_ssn:
                all_globals[f'^DPT("SSN","{vista_ssn}",{vista_ien})'] = ""
            if vista_dob:
                all_globals[f'^DPT("DOB",{vista_dob},{vista_ien})'] = ""

            death_record = patient.metadata.get("death_record") if hasattr(patient, "metadata") else None
            if not death_record:
                death_record = getattr(patient, "death_record", None)
            if isinstance(death_record, dict):
                death_date_raw = death_record.get("death_date")
                primary_cause_code = death_record.get("primary_cause_code")
                manner = death_record.get("manner_of_death")
                cause_text = death_record.get("primary_cause_description")
            else:
                death_date_raw = getattr(death_record, "death_date", None)
                primary_cause_code = getattr(death_record, "primary_cause_code", None)
                manner = getattr(death_record, "manner_of_death", None)
                cause_text = getattr(death_record, "primary_cause_description", None)

            death_date_fm = VistaFormatter.fileman_date_format(death_date_raw) if death_date_raw else ""
            if death_date_fm:
                all_globals[f"^DPT({vista_ien},.35)"] = death_date_fm
            if primary_cause_code:
                cause_ien = registry.get_icd10_ien(primary_cause_code)
                if cause_ien:
                    all_globals[f"^DPT({vista_ien},.351)"] = cause_ien
            if manner:
                all_globals[f"^DPT({vista_ien},.352)"] = VistaFormatter.sanitize_mumps_string(manner)
            if cause_text:
                all_globals[f"^DPT({vista_ien},.353)"] = VistaFormatter.sanitize_mumps_string(cause_text)

        # Index encounters by patient
        encounter_map: Dict[str, List[Dict[str, Any]]] = {}
        for encounter in encounters:
            encounter_map.setdefault(encounter.get('patient_id'), []).append(encounter)

        for patient in tqdm(patients, desc="Creating VistA encounter globals", unit="patients"):
            vista_ien = patient.vista_id or patient.generate_vista_id()
            patient_encounters = encounter_map.get(patient.patient_id, [])
            for encounter in patient_encounters:
                encounter_key = encounter.get('encounter_id') or str(id(encounter))
                visit_ien = visit_map.setdefault(encounter_key, _ensure_unique_ien(visit_iens))

                visit_datetime = VistaFormatter.fileman_datetime_format(encounter.get('date', ''), encounter.get('time'))

                stop_code_value = encounter.get('clinic_stop')
                stop_desc = encounter.get('clinic_stop_description') or encounter.get('department') or encounter.get('type', 'Unknown Clinic')
                if not stop_code_value:
                    stop_code_mapping = {
                        "Wellness Visit": "323",
                        "Emergency": "130",
                        "Follow-up": "323",
                        "Specialist": "301",
                        "Lab": "175",
                        "Surgery": "162",
                    }
                    stop_code_value = stop_code_mapping.get(encounter.get('type', ''), "323")
                stop_code = registry.register_stop_code(stop_code_value, stop_desc)

                service_category = encounter.get('service_category')
                if not service_category:
                    encounter_class = encounter.get('encounter_class')
                    if encounter_class == "emergency":
                        service_category = "E"
                    elif encounter_class == "inpatient":
                        service_category = "I"
                    else:
                        service_category = "A"

                zero_node = f"{vista_ien}^{visit_datetime}^{service_category}^{stop_code}^"
                all_globals[f"^AUPNVSIT({visit_ien},0)"] = zero_node

                location_value = encounter.get('location')
                if location_value:
                    loc_ien = registry.get_location_ien(location_value)
                    if loc_ien:
                        all_globals[f"^AUPNVSIT({visit_ien},.06)"] = loc_ien

                all_globals[f'^AUPNVSIT("B",{vista_ien},{visit_datetime},{visit_ien})'] = ""
                all_globals[f'^AUPNVSIT("D",{visit_datetime},{visit_ien})'] = ""

                if stop_code:
                    all_globals[f'^AUPNVSIT("AE",{stop_code},{visit_ien})'] = ""

                # Preserve GUID cross-reference under custom node to avoid DD conflicts
                if encounter.get('encounter_id'):
                    all_globals[f'^AUPNVSIT("GUID",{visit_ien})'] = encounter['encounter_id']

        status_lookup = {"normal": "N", "abnormal": "A", "critical": "C"}
        current_date_iso = date.today().isoformat()
        for patient in tqdm(patients, desc="Creating VistA medication/lab/allergy globals", unit="patients"):
            vista_ien = patient.vista_id or patient.generate_vista_id()

            for medication in medication_map.get(patient.patient_id, []):
                med_key = (
                    medication.get('medication_id')
                    or medication.get('id')
                    or f"{medication.get('name', '')}-{medication.get('start_date', '')}"
                )
                med_ien = medication_vista_map.setdefault(med_key, _ensure_unique_ien(medication_iens))
                drug_ien = registry.get_drug_ien(medication.get('name'), medication.get('rxnorm_code'))
                visit_ien = ""
                encounter_ref = medication.get('encounter_id')
                if encounter_ref:
                    visit_ien = visit_map.get(encounter_ref, "")
                start_date = VistaFormatter.fileman_date_format(medication.get('start_date'))
                stop_date = VistaFormatter.fileman_date_format(medication.get('end_date')) if medication.get('end_date') else ""
                status_flag = "D" if medication.get('end_date') else "A"
                segments = [
                    str(vista_ien or ""),
                    str(drug_ien or ""),
                    str(visit_ien or ""),
                    str(start_date or ""),
                    status_flag,
                    "",
                    "",
                    "",
                ]
                all_globals[f"^AUPNVMED({med_ien},0)"] = "^".join(segments)
                if stop_date:
                    all_globals[f"^AUPNVMED({med_ien},5101)"] = stop_date
                indication = medication.get('indication')
                if indication:
                    all_globals[f"^AUPNVMED({med_ien},13)"] = VistaFormatter.sanitize_mumps_string(indication)
                all_globals[f'^AUPNVMED("B",{vista_ien},{med_ien})'] = ""
                if visit_ien:
                    all_globals[f'^AUPNVMED("V",{visit_ien},{med_ien})'] = ""
                if drug_ien:
                    all_globals[f'^AUPNVMED("AA",{drug_ien},{med_ien})'] = ""

            for observation in observation_map.get(patient.patient_id, []):
                obs_key = (
                    observation.get('observation_id')
                    or observation.get('id')
                    or f"{observation.get('type', '')}-{observation.get('date', '')}-{observation.get('value', '')}"
                )
                lab_ien = lab_vista_map.setdefault(obs_key, _ensure_unique_ien(lab_iens))
                test_name = (
                    observation.get('type')
                    or observation.get('name')
                    or observation.get('observation_name')
                )
                loinc_code = observation.get('loinc_code') or observation.get('loinc')
                test_ien = registry.get_lab_test_ien(test_name, loinc_code)
                visit_ien = ""
                encounter_ref = observation.get('encounter_id')
                if encounter_ref:
                    visit_ien = visit_map.get(encounter_ref, "")
                raw_value = observation.get('value')
                if raw_value is None and observation.get('value_numeric') is not None:
                    raw_value = observation.get('value_numeric')
                value_str = VistaFormatter.sanitize_mumps_string(str(raw_value)) if raw_value is not None else ""
                units = VistaFormatter.sanitize_mumps_string(observation.get('units', ''))
                status_flag = status_lookup.get(str(observation.get('status', '')).lower(), "U")
                obs_date = (
                    observation.get('date')
                    or observation.get('observation_date')
                    or observation.get('effective_date')
                )
                obs_time: Optional[str] = None
                effective_datetime = observation.get('effective_datetime') or observation.get('timestamp')
                if effective_datetime:
                    try:
                        parsed_dt = datetime.fromisoformat(str(effective_datetime).replace('Z', ''))
                        obs_date = parsed_dt.date().isoformat()
                        obs_time = parsed_dt.time().strftime('%H:%M:%S')
                    except ValueError:
                        pass
                if not obs_date:
                    obs_date = current_date_iso
                obs_datetime = VistaFormatter.fileman_datetime_format(obs_date, obs_time)
                segments = [
                    str(vista_ien or ""),
                    str(test_ien or ""),
                    str(visit_ien or ""),
                    value_str,
                    units,
                    status_flag,
                    obs_datetime,
                ]
                all_globals[f"^AUPNVLAB({lab_ien},0)"] = "^".join(segments)
                ref_range = observation.get('reference_range')
                if ref_range:
                    all_globals[f"^AUPNVLAB({lab_ien},11)"] = VistaFormatter.sanitize_mumps_string(ref_range)
                panel_name = observation.get('panel')
                if panel_name:
                    all_globals[f"^AUPNVLAB({lab_ien},12)"] = VistaFormatter.sanitize_mumps_string(panel_name)
                all_globals[f'^AUPNVLAB("B",{vista_ien},{lab_ien})'] = ""
                if visit_ien:
                    all_globals[f'^AUPNVLAB("V",{visit_ien},{lab_ien})'] = ""
                if test_ien:
                    all_globals[f'^AUPNVLAB("AE",{test_ien},{lab_ien})'] = ""

            for allergy in allergy_map.get(patient.patient_id, []):
                allergy_key = (
                    allergy.get('allergy_id')
                    or allergy.get('id')
                    or f"{allergy.get('substance', '')}-{allergy.get('reaction', '')}"
                )
                allergy_ien = allergy_vista_map.setdefault(allergy_key, _ensure_unique_ien(allergy_iens))
                allergen_ien = registry.get_allergen_ien(
                    allergy.get('substance'),
                    allergy.get('rxnorm_code'),
                    allergy.get('unii_code'),
                )
                recorded_date = (
                    allergy.get('recorded_date')
                    or allergy.get('noted_date')
                    or allergy.get('start_date')
                    or current_date_iso
                )
                allergy_date = VistaFormatter.fileman_date_format(recorded_date)
                reaction_text = VistaFormatter.sanitize_mumps_string(allergy.get('reaction', ''))
                severity_text = VistaFormatter.sanitize_mumps_string(allergy.get('severity', '')).upper()
                segments = [
                    str(vista_ien or ""),
                    str(allergen_ien or ""),
                    "",
                    "o",
                    allergy_date or VistaFormatter.fileman_date_format(current_date_iso),
                ]
                all_globals[f"^GMR(120.8,{allergy_ien},0)"] = "^".join(segments)
                all_globals[f'^GMR(120.8,"B",{vista_ien},{allergy_ien})'] = ""
                if allergen_ien:
                    all_globals[f'^GMR(120.8,"C",{allergen_ien},{allergy_ien})'] = ""
                if reaction_text:
                    all_globals[f"^GMR(120.8,{allergy_ien},1)"] = reaction_text
                if severity_text:
                    all_globals[f"^GMR(120.8,{allergy_ien},3)"] = severity_text

            for immunization in immunization_map.get(patient.patient_id, []):
                imm_key = (
                    immunization.get('immunization_id')
                    or immunization.get('id')
                    or f"{immunization.get('vaccine', '')}-{immunization.get('date', '')}"
                )
                imm_ien = immunization_vista_map.setdefault(imm_key, _ensure_unique_ien(immunization_iens))
                vaccine_ien = registry.get_immunization_ien(
                    immunization.get('vaccine'),
                    immunization.get('cvx_code'),
                    immunization.get('rxnorm_code'),
                )
                visit_ien = ""
                encounter_ref = immunization.get('encounter_id')
                if encounter_ref:
                    visit_ien = visit_map.get(encounter_ref, "")
                imm_date = VistaFormatter.fileman_date_format(immunization.get('date'))
                series_type = (immunization.get('series_type') or "").lower()
                series_flag = "B" if series_type in {"booster", "seasonal"} else "P"
                segments = [
                    str(vista_ien or ""),
                    str(vaccine_ien or ""),
                    str(visit_ien or ""),
                    imm_date,
                    series_flag,
                    "",
                    "",
                    "",
                ]
                all_globals[f"^AUPNVIMM({imm_ien},0)"] = "^".join(segments)
                if vaccine_ien:
                    all_globals[f'^AUPNVIMM("C",{vaccine_ien},{imm_ien})'] = ""
                all_globals[f'^AUPNVIMM("B",{vista_ien},{imm_ien})'] = ""
                if visit_ien:
                    all_globals[f'^AUPNVIMM("AD",{visit_ien},{imm_ien})'] = ""

        # Index conditions by patient
        condition_map: Dict[str, List[Dict[str, Any]]] = {}
        for condition in conditions:
            condition_map.setdefault(condition.get('patient_id'), []).append(condition)

        for patient in tqdm(patients, desc="Creating VistA condition globals", unit="patients"):
            vista_ien = patient.vista_id or patient.generate_vista_id()
            patient_conditions = condition_map.get(patient.patient_id, [])
            for condition in patient_conditions:
                condition_key = condition.get('condition_id') or condition.get('id') or f"{condition.get('name')}-{condition.get('onset_date')}"
                problem_ien = problem_map.setdefault(condition_key, _ensure_unique_ien(problem_iens))

                onset_date = VistaFormatter.fileman_date_format(condition.get('onset_date', ''))
                status_mapping = {
                    "active": "A",
                    "resolved": "I",
                    "remission": "A",
                }
                problem_status = status_mapping.get(condition.get('status', 'active'), "A")

                condition_name = condition.get('name', '')
                icd_code = (
                    condition.get('icd10_code')
                    or condition.get('icd10')
                    or TERMINOLOGY_MAPPINGS.get('conditions', {}).get(condition_name, {}).get('icd10', '')
                )
                if not icd_code:
                    icd_code = VistaFormatter.ICD_FALLBACKS.get(condition_name, "R69")

                narrative_ien = registry.get_narrative_ien(condition_name)
                icd_ien = registry.get_icd10_ien(icd_code)

                zero_node = f"{vista_ien}^{narrative_ien}^{problem_status}^{onset_date}^{icd_ien}"
                all_globals[f"^AUPNPROB({problem_ien},0)"] = zero_node
                if narrative_ien:
                    all_globals[f"^AUPNPROB({problem_ien},.05)"] = narrative_ien

                all_globals[f'^AUPNPROB("B",{vista_ien},{problem_ien})'] = ""
                all_globals[f'^AUPNPROB("S","{problem_status}",{vista_ien},{problem_ien})'] = ""
                if icd_ien:
                    all_globals[f'^AUPNPROB("ICD",{icd_ien},{vista_ien},{problem_ien})'] = ""

        for patient in tqdm(patients, desc="Creating VistA family history globals", unit="patients"):
            vista_ien = patient.vista_id or patient.generate_vista_id()
            patient_history = family_history_map.get(patient.patient_id, [])
            for entry in patient_history:
                entry_key = (
                    entry.get('family_history_id')
                    or entry.get('id')
                    or f"{entry.get('condition')}|{entry.get('relation')}|{entry.get('recorded_date')}"
                )
                fh_ien = family_history_vista_map.setdefault(entry_key, _ensure_unique_ien(family_history_iens))

                relation_ien = registry.get_family_relation_ien(entry.get('relation'))
                narrative_ien = registry.get_narrative_ien(entry.get('condition_display') or entry.get('condition'))
                icd_ien = registry.get_icd10_ien(entry.get('icd10_code'))

                recorded_raw = entry.get('recorded_date')
                if isinstance(recorded_raw, date):
                    recorded_value = VistaFormatter.fileman_date_format(recorded_raw.isoformat())
                else:
                    recorded_value = VistaFormatter.fileman_date_format(recorded_raw)

                onset_age = entry.get('onset_age')
                onset_str = str(onset_age) if onset_age is not None else ""
                risk_value = entry.get('risk_modifier')
                if isinstance(risk_value, (int, float)):
                    risk_str = f"{risk_value:.3f}"
                else:
                    risk_str = VistaFormatter.sanitize_mumps_string(str(risk_value)) if risk_value else ""
                condition_code = entry.get('condition_code') or ''

                segments = [
                    str(vista_ien or ""),
                    str(relation_ien or ""),
                    str(narrative_ien or ""),
                    recorded_value or "",
                    onset_str,
                    str(icd_ien or ""),
                    condition_code,
                    risk_str,
                ]
                all_globals[f"^AUPNFH({fh_ien},0)"] = "^".join(segments)
                all_globals[f'^AUPNFH("B",{vista_ien},{fh_ien})'] = ""
                if relation_ien:
                    all_globals[f'^AUPNFH("AC",{relation_ien},{vista_ien},{fh_ien})'] = ""
                if icd_ien:
                    all_globals[f'^AUPNFH("AD",{icd_ien},{vista_ien},{fh_ien})'] = ""
                notes = entry.get('notes')
                if notes:
                    all_globals[f"^AUPNFH({fh_ien},11)"] = VistaFormatter.sanitize_mumps_string(notes)
                source = entry.get('source')
                if source:
                    all_globals[f"^AUPNFH({fh_ien},12)"] = VistaFormatter.sanitize_mumps_string(source)
                marker = entry.get('genetic_marker')
                if marker:
                    all_globals[f"^AUPNFH({fh_ien},13)"] = VistaFormatter.sanitize_mumps_string(marker)

        all_globals.update(registry.build_reference_globals(VistaFormatter.sanitize_mumps_string))

        fileman_date_today = VistaFormatter.fileman_date_format(date.today().isoformat())
        if patient_iens:
            all_globals["^DPT(0)"] = f"PATIENT^2^{max(patient_iens)}^{fileman_date_today}"
        if visit_iens:
            all_globals["^AUPNVSIT(0)"] = f"VISIT^9000010^{max(visit_iens)}^{fileman_date_today}"
        if problem_iens:
            all_globals["^AUPNPROB(0)"] = f"PROBLEM^9000011^{max(problem_iens)}^{fileman_date_today}"
        if medication_iens:
            all_globals["^AUPNVMED(0)"] = f"V MEDICATION^9000010.14^{max(medication_iens)}^{fileman_date_today}"
        if lab_iens:
            all_globals["^AUPNVLAB(0)"] = f"V LAB^9000010.09^{max(lab_iens)}^{fileman_date_today}"
        if allergy_iens:
            all_globals["^GMR(120.8,0)"] = f"PATIENT ALLERGIES^120.8^{max(allergy_iens)}^{fileman_date_today}"
        if immunization_iens:
            all_globals["^AUPNVIMM(0)"] = f"V IMMUNIZATION^9000010.11^{max(immunization_iens)}^{fileman_date_today}"
        if family_history_iens:
            all_globals["^AUPNFH(0)"] = f"FAMILY HISTORY^9000034^{max(family_history_iens)}^{fileman_date_today}"
        all_globals.update(registry.header_entries(fileman_date_today))

        with open(output_file, 'w') as handle:
            handle.write(";; VistA MUMPS Global Export for Synthetic Patient Data\n")
            handle.write(f";; Generated on {datetime.now().isoformat()}\n")
            handle.write(f";; Total global nodes: {len(all_globals)}\n")
            handle.write(";;\n")

            for global_ref, value in sorted(all_globals.items()):
                if value == "":
                    handle.write(f'S {global_ref}=""\n')
                elif re.fullmatch(r"-?\d+(\.\d+)?", value):
                    handle.write(f"S {global_ref}={value}\n")
                else:
                    handle.write(f'S {global_ref}="{value}"\n')

        print(f"VistA MUMPS globals exported to {output_file} ({len(all_globals)} global nodes)")

        patient_record_pattern = re.compile(r"^\^DPT\(\d+,0\)$")
        visit_record_pattern = re.compile(r"^\^AUPNVSIT\(\d+,0\)$")
        problem_record_pattern = re.compile(r"^\^AUPNPROB\(\d+,0\)$")
        medication_record_pattern = re.compile(r"^\^AUPNVMED\(\d+,0\)$")
        lab_record_pattern = re.compile(r"^\^AUPNVLAB\(\d+,0\)$")
        allergy_record_pattern = re.compile(r"^\^GMR\(120\.8,\d+,0\)$")
        immunization_record_pattern = re.compile(r"^\^AUPNVIMM\(\d+,0\)$")
        family_history_record_pattern = re.compile(r"^\^AUPNFH\(\d+,0\)$")

        dpt_count = sum(1 for k in all_globals if patient_record_pattern.match(k))
        visit_count = sum(1 for k in all_globals if visit_record_pattern.match(k))
        problem_count = sum(1 for k in all_globals if problem_record_pattern.match(k))
        medication_count = sum(1 for k in all_globals if medication_record_pattern.match(k))
        lab_count = sum(1 for k in all_globals if lab_record_pattern.match(k))
        allergy_count = sum(1 for k in all_globals if allergy_record_pattern.match(k))
        immunization_count = sum(1 for k in all_globals if immunization_record_pattern.match(k))
        family_history_count = sum(1 for k in all_globals if family_history_record_pattern.match(k))
        cross_reference_nodes = len(all_globals) - (
            dpt_count
            + visit_count
            + problem_count
            + medication_count
            + lab_count
            + allergy_count
            + immunization_count
            + family_history_count
        )
        return {
            "total_globals": len(all_globals),
            "patient_records": dpt_count,
            "visit_records": visit_count,
            "problem_records": problem_count,
            "medication_records": medication_count,
            "lab_records": lab_count,
            "allergy_records": allergy_count,
            "immunization_records": immunization_count,
            "family_history_records": family_history_count,
            "cross_references": cross_reference_nodes,
        }

    @staticmethod
    def export_vista_globals(
        patients: List[PatientRecord],
        encounters: List[Dict],
        conditions: List[Dict],
        medications: List[Dict],
        observations: List[Dict],
        allergies: List[Dict],
        immunizations: Optional[List[Dict]] = None,
        family_history: Optional[List[Dict]] = None,
        deaths: Optional[List[Dict]] = None,
        output_file: Optional[str] = None,
        export_mode: str = FILEMAN_INTERNAL_MODE,
    ) -> Dict[str, int]:
        # Backwards compatibility for earlier call signatures where optional
        # collections were omitted and ``output_file`` was passed positionally.
        if output_file is None and isinstance(immunizations, (str, os.PathLike)):
            output_file = str(immunizations)
            immunizations = None
        if output_file is None and isinstance(family_history, (str, os.PathLike)):
            output_file = str(family_history)
            family_history = None
        if output_file is None and isinstance(deaths, (str, os.PathLike)):
            output_file = str(deaths)
            deaths = None

        if output_file is None:
            raise ValueError("output_file must be provided for VistA export")

        immunizations = immunizations or []
        family_history = family_history or []
        deaths = deaths or []

        mode = (export_mode or VistaFormatter.FILEMAN_INTERNAL_MODE).lower()
        if mode == VistaFormatter.LEGACY_MODE:
            return VistaFormatter._export_legacy(patients, encounters, conditions, output_file)
        if mode == VistaFormatter.FILEMAN_INTERNAL_MODE:
            return VistaFormatter._export_fileman_internal(
                patients,
                encounters,
                conditions,
                medications,
                observations,
                allergies,
                immunizations,
                family_history,
                deaths,
                output_file,
            )
        raise ValueError(f"Unsupported VistA export mode: {export_mode}")

class HL7MessageValidator:
    """Basic HL7 v2 message validation for Phase 2"""
    
    @staticmethod
    def validate_message_structure(message: str) -> Dict[str, Any]:
        """Validate basic HL7 message structure"""
        validation_result = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "segments_found": []
        }
        
        if not message:
            validation_result["valid"] = False
            validation_result["errors"].append("Empty message")
            return validation_result
        
        segments = message.split('\r')
        
        # Check for required MSH segment
        if not segments or not segments[0].startswith('MSH'):
            validation_result["valid"] = False
            validation_result["errors"].append("Missing or invalid MSH segment")
            return validation_result
        
        # Validate each segment
        for i, segment in enumerate(segments):
            if not segment:
                continue
                
            segment_type = segment[:3]
            validation_result["segments_found"].append(segment_type)
            
            # Basic field count validation
            fields = segment.split('|')
            if segment_type == "MSH" and len(fields) < 10:
                validation_result["errors"].append(f"MSH segment has insufficient fields: {len(fields)}")
            elif segment_type == "PID" and len(fields) < 5:
                validation_result["errors"].append(f"PID segment has insufficient fields: {len(fields)}")
            elif segment_type in ["OBX", "OBR"] and len(fields) < 4:
                validation_result["errors"].append(f"{segment_type} segment has insufficient fields: {len(fields)}")
        
        # Check message type specific requirements
        if "PID" not in validation_result["segments_found"]:
            validation_result["warnings"].append("No PID segment found")
        
        if validation_result["errors"]:
            validation_result["valid"] = False
        
        return validation_result

def load_yaml_config(path):
    with open(path, 'r') as f:
        return yaml.safe_load(f)

def print_and_save_report(report, report_file=None):
    print("\n=== Synthetic Data Summary Report ===")
    print(report)
    if report_file:
        with open(report_file, 'w') as f:
            f.write(report)
        print(f"\nReport saved to {report_file}")

def main():
    parser = argparse.ArgumentParser(description="Synthetic Patient Data Generator")
    parser.add_argument("--num-records", type=int, default=1000, help="Number of patient records to generate")
    parser.add_argument("--output-dir", type=str, default=".", help="Directory to save output files")
    parser.add_argument("--seed", type=int, default=None, help="Random seed for reproducibility")
    parser.add_argument("--csv", action="store_true", help="Output CSV files only")
    parser.add_argument("--parquet", action="store_true", help="Output Parquet files only")
    parser.add_argument("--both", action="store_true", help="Output both CSV and Parquet files (default)")
    parser.add_argument("--config", type=str, default=None, help="Path to YAML config file")
    parser.add_argument("--report-file", type=str, default=None, help="Path to save summary report (optional)")
    parser.add_argument("--scenario", type=str, default=None, help="Name of lifecycle scenario to apply")
    parser.add_argument("--scenario-file", type=str, default=None, help="Path to scenario overrides YAML")
    parser.add_argument("--list-scenarios", action="store_true", help="List available scenarios and exit")
    parser.add_argument(
        "--module",
        action="append",
        dest="modules",
        default=None,
        help="Add a clinical workflow module (repeat to add multiple)",
    )
    parser.add_argument(
        "--list-modules",
        action="store_true",
        help="List available modules under the modules/ directory and exit",
    )
    parser.add_argument(
        "--vista-mode",
        choices=[VistaFormatter.LEGACY_MODE, VistaFormatter.FILEMAN_INTERNAL_MODE],
        default=VistaFormatter.FILEMAN_INTERNAL_MODE,
        help="Control VistA export encoding (default: fileman_internal)",
    )
    parser.add_argument("--skip-fhir", action="store_true", help="Skip FHIR bundle export")
    parser.add_argument("--skip-hl7", action="store_true", help="Skip HL7 v2 message export")
    parser.add_argument("--skip-vista", action="store_true", help="Skip VistA MUMPS export")
    parser.add_argument("--skip-report", action="store_true", help="Skip textual summary report")

    args, unknown = parser.parse_known_args()

    if getattr(args, "list_scenarios", False):
        print("Available scenarios:")
        for name in list_scenarios():
            print(f"  - {name}")
        return

    if getattr(args, "list_modules", False):
        print("Available modules:")
        for name in list_available_modules():
            print(f"  - {name}")
        return

    config = {}
    if args.config:
        config = load_yaml_config(args.config)

    scenario_name = args.scenario or config.get('scenario')
    scenario_file = args.scenario_file or config.get('scenario_file')
    try:
        scenario_config = load_scenario_config(scenario_name, scenario_file)
    except ValueError as exc:
        print(exc)
        return
    scenario_config = dict(scenario_config) if scenario_config else {}
    scenario_metadata = scenario_config.pop('metadata', {}) if scenario_config else {}
    terminology_details = scenario_config.get('terminology_details') if scenario_config else None
    terminology_root_override = scenario_config.get('terminology_root') if scenario_config else None
    terminology_lookup = build_terminology_lookup(terminology_details, terminology_root_override)
    module_names: List[str] = []
    if scenario_config:
        module_names.extend(scenario_config.get('modules', []))
    if config.get('modules'):
        configured = config['modules']
        if isinstance(configured, str):
            module_names.append(configured)
        else:
            module_names.extend(configured)
    if getattr(args, 'modules', None):
        module_names.extend(args.modules)
    module_names = [name for name in dict.fromkeys([m for m in module_names if m])]
    module_engine = ModuleEngine(module_names) if module_names else None

    def get_config(key, default=None):
        # CLI flag overrides config file
        val = getattr(args, key, None)
        if val not in [None, False]:
            return val
        if key in config and config[key] not in [None, False]:
            return config[key]
        if scenario_config and key in scenario_config:
            return scenario_config[key]
        return default

    num_records = int(get_config('num_records', 1000))
    output_dir = get_config('output_dir', '.')
    seed = get_config('seed', None)
    output_format = get_config('output_format', 'both')
    age_dist = get_config('age_dist', None)
    gender_dist = get_config('gender_dist', None)
    race_dist = get_config('race_dist', None)
    smoking_dist = get_config('smoking_dist', None)
    alcohol_dist = get_config('alcohol_dist', None)
    education_dist = get_config('education_dist', None)
    employment_dist = get_config('employment_dist', None)
    housing_dist = get_config('housing_dist', None)

    if seed is not None:
        random.seed(int(seed))
        Faker.seed(int(seed))

    os.makedirs(output_dir, exist_ok=True)

    # Determine output formats
    output_csv = output_format in ["csv", "both"]
    output_parquet = output_format in ["parquet", "both"]
    vista_mode = get_config('vista_mode', VistaFormatter.FILEMAN_INTERNAL_MODE)

    # Parse distributions
    age_dist = parse_distribution(age_dist, AGE_BIN_LABELS, default_dist={l: 1/len(AGE_BIN_LABELS) for l in AGE_BIN_LABELS})
    gender_dist = parse_distribution(gender_dist, GENDERS, default_dist={g: 1/len(GENDERS) for g in GENDERS})
    race_dist = parse_distribution(race_dist, RACES, default_dist={r: 1/len(RACES) for r in RACES})
    smoking_dist = parse_distribution(smoking_dist, SDOH_SMOKING, default_dist={s: 1/len(SDOH_SMOKING) for s in SDOH_SMOKING})
    alcohol_dist = parse_distribution(alcohol_dist, SDOH_ALCOHOL, default_dist={a: 1/len(SDOH_ALCOHOL) for a in SDOH_ALCOHOL})
    education_dist = parse_distribution(education_dist, SDOH_EDUCATION, default_dist={e: 1/len(SDOH_EDUCATION) for e in SDOH_EDUCATION})
    employment_dist = parse_distribution(employment_dist, SDOH_EMPLOYMENT, default_dist={e: 1/len(SDOH_EMPLOYMENT) for e in SDOH_EMPLOYMENT})
    housing_dist = parse_distribution(housing_dist, SDOH_HOUSING, default_dist={h: 1/len(SDOH_HOUSING) for h in SDOH_HOUSING})

    active_scenario_name = scenario_name or ('custom' if scenario_config else 'unspecified')
    orchestrator = LifecycleOrchestrator(
        scenario_name=active_scenario_name,
        scenario_details=scenario_metadata,
    )

    profile_generator = partial(
        generate_patient_profile_for_index,
        age_dist=age_dist,
        gender_dist=gender_dist,
        race_dist=race_dist,
        smoking_dist=smoking_dist,
        alcohol_dist=alcohol_dist,
        education_dist=education_dist,
        employment_dist=employment_dist,
        housing_dist=housing_dist,
        faker=fake,
    )

    print(f"Generating {num_records} patient profiles in parallel...")
    with concurrent.futures.ThreadPoolExecutor() as executor:
        profiles = list(tqdm(
            executor.map(profile_generator, range(num_records)),
            total=num_records,
            desc="Generating patient profiles",
            unit="profiles"
        ))

    patients: List[PatientRecord] = []
    for profile in profiles:
        record_kwargs = {**profile}
        birthdate = record_kwargs.pop("birthdate")
        if isinstance(birthdate, datetime):
            birth_value = birthdate.date()
        elif isinstance(birthdate, date):
            birth_value = birthdate
        else:
            birth_value = datetime.fromisoformat(str(birthdate)).date()
        record_kwargs["birthdate"] = birth_value.isoformat()

        patient = PatientRecord(**record_kwargs)
        patient.generate_vista_id()
        patient.generate_mrn()
        patients.append(patient)

    all_encounters = []
    all_conditions = []
    all_medications = []
    all_allergies = []
    all_procedures = []
    all_immunizations = []
    all_observations = []
    all_deaths = []
    all_family_history = []
    all_care_plans = []
    all_module_attributes = []
    lifecycle_patients: List[LifecyclePatient] = []

    print("Generating related healthcare data...")
    for patient in tqdm(patients, desc="Generating healthcare data", unit="patients"):
        # Convert PatientRecord to dict for backward compatibility with existing functions
        patient_dict = patient.to_dict()
        module_result = module_engine.execute(patient_dict) if module_engine else ModuleExecutionResult()
        replaced = module_result.replacements

        if getattr(module_result, "attributes", None):
            patient_dict.setdefault("module_attributes", {}).update(module_result.attributes)
            for attr, value in module_result.attributes.items():
                all_module_attributes.append(
                    {
                        "patient_id": patient.patient_id,
                        "attribute": attr,
                        "value": value,
                    }
                )

        module_condition_names: List[str] = []
        if module_result.conditions:
            for cond in module_result.conditions:
                name: Optional[str] = None
                if isinstance(cond, dict):
                    name = cond.get("name") or cond.get("condition") or cond.get("display")
                elif hasattr(cond, "name"):
                    name = getattr(cond, "name")
                elif isinstance(cond, str):
                    name = cond
                if name:
                    module_condition_names.append(name)

        baseline_conditions = assign_conditions(patient_dict)

        def _deduplicate(values: Iterable[str]) -> List[str]:
            seen: Set[str] = set()
            ordered: List[str] = []
            for value in values:
                if not value:
                    continue
                if value not in seen:
                    ordered.append(value)
                    seen.add(value)
            return ordered

        if "conditions" in replaced and module_condition_names:
            preassigned_conditions = _deduplicate(module_condition_names)
        else:
            combined = list(baseline_conditions) + [
                name for name in module_condition_names if name not in baseline_conditions
            ]
            preassigned_conditions = _deduplicate(combined)

        patient_dict["preassigned_conditions"] = preassigned_conditions

        family_history_entries, family_history_adjustments = generate_family_history(
            patient_dict,
            min_fam=0,
            max_fam=4,
        )
        patient_dict["family_history_entries"] = family_history_entries
        patient_dict["family_history_adjustments"] = family_history_adjustments

        encounters = []
        if "encounters" in replaced:
            encounters = module_result.encounters
        else:
            encounters = generate_encounters(
                patient_dict,
                module_result.conditions if module_result.conditions else None,
                preassigned_conditions=preassigned_conditions,
            )
            if module_result.encounters:
                encounters.extend(module_result.encounters)
        all_encounters.extend(encounters)

        conditions = []
        if "conditions" in replaced:
            conditions = module_result.conditions or []
        else:
            conditions = generate_conditions(
                patient_dict,
                encounters,
                min_cond=1,
                max_cond=5,
                preassigned_conditions=preassigned_conditions,
            )
            if module_result.conditions:
                conditions.extend(module_result.conditions)

        # Update condition encounter references when missing
        for cond in conditions:
            if not cond.get("encounter_id"):
                enc = random.choice(encounters) if encounters else None
                cond["encounter_id"] = enc["encounter_id"] if enc else None
            if not cond.get("onset_date"):
                enc = next((e for e in encounters if e.get("encounter_id") == cond.get("encounter_id")), None)
                onset = enc["date"] if enc else patient_dict["birthdate"]
                cond["onset_date"] = onset
        patient_dict["condition_profile"] = [c.get("name") for c in conditions]
        all_conditions.extend(conditions)

        if "medications" in replaced:
            medications = module_result.medications
        else:
            medications = generate_medications(patient_dict, encounters, conditions)
            if module_result.medications:
                medications.extend(module_result.medications)
        all_medications.extend(medications)
        patient_dict["medications"] = medications
        patient_dict["medication_profile"] = [m.get("name") for m in medications]

        for condition in conditions:
            if condition.get("precision_markers") and isinstance(condition["precision_markers"], list):
                condition["precision_markers"] = ",".join(condition["precision_markers"])
            if isinstance(condition.get("care_plan"), list):
                condition["care_plan"] = ",".join(condition["care_plan"])
        allergies = generate_allergies(patient_dict)
        allergy_followups = plan_allergy_followups(patient_dict, encounters, allergies)
        if allergy_followups.get("medications"):
            medications.extend(allergy_followups["medications"])
            all_medications.extend(allergy_followups["medications"])
            patient_dict["medications"] = medications
            patient_dict["medication_profile"] = [m.get("name") for m in medications]
        pending_allergy_observations = allergy_followups.get("observations", [])
        allergy_procedures = allergy_followups.get("procedures", [])
        if allergy_followups.get("medications") or allergy_procedures or pending_allergy_observations:
            patient_dict["allergy_followups"] = {
                "medications": len(allergy_followups.get("medications", [])),
                "procedures": len(allergy_procedures),
                "observations": len(pending_allergy_observations),
            }
        all_allergies.extend(allergies)
        patient_dict["allergies"] = allergies
        procedures = generate_procedures(patient_dict, encounters, conditions)
        if allergy_procedures:
            procedures.extend(allergy_procedures)
        if module_result.procedures:
            if "procedures" in replaced:
                procedures = module_result.procedures
            else:
                procedures.extend(module_result.procedures)
        all_procedures.extend(procedures)
        patient_dict["procedures"] = procedures

        immunizations: List[Dict[str, Any]] = []
        immunization_followups: List[Dict[str, Any]] = []
        if "immunizations" in replaced:
            immunizations = module_result.immunizations or []
        else:
            immunizations, immunization_followups = generate_immunizations(
                patient_dict,
                encounters,
                allergies=allergies,
                conditions=conditions,
            )
            if module_result.immunizations:
                immunizations.extend(module_result.immunizations)

        all_immunizations.extend(immunizations)
        patient_dict["immunization_profile"] = [record.get("vaccine") for record in immunizations]
        patient_dict["immunizations"] = immunizations

        observations = generate_observations(patient_dict, encounters, conditions, medications)
        if immunization_followups:
            observations.extend(immunization_followups)
        if module_result.observations:
            if "observations" in replaced:
                observations = module_result.observations
            else:
                observations.extend(module_result.observations)
        if immunization_followups and "observations" in replaced:
            observations.extend(immunization_followups)
        if pending_allergy_observations:
            observations.extend(pending_allergy_observations)
        all_observations.extend(observations)
        patient_dict["observations"] = observations
        care_plans = generate_care_plans(
            patient_dict,
            conditions,
            encounters,
            medications=medications,
            procedures=procedures,
            observations=observations,
            immunizations=immunizations,
        )
        if module_result.care_plans:
            if "care_plans" in replaced:
                care_plans = module_result.care_plans
            else:
                care_plans.extend(module_result.care_plans)
        for plan in care_plans:
            activities = plan.get("activities")
            if isinstance(activities, list):
                if all(isinstance(item, str) for item in activities):
                    plan["activities"] = ", ".join(activities)
                else:
                    plan["activities"] = json.dumps(activities)
            roles = plan.get("responsible_roles")
            if isinstance(roles, list):
                plan["responsible_roles"] = ", ".join(str(role) for role in roles)
            linked = plan.get("linked_encounters")
            if isinstance(linked, list):
                plan["linked_encounters"] = ", ".join(str(item) for item in linked if item)
        all_care_plans.extend(care_plans)
        patient_dict["care_plan_details"] = care_plans
        death = generate_death(patient_dict, conditions, family_history_entries)
        if death:
            all_deaths.append(death)
            patient_dict["deceased"] = True
            patient_dict["death_record"] = death
        else:
            patient_dict["deceased"] = False
        family_history = patient_dict.get("family_history_entries", [])
        all_family_history.extend(family_history)

        # Persist advanced clinical metadata back onto the PatientRecord for downstream exports
        patient.metadata['sdoh_risk_score'] = patient_dict.get('sdoh_risk_score', 0.0)
        patient.metadata['sdoh_risk_factors'] = patient_dict.get('sdoh_risk_factors', [])
        patient.metadata['community_deprivation_index'] = patient_dict.get('community_deprivation_index', 0.0)
        patient.metadata['access_to_care_score'] = patient_dict.get('access_to_care_score', 0.0)
        patient.metadata['transportation_access'] = patient_dict.get('transportation_access', '')
        patient.metadata['language_access_barrier'] = patient_dict.get('language_access_barrier', False)
        patient.metadata['social_support_score'] = patient_dict.get('social_support_score', 0.0)
        patient.metadata['sdoh_care_gaps'] = patient_dict.get('sdoh_care_gaps', [])
        patient.metadata['genetic_risk_score'] = patient_dict.get('genetic_risk_score', 0.0)
        patient.metadata['genetic_markers'] = patient_dict.get('genetic_markers', [])
        patient.metadata['precision_markers'] = patient_dict.get('precision_markers', [])
        patient.metadata['comorbidity_profile'] = patient_dict.get('comorbidity_profile', [])
        care_summary = patient_dict.get('care_plan_summary', {})
        patient.metadata['care_plan_total'] = care_summary.get('total', 0)
        patient.metadata['care_plan_completed'] = care_summary.get('completed', 0)
        patient.metadata['care_plan_overdue'] = care_summary.get('overdue', 0)
        patient.metadata['care_plan_scheduled'] = care_summary.get('scheduled', 0)
        patient.metadata['care_plan_in_progress'] = care_summary.get('in_progress', 0)
        patient.metadata['deceased'] = patient_dict.get('deceased', False)
        patient.metadata['death_record'] = death
        patient.metadata['family_history_entries'] = family_history
        patient.metadata['family_history_adjustments'] = family_history_adjustments

        # Refresh the dictionary snapshot so metadata changes are captured
        patient_snapshot = patient.to_dict()
        patient_snapshot["family_history_entries"] = family_history
        if death:
            patient_snapshot["death_record"] = death
        if "module_attributes" in patient_dict:
            patient_snapshot["module_attributes"] = patient_dict["module_attributes"]
        lifecycle_patients.append(
            orchestrator.build_patient(
                patient_snapshot,
                encounters=encounters,
                conditions=conditions,
                medications=medications,
                immunizations=immunizations,
                observations=observations,
                allergies=allergies,
                procedures=procedures,
                family_history=family_history,
                death=death,
                metadata={**patient.metadata, "care_plan_details": care_plans},
            )
        )
        # Restore patient_dict reference for downstream legacy operations
        patient_dict = patient_snapshot

    def ensure_lookup_entries(system: str, codes: Iterable[Optional[str]], loader) -> None:
        existing = terminology_lookup.setdefault(system, {})
        missing = {str(code) for code in codes if code and str(code) not in existing}
        if not missing:
            return
        try:
            entries = loader(terminology_root_override)
        except Exception:
            return
        for entry in entries:
            if entry.code in missing:
                existing[entry.code] = entry
        if existing:
            terminology_lookup[system] = existing

    ensure_lookup_entries(
        "rxnorm",
        (med.get("rxnorm_code") for med in all_medications),
        load_rxnorm_medications,
    )
    ensure_lookup_entries(
        "loinc",
        (obs.get("loinc_code") for obs in all_observations),
        load_loinc_labs,
    )

    def build_umls_source_index() -> Dict[Tuple[str, str], List[TerminologyEntry]]:
        index: Dict[Tuple[str, str], List[TerminologyEntry]] = {}
        for entry in terminology_lookup.get("umls", {}).values():
            sab = entry.metadata.get("sab")
            source_code = entry.metadata.get("code")
            if not sab or not source_code:
                continue
            index.setdefault((sab.upper(), str(source_code)), []).append(entry)
        return index

    umls_source_index = build_umls_source_index()

    vsac_index: Dict[str, List[TerminologyEntry]] = {}
    for entry in terminology_lookup.get("vsac", {}).values():
        vsac_index.setdefault(entry.code, []).append(entry)

    loinc_lookup = terminology_lookup.get("loinc", {})
    rxnorm_lookup = terminology_lookup.get("rxnorm", {})

    for record in all_observations:
        code = record.get("loinc_code") or record.get("loinc")
        if code:
            entry = loinc_lookup.get(str(code))
            if entry:
                record.setdefault("loinc_display", entry.display)
                if entry.metadata.get("ncbi_url"):
                    record.setdefault("loinc_ncbi_url", entry.metadata["ncbi_url"])
            vsac_entries = vsac_index.get(str(code), [])
            oids = sorted(
                {
                    item.metadata.get("value_set_oid")
                    for item in vsac_entries
                    if item.metadata.get("value_set_oid")
                }
            )
            if oids:
                record["value_set_oids"] = ",".join(oids)
                names = sorted(
                    {
                        item.metadata.get("value_set_name")
                        for item in vsac_entries
                        if item.metadata.get("value_set_name")
                    }
                )
                if names:
                    record["value_set_names"] = ",".join(names)

    for record in all_medications:
        code = record.get("rxnorm_code") or record.get("rxnorm")
        if code:
            entry = rxnorm_lookup.get(str(code))
            if entry:
                record.setdefault("rxnorm_display", entry.display)
                if entry.metadata.get("ndc_example"):
                    record.setdefault("ndc_example", entry.metadata.get("ndc_example"))
            umls_entries = umls_source_index.get(("RXNORM", str(code)), [])
            if umls_entries:
                cuis = sorted({item.code for item in umls_entries if item.code})
                semantic_types = sorted(
                    {
                        item.metadata.get("semantic_type")
                        for item in umls_entries
                        if item.metadata.get("semantic_type")
                    }
                )
                if cuis:
                    record["umls_cuis"] = ",".join(cuis)
                if semantic_types:
                    record["umls_semantic_types"] = ",".join(semantic_types)

    def save(df, name):
        if output_csv:
            df.write_csv(os.path.join(output_dir, f"{name}.csv"))
        if output_parquet:
            df.write_parquet(os.path.join(output_dir, f"{name}.parquet"))

    def save_lifecycle_patients(patients_list, filename="lifecycle_patients.json"):
        """Persist lifecycle-focused patient payloads for the new simulator path."""
        import json

        lifecycle_path = os.path.join(output_dir, filename)
        payload = [patient.to_serializable_dict() for patient in patients_list]
        with open(lifecycle_path, "w") as handle:
            json.dump(payload, handle, indent=2)
        return lifecycle_path

    def save_fhir_bundle(patients_list, terminology_lookup, filename="fhir_bundle.json"):
        """Save FHIR bundle with Patient and Condition resources"""
        import json

        fhir_formatter = FHIRFormatter(terminology_lookup)
        bundle_entries = []

        # Add Patient resources
        for patient in tqdm(patients_list, desc="Creating FHIR Patient resources", unit="patients"):
            patient_resource = fhir_formatter.create_patient_resource(patient)
            bundle_entries.append({"resource": patient_resource})

        # Add Condition resources grouped by patient
        for patient in tqdm(patients_list, desc="Creating FHIR Condition resources", unit="patients"):
            if isinstance(patient, LifecyclePatient):
                patient_conditions = patient.conditions
            else:
                patient_conditions = []

            for condition in patient_conditions:
                condition_resource = fhir_formatter.create_condition_resource(
                    patient.patient_id, condition
                )
                bundle_entries.append({"resource": condition_resource})

        # Add AllergyIntolerance resources
        for patient in tqdm(patients_list, desc="Creating FHIR Allergy resources", unit="patients"):
            if not isinstance(patient, LifecyclePatient):
                continue
            for allergy in patient.allergies:
                allergy_resource = fhir_formatter.create_allergy_intolerance_resource(
                    patient.patient_id, allergy
                )
                bundle_entries.append({"resource": allergy_resource})

        # Add MedicationStatement resources
        for patient in tqdm(patients_list, desc="Creating FHIR Medication resources", unit="patients"):
            if not isinstance(patient, LifecyclePatient):
                continue
            for medication in patient.medications:
                medication_resource = fhir_formatter.create_medication_statement_resource(
                    patient.patient_id, medication
                )
                bundle_entries.append({"resource": medication_resource})

        # Add Immunization resources
        for patient in tqdm(patients_list, desc="Creating FHIR Immunization resources", unit="patients"):
            if not isinstance(patient, LifecyclePatient):
                continue
            for immunization in patient.immunizations:
                immunization_resource = fhir_formatter.create_immunization_resource(
                    patient.patient_id, immunization
                )
                bundle_entries.append({"resource": immunization_resource})

        for patient in tqdm(patients_list, desc="Creating FHIR CarePlan resources", unit="patients"):
            if isinstance(patient, LifecyclePatient):
                plan_records = patient.care_plans or patient.metadata.get("care_plan_details", [])
            else:
                plan_records = []
            for plan in plan_records:
                if isinstance(plan, str):
                    continue
                care_plan_resource = fhir_formatter.create_care_plan_resource(
                    patient.patient_id if isinstance(patient, LifecyclePatient) else plan.get("patient_id", ""),
                    plan,
                )
                bundle_entries.append({"resource": care_plan_resource})

        # Add Observation resources when lifecycle data is available
        for patient in tqdm(patients_list, desc="Creating FHIR Observation resources", unit="patients"):
            if not isinstance(patient, LifecyclePatient):
                continue
            for observation in patient.observations:
                observation_resource = fhir_formatter.create_observation_resource(
                    patient.patient_id, observation
                )
                bundle_entries.append({"resource": observation_resource})

        for patient in tqdm(patients_list, desc="Creating FHIR FamilyHistory resources", unit="patients"):
            if not isinstance(patient, LifecyclePatient):
                continue
            for entry in patient.family_history:
                family_history_resource = fhir_formatter.create_family_history_resource(
                    patient.patient_id,
                    entry,
                )
                bundle_entries.append({"resource": family_history_resource})

        # Create FHIR Bundle
        fhir_bundle = {
            "resourceType": "Bundle",
            "type": "collection",
            "timestamp": datetime.now().isoformat(),
            "entry": bundle_entries
        }
        
        # Save to file
        with open(os.path.join(output_dir, filename), 'w') as f:
            json.dump(fhir_bundle, f, indent=2)
        
        print(f"FHIR Bundle saved: {filename} ({len(bundle_entries)} resources)")

    def save_terminology_reference(terminology_lookup, output_directory, filename="terminology_reference.csv"):
        if not terminology_lookup:
            return

        rows: List[Dict[str, Any]] = []
        for system, entries in terminology_lookup.items():
            for entry in entries.values():
                row = {
                    "system": system,
                    "code": entry.code,
                    "display": entry.display,
                }
                row.update(entry.metadata)
                rows.append(row)

        if not rows:
            return

        df = pl.DataFrame(rows)
        df.write_csv(os.path.join(output_directory, filename))

    def save_hl7_messages(patients_list, encounters_list, observations_list, filename_prefix="hl7_messages"):
        """Save HL7 v2 messages (ADT and ORU)"""
        hl7_formatter = HL7v2Formatter()
        validator = HL7MessageValidator()

        adt_messages = []
        oru_messages = []
        validation_results = []

        def to_encounter_dict(encounter: LifecycleEncounter) -> Dict[str, Any]:
            return {
                "encounter_id": encounter.encounter_id,
                "patient_id": encounter.patient_id,
                "date": encounter.start_date.isoformat() if encounter.start_date else None,
                "type": encounter.encounter_type,
                "reason": encounter.reason,
                "provider": encounter.provider,
                "location": encounter.location,
            }

        def to_observation_dict(observation: LifecycleObservation) -> Dict[str, Any]:
            return {
                "observation_id": observation.observation_id,
                "patient_id": observation.patient_id,
                "type": observation.name,
                "value": observation.value,
                "unit": observation.unit,
                "status": observation.status,
                "interpretation": observation.interpretation,
                "observation_date": observation.effective_datetime.isoformat()
                if observation.effective_datetime
                else None,
            }

        # Create ADT messages for each patient
        for patient in tqdm(patients_list, desc="Creating HL7 ADT messages", unit="patients"):
            if isinstance(patient, LifecyclePatient):
                patient_encounters = [to_encounter_dict(enc) for enc in patient.encounters]
            else:
                patient_encounters = [
                    enc for enc in encounters_list if enc.get('patient_id') == patient.patient_id
                ]

            if patient_encounters:
                encounter = patient_encounters[0]
                adt_message = hl7_formatter.create_adt_message(patient, encounter, "A04")
            else:
                adt_message = hl7_formatter.create_adt_message(patient, None, "A04")

            adt_messages.append(adt_message)

            validation = validator.validate_message_structure(adt_message)
            validation_results.append({
                "patient_id": patient.patient_id,
                "message_type": "ADT",
                "valid": validation["valid"],
                "errors": validation["errors"],
                "warnings": validation["warnings"],
            })

        # Build fallback observation mapping for legacy payloads
        fallback_obs_map: Dict[str, List[Dict[str, Any]]] = {}
        for obs in observations_list:
            patient_id = obs.get('patient_id')
            fallback_obs_map.setdefault(patient_id, []).append(obs)

        for patient in tqdm(patients_list, desc="Creating HL7 ORU messages", unit="patients"):
            if isinstance(patient, LifecyclePatient):
                patient_observations = [to_observation_dict(obs) for obs in patient.observations]
            else:
                patient_observations = fallback_obs_map.get(patient.patient_id, [])

            if not patient_observations:
                continue

            oru_message = hl7_formatter.create_oru_message(patient, patient_observations)
            oru_messages.append(oru_message)

            validation = validator.validate_message_structure(oru_message)
            validation_results.append({
                "patient_id": patient.patient_id,
                "message_type": "ORU",
                "valid": validation["valid"],
                "errors": validation["errors"],
                "warnings": validation["warnings"],
            })
        
        # Save ADT messages
        if adt_messages:
            with open(os.path.join(output_dir, f"{filename_prefix}_adt.hl7"), 'w') as f:
                f.write('\n'.join(adt_messages))
            print(f"HL7 ADT messages saved: {filename_prefix}_adt.hl7 ({len(adt_messages)} messages)")
        
        # Save ORU messages  
        if oru_messages:
            with open(os.path.join(output_dir, f"{filename_prefix}_oru.hl7"), 'w') as f:
                f.write('\n'.join(oru_messages))
            print(f"HL7 ORU messages saved: {filename_prefix}_oru.hl7 ({len(oru_messages)} messages)")
        
        # Save validation results
        if validation_results:
            import json
            with open(os.path.join(output_dir, f"{filename_prefix}_validation.json"), 'w') as f:
                json.dump(validation_results, f, indent=2)
            
            # Print validation summary
            valid_count = sum(1 for r in validation_results if r["valid"])
            total_count = len(validation_results)
            print(f"HL7 Validation: {valid_count}/{total_count} messages valid")

    # Convert PatientRecord objects to dictionaries for DataFrame creation
    print("Converting patient records to dictionaries...")
    patients_dict = [patient.to_dict() for patient in tqdm(patients, desc="Converting patients", unit="patients")]
    
    print("Saving data files...")
    def _sanitize_frame(data: List[Dict[str, Any]]) -> pl.DataFrame:
        if not data:
            return pl.DataFrame([])

        def _normalize_value(value: Any) -> Any:
            if isinstance(value, pl.Series):
                value = value.to_list()
            if isinstance(value, tuple):
                value = list(value)
            if isinstance(value, list):
                if all(isinstance(item, (str, int, float, bool, type(None))) for item in value):
                    return ",".join("" if item is None else str(item) for item in value)
                return json.dumps(value)
            if isinstance(value, dict):
                return json.dumps(value)
            return value

        normalized_rows: List[Dict[str, Any]] = []
        for row in data:
            normalized_row: Dict[str, Any] = {}
            for key, value in row.items():
                normalized_row[key] = _normalize_value(value)
            normalized_rows.append(normalized_row)

        return pl.DataFrame(normalized_rows)

    tables_to_save = [
        (_sanitize_frame(patients_dict), "patients"),
        (_sanitize_frame(all_encounters), "encounters"),
        (_sanitize_frame(all_conditions), "conditions"),
        (_sanitize_frame(all_medications), "medications"),
        (_sanitize_frame(all_allergies), "allergies"),
        (_sanitize_frame(all_procedures), "procedures"),
        (_sanitize_frame(all_immunizations), "immunizations"),
        (_sanitize_frame(all_observations), "observations"),
    ]
    
    if all_module_attributes:
        tables_to_save.append((_sanitize_frame(all_module_attributes), "module_attributes"))
    
    if all_deaths:
        tables_to_save.append((pl.DataFrame(all_deaths), "deaths"))
    if all_family_history:
        tables_to_save.append((pl.DataFrame(all_family_history), "family_history"))
    if all_care_plans:
        tables_to_save.append((pl.DataFrame(all_care_plans), "care_plans"))
    
    for df, name in tqdm(tables_to_save, desc="Saving tables", unit="tables"):
        save(df, name)

    lifecycle_output = save_lifecycle_patients(lifecycle_patients)
    print(f"Lifecycle patient payload saved: {os.path.basename(lifecycle_output)}")

    if not args.skip_fhir or not args.skip_hl7 or not args.skip_vista:
        print("\nExporting specialized formats...")
    
    # Export FHIR bundle (Phase 1: basic Patient and Condition resources)
    if args.skip_fhir:
        print("Skipping FHIR bundle export (--skip-fhir).")
    else:
        print("Creating FHIR bundle...")
        save_fhir_bundle(lifecycle_patients, terminology_lookup, "fhir_bundle.json")
        save_terminology_reference(terminology_lookup, output_dir)
    
    # Export HL7 v2 messages (Phase 2: ADT and ORU messages)
    if args.skip_hl7:
        print("Skipping HL7 v2 message export (--skip-hl7).")
    else:
        print("Creating HL7 v2 messages...")
        save_hl7_messages(lifecycle_patients, all_encounters, all_observations, "hl7_messages")
    
    # Export VistA MUMPS globals (Phase 3: VA migration simulation)
    if args.skip_vista:
        print("Skipping VistA MUMPS export (--skip-vista).")
        vista_stats = {}
    else:
        print("Creating VistA MUMPS globals...")
        vista_output_file = os.path.join(output_dir, "vista_globals.mumps")
        vista_stats = VistaFormatter.export_vista_globals(
            patients,
            all_encounters,
            all_conditions,
            all_medications,
            all_observations,
            all_allergies,
            all_immunizations,
            all_family_history,
            all_deaths,
            vista_output_file,
            export_mode=vista_mode,
        )

    print(f"Done! Files written to {output_dir}: patients, encounters, conditions, medications, allergies, procedures, immunizations, observations, deaths, family_history (CSV and/or Parquet), FHIR bundle, HL7 messages, VistA MUMPS globals")

    # Summary report
    if not args.skip_report:
        import collections

        def value_counts(lst, bins=None):
            if bins:
                binned = collections.Counter()
                for v in lst:
                    for label, (a, b) in bins.items():
                        if a <= v <= b:
                            binned[label] += 1
                            break
                return binned
            return collections.Counter(lst)

        age_bins_dict = {f"{a}-{b}": (a, b) for a, b in AGE_BINS}
        patients_df = pl.DataFrame(patients)
        report_lines = []
        report_lines.append(f"Scenario: {active_scenario_name}")
        report_lines.append(f"Patients: {len(patients)}")
        report_lines.append(f"Encounters: {len(all_encounters)}")
        report_lines.append(f"Conditions: {len(all_conditions)}")
        report_lines.append(f"Medications: {len(all_medications)}")
        report_lines.append(f"Allergies: {len(all_allergies)}")
        report_lines.append(f"Procedures: {len(all_procedures)}")
        report_lines.append(f"Immunizations: {len(all_immunizations)}")
        report_lines.append(f"Observations: {len(all_observations)}")
        report_lines.append(f"Deaths: {len(all_deaths)}")
        report_lines.append(f"Family History: {len(all_family_history)}")
        report_lines.append("")
        # Age
        ages = patients_df["age"].to_list()
        age_counts = value_counts(ages, bins=age_bins_dict)
        report_lines.append("Age distribution:")
        for k, v in age_counts.items():
            report_lines.append(f"  {k}: {v}")
        # Gender
        report_lines.append("Gender distribution:")
        for k, v in value_counts(patients_df["gender"].to_list()).items():
            report_lines.append(f"  {k}: {v}")
        # Race
        report_lines.append("Race distribution:")
        for k, v in value_counts(patients_df["race"].to_list()).items():
            report_lines.append(f"  {k}: {v}")
        # SDOH fields
        for field, label in [
            ("smoking_status", "Smoking"),
            ("alcohol_use", "Alcohol"),
            ("education", "Education"),
            ("employment_status", "Employment"),
            ("housing_status", "Housing"),
        ]:
            report_lines.append(f"{label} distribution:")
            for k, v in value_counts(patients_df[field].to_list()).items():
                report_lines.append(f"  {k}: {v}")
        # Top conditions
        cond_names = [c["name"] for c in all_conditions]
        cond_counts = value_counts(cond_names)
        report_lines.append("Top 10 conditions:")
        for k, v in cond_counts.most_common(10):
            report_lines.append(f"  {k}: {v}")
    
        if not args.skip_vista and vista_stats:
            report_lines.append("")
            report_lines.append("VistA MUMPS Global Export Summary:")
            report_lines.append(f"  Total global nodes: {vista_stats['total_globals']}")
            report_lines.append(f"  Patient records (^DPT): {vista_stats['patient_records']}")
            report_lines.append(f"  Visit records (^AUPNVSIT): {vista_stats['visit_records']}")
            report_lines.append(f"  Problem records (^AUPNPROB): {vista_stats['problem_records']}")
            report_lines.append(f"  Medication records (^AUPNVMED): {vista_stats.get('medication_records', 0)}")
            report_lines.append(f"  Lab records (^AUPNVLAB): {vista_stats.get('lab_records', 0)}")
            report_lines.append(f"  Allergy records (^GMR(120.8,)): {vista_stats.get('allergy_records', 0)}")
            report_lines.append(f"  Immunization records (^AUPNVIMM): {vista_stats.get('immunization_records', 0)}")
            report_lines.append(f"  Family history records (^AUPNFH): {vista_stats.get('family_history_records', 0)}")
            report_lines.append(f"  Cross-references: {vista_stats['cross_references']}")
    
        report = "\n".join(report_lines)
        print_and_save_report(report, get_config('report_file', None))
    
    print(f"\nAll outputs saved to: {output_dir}")
    print("Generation completed successfully!")

if __name__ == "__main__":
    main() 
