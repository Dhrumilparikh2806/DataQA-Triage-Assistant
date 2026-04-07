from env.tasks import TASKS, get_task


def test_task_registry_has_required_difficulties() -> None:
    difficulties = {task.difficulty for task in TASKS.values()}
    assert {"easy", "medium", "hard"}.issubset(difficulties)


def test_get_task_returns_expected_task() -> None:
    task = get_task("medium_type_and_category")
    assert task.task_id == "medium_type_and_category"
    assert task.step_budget == 10
    assert task.initial_quality_report["invalid_types"] > 0


def test_each_task_has_explicit_grader() -> None:
    for task_id in ("easy_missing_and_dupes", "medium_type_and_category", "hard_conflicts_and_budget"):
        task = get_task(task_id)
        assert task.grader.startswith("env.graders:")


def test_task_registry_exports_are_available() -> None:
    from env import TASK_CONFIGS, TASKS as PACKAGE_TASKS, task_catalog, tasks

    assert len(PACKAGE_TASKS) == 3
    assert len(TASK_CONFIGS) == 3
    assert len(task_catalog) == 3
    assert len(tasks) == 3
