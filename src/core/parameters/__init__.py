"""Parameter store utilities for evidence-backed module configuration.

Parameters live under ``data/parameters/<domain>.yaml`` and are referenced by
modules using ``use: <domain>.<path>`` tokens. Each YAML file contains a
``parameters`` mapping which can include nested dictionaries. This helper
exposes convenience loaders with simple caching.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Iterable

import yaml


PARAMETER_ROOT_ENV = "PARAMETER_ROOT"
DEFAULT_PARAMETER_ROOT = Path("data/parameters")


def _parameter_root() -> Path:
    root_override = os.environ.get(PARAMETER_ROOT_ENV)
    if root_override:
        return Path(root_override)
    return DEFAULT_PARAMETER_ROOT


@lru_cache(maxsize=32)
def load_parameter_domain(domain: str) -> Dict[str, Any]:
    """Load and cache a parameter domain (e.g., ``asthma``).

    Parameters
    ----------
    domain:
        Name of the YAML file (without extension) under ``data/parameters``.

    Returns
    -------
    dict
        Parsed parameters dictionary.

    Raises
    ------
    FileNotFoundError
        If the requested domain YAML file does not exist.
    ValueError
        If the YAML file is missing the ``parameters`` top-level key.
    """

    path = _parameter_root() / f"{domain}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Parameter domain '{domain}' not found at {path}")

    with path.open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle) or {}

    if "parameters" not in payload:
        raise ValueError(f"Parameter domain '{domain}' is missing the 'parameters' key")

    return payload["parameters"]


def get_parameter(domain: str, path: str, default: Any = None) -> Any:
    """Retrieve a nested parameter given a dotted path.

    Example
    -------
    ``get_parameter(\"asthma\", \"attack_rate_semiannual\")``

    Parameters
    ----------
    domain:
        Parameter domain (YAML file name without extension).
    path:
        Dot-delimited path within the ``parameters`` mapping.
    default:
        Value to return if the parameter path is not found. When omitted, a
        ``KeyError`` is raised for missing paths.
    """

    parts: Iterable[str] = path.split(".")
    node: Any = load_parameter_domain(domain)
    for part in parts:
        if isinstance(node, dict) and part in node:
            node = node[part]
        else:
            if default is not None:
                return default
            joined = ".".join(parts)
            raise KeyError(f"Parameter '{domain}.{joined}' not found")
    return node
