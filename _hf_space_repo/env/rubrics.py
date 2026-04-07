from __future__ import annotations

from typing import Any

from openenv.core.rubrics import Rubric

from .graders import grade_task
from .tasks import get_task


class TaskGradeRubric(Rubric):
    def __init__(self, task_id: str) -> None:
        super().__init__()
        self.task_id = task_id

    def forward(self, action: Any, observation: Any) -> float:
        task = get_task(self.task_id)
        quality_report = getattr(observation, "quality_report", {}) or {}
        validation_passed = bool(getattr(observation, "validation_passed", False))
        action_history = list(getattr(observation, "action_history", []) or [])
        submitted = "submit" in action_history
        step_count = len(action_history)
        return grade_task(
            task=task,
            quality_report=quality_report,
            validation_passed=validation_passed,
            submitted=submitted,
            step_count=step_count,
        )


class DataQualityTriageRubric(Rubric):
    def __init__(self) -> None:
        super().__init__()
        self.easy_missing_and_dupes = TaskGradeRubric("easy_missing_and_dupes")
        self.medium_type_and_category = TaskGradeRubric("medium_type_and_category")
        self.hard_conflicts_and_budget = TaskGradeRubric("hard_conflicts_and_budget")

    def forward(self, action: Any, observation: Any) -> float:
        task_id = getattr(observation, "task_id", "easy_missing_and_dupes")
        rubric = self.get_rubric(task_id) if task_id in {name for name, _ in self.named_children()} else self.easy_missing_and_dupes
        return rubric(action, observation)