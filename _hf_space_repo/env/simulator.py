from copy import deepcopy
from typing import Dict, Tuple

from .models import Action

# Deterministic per-operation reduction for quality issue categories.
OP_EFFECTS: Dict[str, Dict[str, int]] = {
    "inspect_schema": {},
    "profile_column": {},
    "clean_missing": {"missing_values": 4},
    "deduplicate": {"duplicates": 3},
    "cast_type": {"invalid_types": 4},
    "normalize_categories": {"category_inconsistency": 5},
    "cap_outliers": {"outliers": 3},
    "validate_constraints": {},
    "submit": {},
}


def apply_action(quality_report: Dict[str, int], action: Action) -> Tuple[Dict[str, int], Dict[str, int]]:
    updated = deepcopy(quality_report)
    delta: Dict[str, int] = {}

    effects = OP_EFFECTS.get(action.operation, {})
    for key, decrement in effects.items():
        before = updated.get(key, 0)
        after = max(0, before - decrement)
        updated[key] = after
        delta[key] = before - after

    return updated, delta


def quality_score(quality_report: Dict[str, int]) -> float:
    total_issues = sum(max(0, v) for v in quality_report.values())
    # Keep the quality score strictly inside (0, 1) for validator compatibility.
    raw_score = 1.0 / (1.0 + float(total_issues))
    epsilon = 0.001
    return max(epsilon, min(1.0 - epsilon, raw_score))
