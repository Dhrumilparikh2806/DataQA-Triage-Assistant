from typing import Any, Dict

from .tasks import TaskDefinition, get_task

def _extract_report(report: Dict[str, Any]):
    task = get_task(report["task"]["task_id"])
    quality_report = report["quality_outcome"]["final_quality_report"]
    validation_passed = report["episode"]["validation_passed"]
    submitted = report["episode"]["submitted"]
    step_count = report["episode"]["step_count"]
    return task, quality_report, validation_passed, submitted, step_count

# Small epsilon to ensure scores stay strictly within (0, 1)
EPSILON = 0.001

# Explicit task-specific grading profiles to keep task work and scoring distinct.
GRADE_PROFILES = {
    "easy_missing_and_dupes": (0.60, 0.25, 0.15),
    "medium_type_and_category": (0.50, 0.30, 0.20),
    "hard_conflicts_and_budget": (0.45, 0.35, 0.20),
}

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

    quality_weight, validation_weight, budget_weight = GRADE_PROFILES.get(
        task.task_id,
        (0.5, 0.3, 0.2),
    )
    score = (
        (quality_weight * quality_target_score)
        + (validation_weight * validation_score)
        + (budget_weight * budget_efficiency)
    )
    return _bounded(score)


def grade_easy_missing_and_dupes(
    report: Dict[str, Any] = None,
    *,
    task: TaskDefinition = None,
    quality_report: Dict[str, int] = None,
    validation_passed: bool = None,
    submitted: bool = None,
    step_count: int = None,
) -> float:
    if report is not None:
        task, quality_report, validation_passed, submitted, step_count = _extract_report(report)
    return grade_task(
        task=task,
        quality_report=quality_report,
        validation_passed=validation_passed,
        submitted=submitted,
        step_count=step_count,
    )


def grade_medium_type_and_category(
    report: Dict[str, Any] = None,
    *,
    task: TaskDefinition = None,
    quality_report: Dict[str, int] = None,
    validation_passed: bool = None,
    submitted: bool = None,
    step_count: int = None,
) -> float:
    if report is not None:
        task, quality_report, validation_passed, submitted, step_count = _extract_report(report)
    return grade_task(
        task=task,
        quality_report=quality_report,
        validation_passed=validation_passed,
        submitted=submitted,
        step_count=step_count,
    )


def grade_hard_conflicts_and_budget(
    report: Dict[str, Any] = None,
    *,
    task: TaskDefinition = None,
    quality_report: Dict[str, int] = None,
    validation_passed: bool = None,
    submitted: bool = None,
    step_count: int = None,
) -> float:
    if report is not None:
        task, quality_report, validation_passed, submitted, step_count = _extract_report(report)
    return grade_task(
        task=task,
        quality_report=quality_report,
        validation_passed=validation_passed,
        submitted=submitted,
        step_count=step_count,
    )


GRADERS = {
    "easy_missing_and_dupes": grade_easy_missing_and_dupes,
    "medium_type_and_category": grade_medium_type_and_category,
    "hard_conflicts_and_budget": grade_hard_conflicts_and_budget,
}
