import polars as pl
from faker import Faker
import random
import concurrent.futures
import sys
import argparse
import os
import yaml
import json
from datetime import date, datetime, timedelta
import uuid
from collections import defaultdict, Counter
from functools import partial
from pathlib import Path
from typing import List, Dict, Optional, Any, Tuple, Union, Iterable
from tqdm import tqdm

from .terminology_catalogs import LAB_CODES
from .lifecycle import (
    Patient as LifecyclePatient,
    Condition as LifecycleCondition,
    Observation as LifecycleObservation,
    Encounter as LifecycleEncounter,
    MedicationOrder as LifecycleMedicationOrder,
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
    generate_care_plans,
    generate_conditions,
    generate_death,
    generate_encounters,
    generate_family_history,
    generate_immunizations,
    generate_medications,
    generate_observations,
    generate_procedures,
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
        else:
            mrn = patient_record.mrn or patient_record.generate_mrn()
            ssn = patient_record.ssn
            address_lines = [patient_record.address] if patient_record.address else []
            birthdate = patient_record.birthdate
            given_names = [patient_record.first_name]
            phone = getattr(patient_record, "phone", None)

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

        return {
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
        else:
            condition_name = condition.get("name", "")
            onset_date = condition.get("onset_date")
            status = condition.get("status", "active")
            condition_id = condition.get("condition_id", str(uuid.uuid4()))

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

        return {
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
            "onsetDateTime": onset_date,
        }

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

    def create_medication_statement_resource(
        self,
        patient_id: str,
        medication: Union[Dict[str, Any], LifecycleMedicationOrder],
    ) -> Dict[str, Any]:
        medication_id = getattr(medication, "medication_id", None) or str(uuid.uuid4())
        medication_name = getattr(medication, "name", None) or medication.get("medication", "Unknown Medication")
        start_date = getattr(medication, "start_date", None)
        if not start_date:
            start_date = medication.get("start_date") if isinstance(medication, dict) else None
        if isinstance(start_date, datetime):
            effective = start_date.isoformat()
        elif isinstance(start_date, date):
            effective = datetime.combine(start_date, datetime.min.time()).isoformat()
        elif isinstance(start_date, str):
            effective = start_date
        else:
            effective = datetime.now().isoformat()

        rxnorm_code = None
        if isinstance(medication, LifecycleMedicationOrder):
            rxnorm_code = medication.rxnorm_code
        else:
            rxnorm_code = medication.get("rxnorm_code") or medication.get("rxnorm")

        coding: Dict[str, Any] = {
            "coding": [],
        }
        if rxnorm_code:
            rxnorm_entry = self.rxnorm_lookup.get(str(rxnorm_code))
            display = rxnorm_entry.display if rxnorm_entry else medication_name
            coding["coding"].append(
                {
                    "system": "http://www.nlm.nih.gov/research/umls/rxnorm",
                    "code": str(rxnorm_code),
                    "display": display,
                }
            )
            umls_concepts = self.umls_by_source.get(("RXNORM", str(rxnorm_code)), [])
            if umls_concepts:
                extensions = coding["coding"][-1].setdefault("extension", [])
                for concept in umls_concepts:
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
        if not coding["coding"]:
            coding["text"] = medication_name

        dosage = None
        if isinstance(medication, LifecycleMedicationOrder):
            dosage = medication.metadata.get("dosage")
        else:
            dosage = medication.get("dosage")

        resource: Dict[str, Any] = {
            "resourceType": "MedicationStatement",
            "id": medication_id,
            "status": "active",
            "medicationCodeableConcept": coding,
            "subject": {"reference": f"Patient/{patient_id}"},
            "effectiveDateTime": effective,
        }

        if dosage:
            resource["dosage"] = [{"text": dosage}]

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

class HL7v2Formatter:
    """HL7 v2.x message formatter for Phase 2"""
    
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
            "",   # Death Date
            "",   # Death Indicator
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
        
        # PV1 - Patient Visit (if encounter provided)
        if encounter:
            pv1_segments = [
                "PV1",
                "1",  # Set ID
                encounter.get('type', 'O'),  # Patient Class (O=Outpatient, I=Inpatient)
                "CLINIC1^^^VA^CLINIC",  # Assigned Patient Location
                "",   # Admission Type
                "",   # Preadmit Number
                "",   # Prior Patient Location
                "DOE^JOHN^A^^^DR",  # Attending Doctor
                "",   # Referring Doctor
                "",   # Consulting Doctor
                "GIM",  # Hospital Service
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

class VistaFormatter:
    """VistA MUMPS global formatter for Phase 3 - Production accurate VA migration simulation"""
    
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
    def generate_vista_ien() -> str:
        """Generate VistA Internal Entry Number (IEN)"""
        return str(random.randint(1, 999999))
    
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
            globals_dict[f"^DPT({vista_ien},.13)"] = VistaFormatter.sanitize_mumps_string(patient_record.phone)
        
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
        stop_code_mapping = {
            "Wellness Visit": "323",
            "Emergency": "130", 
            "Follow-up": "323",
            "Specialist": "301",
            "Lab": "175",
            "Surgery": "162"
        }
        stop_code = stop_code_mapping.get(encounter.get('type', ''), "323")
        
        # Service category mapping
        service_category = "A"  # Ambulatory care
        if encounter.get('type') == "Emergency":
            service_category = "E"  # Emergency
        elif encounter.get('type') == "Surgery":
            service_category = "I"  # Inpatient
        
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
    def export_vista_globals(patients: List[PatientRecord], encounters: List[Dict], conditions: List[Dict], output_file: str):
        """Export all VistA globals to MUMPS format file"""
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
    lifecycle_patients: List[LifecyclePatient] = []

    print("Generating related healthcare data...")
    for patient in tqdm(patients, desc="Generating healthcare data", unit="patients"):
        # Convert PatientRecord to dict for backward compatibility with existing functions
        patient_dict = patient.to_dict()
        module_result = module_engine.execute(patient_dict) if module_engine else ModuleExecutionResult()
        replaced = module_result.replacements

        encounters = []
        if "encounters" in replaced:
            encounters = module_result.encounters
        else:
            encounters = generate_encounters(patient_dict, module_result.encounters or None)
            if module_result.encounters:
                encounters.extend(module_result.encounters)
        all_encounters.extend(encounters)

        conditions = []
        if "conditions" in replaced:
            conditions = module_result.conditions
        else:
            conditions = generate_conditions(patient_dict, encounters, min_cond=1, max_cond=5)
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

        for condition in conditions:
            if condition.get("precision_markers") and isinstance(condition["precision_markers"], list):
                condition["precision_markers"] = ",".join(condition["precision_markers"])
            if isinstance(condition.get("care_plan"), list):
                condition["care_plan"] = ",".join(condition["care_plan"])
        allergies = generate_allergies(patient_dict)
        all_allergies.extend(allergies)
        procedures = generate_procedures(patient_dict, encounters, conditions)
        if module_result.procedures:
            if "procedures" in replaced:
                procedures = module_result.procedures
            else:
                procedures.extend(module_result.procedures)
        all_procedures.extend(procedures)
        immunizations = generate_immunizations(patient_dict, encounters)
        if module_result.immunizations:
            if "immunizations" in replaced:
                immunizations = module_result.immunizations
            else:
                immunizations.extend(module_result.immunizations)
        all_immunizations.extend(immunizations)
        observations = generate_observations(patient_dict, encounters, conditions)
        if module_result.observations:
            if "observations" in replaced:
                observations = module_result.observations
            else:
                observations.extend(module_result.observations)
        all_observations.extend(observations)
        care_plans = generate_care_plans(patient_dict, conditions, encounters)
        if module_result.care_plans:
            if "care_plans" in replaced:
                care_plans = module_result.care_plans
            else:
                care_plans.extend(module_result.care_plans)
        all_care_plans.extend(care_plans)
        death = generate_death(patient_dict, conditions)
        if death:
            all_deaths.append(death)
        family_history = generate_family_history(patient_dict)
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

        # Refresh the dictionary snapshot so metadata changes are captured
        patient_snapshot = patient.to_dict()
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

        # Add MedicationStatement resources
        for patient in tqdm(patients_list, desc="Creating FHIR Medication resources", unit="patients"):
            if not isinstance(patient, LifecyclePatient):
                continue
            for medication in patient.medications:
                medication_resource = fhir_formatter.create_medication_statement_resource(
                    patient.patient_id, medication
                )
                bundle_entries.append({"resource": medication_resource})

        # Add Observation resources when lifecycle data is available
        for patient in tqdm(patients_list, desc="Creating FHIR Observation resources", unit="patients"):
            if not isinstance(patient, LifecyclePatient):
                continue
            for observation in patient.observations:
                observation_resource = fhir_formatter.create_observation_resource(
                    patient.patient_id, observation
                )
                bundle_entries.append({"resource": observation_resource})

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
    tables_to_save = [
        (pl.DataFrame(patients_dict), "patients"),
        (pl.DataFrame(all_encounters), "encounters"),
        (pl.DataFrame(all_conditions), "conditions"),
        (pl.DataFrame(all_medications), "medications"),
        (pl.DataFrame(all_allergies), "allergies"),
        (pl.DataFrame(all_procedures), "procedures"),
        (pl.DataFrame(all_immunizations), "immunizations"),
        (pl.DataFrame(all_observations), "observations")
    ]
    
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

    print("\nExporting specialized formats...")
    
    # Export FHIR bundle (Phase 1: basic Patient and Condition resources)
    print("Creating FHIR bundle...")
    save_fhir_bundle(lifecycle_patients, terminology_lookup, "fhir_bundle.json")
    save_terminology_reference(terminology_lookup, output_dir)
    
    # Export HL7 v2 messages (Phase 2: ADT and ORU messages)
    print("Creating HL7 v2 messages...")
    save_hl7_messages(lifecycle_patients, all_encounters, all_observations, "hl7_messages")
    
    # Export VistA MUMPS globals (Phase 3: VA migration simulation)
    print("Creating VistA MUMPS globals...")
    vista_formatter = VistaFormatter()
    vista_output_file = os.path.join(output_dir, "vista_globals.mumps")
    vista_stats = vista_formatter.export_vista_globals(patients, all_encounters, all_conditions, vista_output_file)

    print(f"Done! Files written to {output_dir}: patients, encounters, conditions, medications, allergies, procedures, immunizations, observations, deaths, family_history (CSV and/or Parquet), FHIR bundle, HL7 messages, VistA MUMPS globals")

    # Summary report
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
    ages = patients_df['age'].to_list()
    age_counts = value_counts(ages, bins=age_bins_dict)
    report_lines.append("Age distribution:")
    for k, v in age_counts.items():
        report_lines.append(f"  {k}: {v}")
    # Gender
    report_lines.append("Gender distribution:")
    for k, v in value_counts(patients_df['gender'].to_list()).items():
        report_lines.append(f"  {k}: {v}")
    # Race
    report_lines.append("Race distribution:")
    for k, v in value_counts(patients_df['race'].to_list()).items():
        report_lines.append(f"  {k}: {v}")
    # SDOH fields
    for field, label in [
        ('smoking_status', 'Smoking'),
        ('alcohol_use', 'Alcohol'),
        ('education', 'Education'),
        ('employment_status', 'Employment'),
        ('housing_status', 'Housing')]:
        report_lines.append(f"{label} distribution:")
        for k, v in value_counts(patients_df[field].to_list()).items():
            report_lines.append(f"  {k}: {v}")
    # Top conditions
    cond_names = [c['name'] for c in all_conditions]
    cond_counts = value_counts(cond_names)
    report_lines.append("Top 10 conditions:")
    for k, v in cond_counts.most_common(10):
        report_lines.append(f"  {k}: {v}")
    
    # VistA MUMPS global statistics
    report_lines.append("")
    report_lines.append("VistA MUMPS Global Export Summary:")
    report_lines.append(f"  Total global nodes: {vista_stats['total_globals']}")
    report_lines.append(f"  Patient records (^DPT): {vista_stats['patient_records']}")
    report_lines.append(f"  Visit records (^AUPNVSIT): {vista_stats['visit_records']}")
    report_lines.append(f"  Problem records (^AUPNPROB): {vista_stats['problem_records']}")
    report_lines.append(f"  Cross-references: {vista_stats['cross_references']}")
    
    report = "\n".join(report_lines)
    print_and_save_report(report, get_config('report_file', None))
    
    print(f"\nAll outputs saved to: {output_dir}")
    print("Generation completed successfully!")

if __name__ == "__main__":
    main() 
