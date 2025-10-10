import os
from pathlib import Path

import pytest

from src.core.parameters import get_parameter, load_parameter_domain, PARAMETER_ROOT_ENV


@pytest.fixture()
def parameter_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    from src.core.parameters import load_parameter_domain

    load_parameter_domain.cache_clear()  # type: ignore[attr-defined]

    root = tmp_path / "parameters"
    root.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv(PARAMETER_ROOT_ENV, str(root))
    return root


def test_load_parameter_domain_reads_yaml(parameter_root: Path) -> None:
    (parameter_root / "asthma.yaml").write_text(
        """
parameters:
  attack_rate_semiannual:
    value: 0.265
""",
        encoding="utf-8",
    )

    params = load_parameter_domain("asthma")
    assert params["attack_rate_semiannual"]["value"] == pytest.approx(0.265)


def test_get_parameter_returns_nested_value(parameter_root: Path) -> None:
    (parameter_root / "copd.yaml").write_text(
        """
parameters:
  exacerbations_per_year_mean:
    value: 0.8
  staging:
    gold_1:
      prevalence: 0.1
""",
        encoding="utf-8",
    )

    value = get_parameter("copd", "staging.gold_1.prevalence")
    assert value == pytest.approx(0.1)


def test_get_parameter_missing_domain_raises(parameter_root: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_parameter_domain("missing_domain")


def test_get_parameter_default(parameter_root: Path) -> None:
    (parameter_root / "empty.yaml").write_text(
        """
parameters:
  placeholder: {}
""",
        encoding="utf-8",
    )

    assert get_parameter("empty", "not.present", default="fallback") == "fallback"
    with pytest.raises(KeyError):
        get_parameter("empty", "not.present")
