from typing import Dict, Tuple

from .models import Reward


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
) -> Tuple[Reward, Dict[str, float]]:
    before_total = float(sum(quality_before.values()))
    after_total = float(sum(quality_after.values()))
    improvement = max(0.0, before_total - after_total)

    quality_delta = 0.03 * improvement
    efficiency_penalty = 0.01 if step_count > (step_budget * 0.7) else 0.0
    safety_penalty = 0.0
    if repeated_action:
        safety_penalty += 0.02
    if invalid_action:
        safety_penalty += 0.05

    immediate_reward = quality_delta
    if operation in {"inspect_schema", "profile_column", "validate_constraints"} and not invalid_action:
        immediate_reward += 0.005

    terminal_bonus = 0.0
    if submitted:
        terminal_bonus = 0.2 if validation_passed else -0.1

    reward = Reward(
        immediate_reward=immediate_reward,
        quality_delta=quality_delta,
        efficiency_penalty=efficiency_penalty,
        safety_penalty=safety_penalty,
        terminal_bonus=terminal_bonus,
    )
    components = {
        "improvement": improvement,
        "quality_delta": quality_delta,
        "efficiency_penalty": efficiency_penalty,
        "safety_penalty": safety_penalty,
        "invalid_action": 1.0 if invalid_action else 0.0,
        "terminal_bonus": terminal_bonus,
        "total": reward.total,
    }
    return reward, components
