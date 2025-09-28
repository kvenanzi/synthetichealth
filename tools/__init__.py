"""Utility scripts for terminology and simulator tooling."""

__all__ = ["build_database"]


def build_database(*args, **kwargs):
    """Proxy to :func:`tools.build_terminology_db.build_database` with lazy import.

    Importing :mod:`build_terminology_db` at module import time forces optional
    dependencies like ``duckdb`` to load even when consumers simply want other
    helpers (e.g., ``import_vsac``). Delaying the import keeps the package
    lightweight for unit tests that only touch the normalization scripts.
    """

    from .build_terminology_db import build_database as _build_database

    return _build_database(*args, **kwargs)
