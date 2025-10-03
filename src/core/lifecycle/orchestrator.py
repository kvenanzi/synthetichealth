"""Lifecycle orchestration helpers."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .models import Patient as LifecyclePatient


@dataclass
class LifecycleOrchestrator:
    """Constructs lifecycle-aware patient payloads."""

    scenario_name: str = "unspecified"
    scenario_details: Dict[str, Any] = field(default_factory=dict)

    def build_patient(
        self,
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
    ) -> LifecyclePatient:
        """Assemble a `LifecyclePatient` enriched with scenario metadata."""

        merged_metadata: Dict[str, Any] = dict(metadata or {})
        merged_metadata.setdefault("scenario", self.scenario_name)
        if self.scenario_details:
            merged_metadata.setdefault("scenario_details", self.scenario_details)

        patient_payload = dict(patient)
        for summary_key in (
            "care_plan_total",
            "care_plan_completed",
            "care_plan_overdue",
            "care_plan_scheduled",
            "care_plan_in_progress",
        ):
            if summary_key in merged_metadata and summary_key not in patient_payload:
                patient_payload[summary_key] = merged_metadata[summary_key]

        return LifecyclePatient.from_legacy(
            patient_payload,
            encounters=encounters,
            conditions=conditions,
            medications=medications,
            immunizations=immunizations,
            observations=observations,
            allergies=allergies,
            procedures=procedures,
            family_history=family_history,
            death=death,
            metadata=merged_metadata,
        )
