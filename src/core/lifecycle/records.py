"""Lifecycle-level record structures used across generators and exporters."""
from __future__ import annotations

import json
import random
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class PatientRecord:
    """Enhanced patient record with multiple identifiers and SDOH metadata."""

    # Core identifiers
    patient_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    vista_id: Optional[str] = None
    mrn: Optional[str] = None
    ssn: Optional[str] = None

    # Demographics
    first_name: str = ""
    last_name: str = ""
    middle_name: str = ""
    gender: str = ""
    birthdate: str = ""
    age: int = 0
    race: str = ""
    ethnicity: str = ""

    # Address
    address: str = ""
    city: str = ""
    state: str = ""
    zip: str = ""
    country: str = "US"

    # Contact and administrative
    phone: str = ""
    email: str = ""
    marital_status: str = ""
    language: str = ""
    insurance: str = ""

    # SDOH fields
    smoking_status: str = ""
    alcohol_use: str = ""
    education: str = ""
    employment_status: str = ""
    income: int = 0
    housing_status: str = ""

    # Clinical data containers retained for legacy compatibility
    encounters: List[Dict[str, Any]] = field(default_factory=list)
    conditions: List[Dict[str, Any]] = field(default_factory=list)
    medications: List[Dict[str, Any]] = field(default_factory=list)
    allergies: List[Dict[str, Any]] = field(default_factory=list)
    procedures: List[Dict[str, Any]] = field(default_factory=list)
    immunizations: List[Dict[str, Any]] = field(default_factory=list)
    observations: List[Dict[str, Any]] = field(default_factory=list)

    # Metadata for migration simulation and downstream exporters
    metadata: Dict[str, Any] = field(
        default_factory=lambda: {
            "source_system": "synthetic",
            "migration_status": "pending",
            "data_quality_score": 1.0,
            "created_timestamp": datetime.now().isoformat(),
        }
    )

    def generate_vista_id(self) -> str:
        """Generate a simple VistA identifier if one has not been assigned."""

        if not self.vista_id:
            self.vista_id = str(random.randint(1, 9_999_999))
        return self.vista_id

    def generate_mrn(self) -> str:
        """Generate a pseudo Medical Record Number."""

        if not self.mrn:
            self.mrn = f"MRN{random.randint(100000, 999999)}"
        return self.mrn

    def to_dict(self) -> Dict[str, Any]:
        """Convert to a dictionary for backward compatibility with CSV/Parquet exports."""

        return {
            "patient_id": self.patient_id,
            "vista_id": self.vista_id,
            "mrn": self.mrn,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "middle_name": self.middle_name,
            "gender": self.gender,
            "birthdate": self.birthdate,
            "age": self.age,
            "race": self.race,
            "ethnicity": self.ethnicity,
            "address": self.address,
            "city": self.city,
            "state": self.state,
            "zip": self.zip,
            "country": self.country,
            "phone": self.phone,
            "email": self.email,
            "marital_status": self.marital_status,
            "language": self.language,
            "insurance": self.insurance,
            "ssn": self.ssn,
            "smoking_status": self.smoking_status,
            "alcohol_use": self.alcohol_use,
            "education": self.education,
            "employment_status": self.employment_status,
            "income": self.income,
            "housing_status": self.housing_status,
            "sdoh_risk_score": self.metadata.get("sdoh_risk_score", 0.0),
            "sdoh_risk_factors": json.dumps(self.metadata.get("sdoh_risk_factors", [])),
            "community_deprivation_index": self.metadata.get("community_deprivation_index", 0.0),
            "access_to_care_score": self.metadata.get("access_to_care_score", 0.0),
            "transportation_access": self.metadata.get("transportation_access", ""),
            "language_access_barrier": self.metadata.get("language_access_barrier", False),
            "social_support_score": self.metadata.get("social_support_score", 0.0),
            "sdoh_care_gaps": json.dumps(self.metadata.get("sdoh_care_gaps", [])),
            "genetic_risk_score": self.metadata.get("genetic_risk_score", 0.0),
            "genetic_markers": json.dumps(self.metadata.get("genetic_markers", [])),
            "precision_markers": json.dumps(self.metadata.get("precision_markers", [])),
            "comorbidity_profile": json.dumps(self.metadata.get("comorbidity_profile", [])),
            "care_plan_total": self.metadata.get("care_plan_total", 0),
            "care_plan_completed": self.metadata.get("care_plan_completed", 0),
            "care_plan_overdue": self.metadata.get("care_plan_overdue", 0),
            "care_plan_scheduled": self.metadata.get("care_plan_scheduled", 0),
        }


__all__ = ["PatientRecord"]

