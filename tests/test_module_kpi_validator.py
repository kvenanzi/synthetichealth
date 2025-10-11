from __future__ import annotations

import polars as pl
import pytest

from tools.module_kpi_validator import (
    compute_proportion_split,
    compute_event_rate_per_year,
    compute_ed_visits_per_100_ptyears,
    compute_rescue_therapy_fraction,
)


def _base_data(**overrides):
    data = {
        "patients": pl.DataFrame({"patient_id": ["p1", "p2", "p3"]}),
        "observations": pl.DataFrame(),
        "medications": pl.DataFrame(),
        "attributes": pl.DataFrame(),
    }
    data.update(overrides)
    return data


def test_compute_proportion_split_matches_expected_share():
    attributes = pl.DataFrame(
        {
            "patient_id": ["p1", "p2", "p3"],
            "attribute": ["asthma_type", "asthma_type", "asthma_type"],
            "value": ["childhood", "childhood", "lifelong"],
        }
    )
    data = _base_data(attributes=attributes)
    kpi = {
        "name": "childhood_vs_adult_onset",
        "metric": "proportion_split",
        "groups": [
            {"attribute": "asthma_type", "value": "childhood"},
            {"attribute": "asthma_type", "value": "lifelong"},
        ],
        "targets": {"childhood": 2 / 3, "lifelong": 1 / 3},
        "tolerance_abs": 0.01,
    }

    result = compute_proportion_split(kpi, data)

    assert pytest.approx(result.actual["childhood"], rel=1e-6) == 2 / 3
    assert result.within_tolerance


def test_compute_event_rate_per_year_uses_patient_count():
    observations = pl.DataFrame({"panel": ["asthma_attack", "asthma_attack", "asthma_attack"]})
    data = _base_data(observations=observations)
    kpi = {
        "name": "annual_attack_rate",
        "metric": "event_rate_per_year",
        "event": "asthma_attack",
        "target": 1.0,
        "tolerance_abs": 0.1,
    }

    result = compute_event_rate_per_year(kpi, data)

    assert pytest.approx(result.actual, rel=1e-6) == 1.0
    assert result.within_tolerance


def test_compute_ed_visits_per_100_ptyears_scales_by_patients():
    observations = pl.DataFrame({"panel": ["asthma_ed_visit", "asthma_ed_visit"]})
    data = _base_data(observations=observations)
    kpi = {
        "name": "ed_visits_per_100_ptyears",
        "metric": "ed_visits_per_100_ptyears",
        "event": "asthma_ed_visit",
        "target": 66.67,
        "tolerance_abs": 0.5,
    }

    result = compute_ed_visits_per_100_ptyears(kpi, data)

    assert pytest.approx(result.actual, rel=1e-4) == 66.6666666667
    assert result.within_tolerance


def test_compute_rescue_therapy_fraction_handles_zero_division():
    observations = pl.DataFrame({"panel": ["copd_exacerbation"]})
    medications = pl.DataFrame({"therapy_category": ["antibiotic"]})
    data = _base_data(observations=observations, medications=medications)
    kpi = {
        "name": "rescue_fraction",
        "metric": "rescue_therapy_fraction",
        "target": 1.0,
        "tolerance_abs": 0.0,
    }

    result = compute_rescue_therapy_fraction(kpi, data)

    assert result.actual == 1.0
    assert result.within_tolerance

