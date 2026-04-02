from env.graders import grade_task
from env.tasks import get_task


def test_grade_bounds() -> None:
    task = get_task("easy_missing_and_dupes")
    score = grade_task(
        task=task,
        quality_report=task.initial_quality_report,
        validation_passed=False,
        submitted=True,
        step_count=task.step_budget,
    )
    assert 0.0 <= score <= 1.0


def test_grade_improves_when_quality_improves() -> None:
    task = get_task("easy_missing_and_dupes")

    bad_score = grade_task(
        task=task,
        quality_report=task.initial_quality_report,
        validation_passed=False,
        submitted=True,
        step_count=task.step_budget,
    )
    good_score = grade_task(
        task=task,
        quality_report=task.target_quality_report,
        validation_passed=True,
        submitted=True,
        step_count=3,
    )

    assert good_score > bad_score