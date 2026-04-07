from env.graders import GRADERS, grade_task
from env.simulator import quality_score
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


def test_task_scores_stay_in_open_interval() -> None:
    for task_id in ("easy_missing_and_dupes", "medium_type_and_category", "hard_conflicts_and_budget"):
        task = get_task(task_id)
        score = grade_task(
            task=task,
            quality_report=task.target_quality_report,
            validation_passed=True,
            submitted=True,
            step_count=1,
        )
        assert 0.0 < score < 1.0


def test_quality_score_stays_in_open_interval() -> None:
    assert 0.0 < quality_score({"missing_values": 0, "duplicates": 0, "invalid_types": 0, "category_inconsistency": 0, "outliers": 0}) < 1.0


def test_explicit_task_graders_registry() -> None:
    expected = {
        "easy_missing_and_dupes",
        "medium_type_and_category",
        "hard_conflicts_and_budget",
    }
    assert expected.issubset(set(GRADERS.keys()))


def test_package_exports_include_grader_registry() -> None:
    from env import GRADERS as PACKAGE_GRADERS, TASK_GRADERS, task_graders

    assert len(PACKAGE_GRADERS) == 3
    assert len(TASK_GRADERS) == 3
    assert len(task_graders) == 3