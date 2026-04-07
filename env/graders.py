from typing import Dict

from .tasks import TaskDefinition

# Small epsilon to ensure scores stay strictly within (0, 1)
EPSILON = 0.001

def _bounded(value: float) -> float:
    """Bound value strictly to (EPSILON, 1-EPSILON) to ensure open interval."""
    return max(EPSILON, min(1.0 - EPSILON, value))


def grade_task(
    *,
    task: TaskDefinition,
    quality_report: Dict[str, int],
    validation_passed: bool,
    submitted: bool,
    step_count: int,
) -> float:
    if not submitted:
        # Return a minimal score for incomplete/unsubmitted episodes, still in (0, 1)
        return EPSILON

    max_reduction = 0.0
    residual_gap = 0.0
    for key, initial_value in task.initial_quality_report.items():
        target_value = float(task.target_quality_report.get(key, 0))
        current_value = float(quality_report.get(key, 0))
        max_reduction += max(0.0, float(initial_value) - target_value)
        residual_gap += max(0.0, current_value - target_value)

    # If no reduction needed, return high score but not 1.0
    quality_target_score = (1.0 - EPSILON) if max_reduction == 0 else (1.0 - (residual_gap / max_reduction))
    quality_target_score = _bounded(quality_target_score)

    # Validation score: if passed return high, if not return low but not exactly 0 or 1
    validation_score = (1.0 - EPSILON) if validation_passed else EPSILON
    budget_efficiency = _bounded(1.0 - (step_count / float(task.step_budget + 1)))

    score = (0.5 * quality_target_score) + (0.3 * validation_score) + (0.2 * budget_efficiency)
    return _bounded(score)
