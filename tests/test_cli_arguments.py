import sys
from pathlib import Path

import pytest

# Ensure repository root is discoverable when tests execute in isolation.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
root_str = str(PROJECT_ROOT)
if root_str not in sys.path:
    sys.path.insert(0, root_str)

from src.core import synthetic_patient_generator as cli  # noqa: E402


def _invoke_cli(monkeypatch, args):
    original_argv = list(sys.argv)
    monkeypatch.setattr(sys, "argv", ["synthetic_patient_generator", *args])
    try:
        cli.main()
    finally:
        sys.argv = original_argv


def test_cli_lists_scenarios(capfd, monkeypatch):
    _invoke_cli(monkeypatch, ["--list-scenarios"])
    out, err = capfd.readouterr()
    assert err == ""
    assert "Available scenarios:" in out
    assert "general" in out


@pytest.mark.parametrize("flag", ["--list-modules"])
def test_cli_lists_modules(capfd, monkeypatch, flag):
    _invoke_cli(monkeypatch, [flag])
    out, err = capfd.readouterr()
    assert err == ""
    assert "Available modules:" in out
    # sanity check on at least one known module
    assert "cardiometabolic_intensive" in out or "adult_primary_care_wellness" in out
