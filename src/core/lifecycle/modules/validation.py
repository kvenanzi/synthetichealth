from __future__ import annotations

import math
from typing import Any, Dict, List, Set


class ModuleValidationError(Exception):
    """Raised when a module definition fails structural validation."""

    def __init__(self, module_name: str, issues: List[str]) -> None:
        self.module_name = module_name
        self.issues = issues
        joined = "; ".join(issues)
        message = f"Module '{module_name}' failed validation: {joined}"
        super().__init__(message)


def validate_module_definition(definition: Any) -> List[str]:
    """Return a list of validation issues for the provided module definition."""

    issues: List[str] = []
    states: Dict[str, Any] = getattr(definition, "states", {})
    if "start" not in states:
        issues.append("missing 'start' state")
        return issues

    seen_states: Set[str] = set()
    pending: List[str] = ["start"]

    while pending:
        current = pending.pop()
        if current in seen_states:
            continue
        seen_states.add(current)
        state = states.get(current)
        if state is None:
            continue
        for transition in getattr(state, "transitions", []) or []:
            target = transition.get("to")
            if not target:
                issues.append(f"state '{state.name}' has transition without 'to'")
                continue
            if target != "end":
                pending.append(target)

        if getattr(state, "type", "") == "decision":
            probability_total = 0.0
            for transition in getattr(state, "transitions", []) or []:
                try:
                    probability_total += float(transition.get("probability", 0.0))
                except (TypeError, ValueError):
                    issues.append(
                        f"state '{state.name}' has non-numeric probability '{transition.get('probability')}'"
                    )
            if not math.isclose(probability_total, 1.0, rel_tol=0.05, abs_tol=0.05):
                issues.append(
                    f"state '{state.name}' decision probabilities sum to {probability_total:.2f} (expected ≈1.0)"
                )

    unreachable = set(states.keys()) - seen_states - {"end"}
    if unreachable:
        names = ", ".join(sorted(unreachable))
        issues.append(f"unreachable states detected: {names}")

    for state_name, state in states.items():
        for transition in getattr(state, "transitions", []) or []:
            target = transition.get("to")
            if target in {None, "end"}:
                continue
            if target not in states:
                issues.append(
                    f"state '{state_name}' points to unknown target '{target}'"
                )

    return issues

