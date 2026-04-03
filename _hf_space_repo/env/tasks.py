from dataclasses import dataclass
from typing import Dict


@dataclass(frozen=True)
class TaskDefinition:
    task_id: str
    dataset_id: str
    difficulty: str
    step_budget: int
    initial_quality_report: Dict[str, int]
    target_quality_report: Dict[str, int]


TASKS: Dict[str, TaskDefinition] = {
    "easy_missing_and_dupes": TaskDefinition(
        task_id="easy_missing_and_dupes",
        dataset_id="sales_small_v1",
        difficulty="easy",
        step_budget=8,
        initial_quality_report={
            "missing_values": 0,
            "duplicates": 0,
            "invalid_types": 0,
            "category_inconsistency": 200,
            "outliers": 0,
        },
        target_quality_report={
            "missing_values": 0,
            "duplicates": 0,
            "invalid_types": 0,
            "category_inconsistency": 0,
            "outliers": 0,
        },
    ),
    "medium_type_and_category": TaskDefinition(
        task_id="medium_type_and_category",
        dataset_id="ops_medium_v2",
        difficulty="medium",
        step_budget=10,
        initial_quality_report={
            "missing_values": 9,
            "duplicates": 4,
            "invalid_types": 8,
            "category_inconsistency": 11,
            "outliers": 4,
        },
        target_quality_report={
            "missing_values": 0,
            "duplicates": 0,
            "invalid_types": 0,
            "category_inconsistency": 0,
            "outliers": 1,
        },
    ),
    "hard_conflicts_and_budget": TaskDefinition(
        task_id="hard_conflicts_and_budget",
        dataset_id="finance_hard_v3",
        difficulty="hard",
        step_budget=12,
        initial_quality_report={
            "missing_values": 17,
            "duplicates": 7,
            "invalid_types": 13,
            "category_inconsistency": 14,
            "outliers": 10,
        },
        target_quality_report={
            "missing_values": 1,
            "duplicates": 0,
            "invalid_types": 0,
            "category_inconsistency": 0,
            "outliers": 2,
        },
    ),
}


def get_task(task_id: str) -> TaskDefinition:
    if task_id not in TASKS:
        available = ", ".join(sorted(TASKS.keys()))
        raise ValueError(f"Unknown task_id '{task_id}'. Available: {available}")
    return TASKS[task_id]
