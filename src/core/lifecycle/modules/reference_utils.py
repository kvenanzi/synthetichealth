from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Set, Tuple

from src.core.parameters import get_parameter


@dataclass(frozen=True)
class ParameterMetadata:
    """Metadata describing a resolved parameter reference."""

    token: str
    domain: str
    path: str
    source_id: Optional[str]


class ParameterResolutionError(ValueError):
    """Raised when a ``use:`` token cannot be resolved to a parameter."""


def _split_token(token: str) -> Tuple[str, str]:
    if "." not in token:
        raise ParameterResolutionError(
            f"Invalid parameter token '{token}'. Expected format '<domain>.<path>'."
        )
    domain, path = token.split(".", 1)
    domain = domain.strip()
    path = path.strip()
    if not domain or not path:
        raise ParameterResolutionError(
            f"Invalid parameter token '{token}'. Expected non-empty domain and path."
        )
    return domain, path


def resolve_use_token(token: str) -> Tuple[Any, ParameterMetadata]:
    """Resolve a ``use:`` token to its parameter value and capture metadata.

    Parameters
    ----------
    token:
        String token in the form ``<domain>.<path>``.

    Returns
    -------
    tuple
        ``(value, metadata)`` where ``value`` is the resolved parameter value
        (preferring the ``value`` field when present) and ``metadata`` captures
        the token plus associated ``source_id`` when available.

    Raises
    ------
    ParameterResolutionError
        If the token cannot be parsed or the parameter does not exist.
    """

    domain, path = _split_token(token)
    try:
        parameter = get_parameter(domain, path)
    except (FileNotFoundError, KeyError) as exc:
        raise ParameterResolutionError(str(exc)) from exc

    source_id: Optional[str] = None
    value = parameter
    if isinstance(parameter, dict):
        source_id = parameter.get("source_id")
        value = parameter.get("value", parameter)

    metadata = ParameterMetadata(
        token=token,
        domain=domain,
        path=path,
        source_id=source_id,
    )
    return value, metadata


def collect_use_tokens(payload: Any) -> Set[str]:
    """Collect all ``use:`` tokens present in the payload."""

    tokens: Set[str] = set()

    def _collect(node: Any) -> None:
        if isinstance(node, dict):
            use_value = node.get("use")
            if isinstance(use_value, str):
                tokens.add(use_value)
            for value in node.values():
                _collect(value)
        elif isinstance(node, list):
            for item in node:
                _collect(item)

    _collect(payload)
    return tokens


def replace_use_tokens(payload: Any, *, record: Optional[Set[str]] = None) -> Any:
    """Return a copy of ``payload`` with any ``use:`` tokens resolved."""

    def _replace(node: Any) -> Any:
        if isinstance(node, dict):
            use_value = node.get("use")
            if isinstance(use_value, str) and len(node) == 1:
                if record is not None:
                    record.add(use_value)
                value, _ = resolve_use_token(use_value)
                return value
            return {key: _replace(value) for key, value in node.items()}
        if isinstance(node, list):
            return [_replace(item) for item in node]
        return node

    return _replace(payload)


def resolve_definition_parameters(definition: Any) -> Dict[str, Set[str]]:
    """Resolve ``use:`` tokens across a module definition in place.

    Returns
    -------
    dict
        Mapping of state name to the set of parameter tokens that were consumed.
    """

    usage: Dict[str, Set[str]] = {}
    states = getattr(definition, "states", {})
    for state_name, state in states.items():
        tokens: Set[str] = set()
        state.data = replace_use_tokens(state.data, record=tokens)
        resolved_transitions: list[dict[str, Any]] = []
        for transition in getattr(state, "transitions", []) or []:
            resolved_transitions.append(
                {
                    key: replace_use_tokens(value, record=tokens)
                    for key, value in transition.items()
                }
            )
        state.transitions = resolved_transitions
        usage[state_name] = tokens
    return usage
