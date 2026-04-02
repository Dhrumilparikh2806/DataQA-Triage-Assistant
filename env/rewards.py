from typing import Dict, Tuple

from .models import Reward


CATEGORY_WEIGHTS: Dict[str, float] = {
    "missing_values": 1.0,
    "duplicates": 1.15,
    "invalid_types": 1.25,
    "category_inconsistency": 0.95,
    "outliers": 0.85,
}

ACTION_ALIGNMENT: Dict[str, str] = {
    "clean_missing": "missing_values",
    "deduplicate": "duplicates",
    "cast_type": "invalid_types",
    "normalize_categories": "category_inconsistency",
    "cap_outliers": "outliers",
}


def compute_reward(
    *,
    quality_before: Dict[str, int],
    quality_after: Dict[str, int],
    operation: str,
    step_count: int,
    step_budget: int,
    submitted: bool,
    validation_passed: bool,
    repeated_action: bool,
    invalid_action: bool,
    repeat_streak: int = 1,
) -> Tuple[Reward, Dict[str, float]]:
    before_total = float(sum(max(0, value) for value in quality_before.values()))
    after_total = float(sum(max(0, value) for value in quality_after.values()))
    improvement = max(0.0, before_total - after_total)

    category_improvements: Dict[str, float] = {}
    weighted_improvement = 0.0
    for key, before_value in quality_before.items():
        after_value = float(quality_after.get(key, before_value))
        delta = max(0.0, float(before_value) - after_value)
        if delta > 0:
            category_improvements[key] = delta
            weighted_improvement += delta * CATEGORY_WEIGHTS.get(key, 1.0)

    quality_delta = 0.02 * improvement
    progress_reward = 0.015 * weighted_improvement
    alignment_bonus = 0.0
    aligned_category = ACTION_ALIGNMENT.get(operation)
    if aligned_category and category_improvements.get(aligned_category, 0.0) > 0:
        alignment_bonus = 0.01 * category_improvements[aligned_category]

    validation_bonus = 0.04 if operation == "validate_constraints" and validation_passed else 0.0

    efficiency_penalty = 0.008 if step_count > (step_budget * 0.7) else 0.0
    if step_count > (step_budget * 0.9) and improvement == 0:
        efficiency_penalty += 0.01

    safety_penalty = 0.0
    if repeated_action:
        safety_penalty += 0.02 + (0.01 * max(0, repeat_streak - 1))
    if invalid_action:
        safety_penalty += 0.05

    immediate_reward = alignment_bonus
    if operation in {"inspect_schema", "profile_column", "validate_constraints"} and not invalid_action:
        immediate_reward += 0.005

    terminal_bonus = 0.0
    if submitted:
        terminal_bonus = 0.18 if validation_passed else -0.12

    reward = Reward(
        immediate_reward=immediate_reward,
        quality_delta=quality_delta,
        progress_reward=progress_reward,
        validation_bonus=validation_bonus,
        efficiency_penalty=efficiency_penalty,
        safety_penalty=safety_penalty,
        terminal_bonus=terminal_bonus,
    )
    components = {
        "improvement": improvement,
        "weighted_improvement": weighted_improvement,
        "quality_delta": quality_delta,
        "progress_reward": progress_reward,
        "alignment_bonus": alignment_bonus,
        "validation_bonus": validation_bonus,
        "efficiency_penalty": efficiency_penalty,
        "safety_penalty": safety_penalty,
        "invalid_action": 1.0 if invalid_action else 0.0,
        "repeat_streak": float(repeat_streak),
        "terminal_bonus": terminal_bonus,
        "category_improvements": category_improvements,
        "total": reward.total,
    }
    return reward, components
