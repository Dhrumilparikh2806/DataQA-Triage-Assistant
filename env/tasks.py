from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass(frozen=True)
class TaskDefinition:
    task_id: str
    dataset_id: str
    difficulty: str
    step_budget: int
    initial_quality_report: Dict[str, int]
    target_quality_report: Dict[str, int]
    grader: str
    work_objective: str
    primary_operations: tuple[str, ...]
    schema_constraints: Dict[str, Any]
    dataset_mode: str = "synthetic"
    hf_dataset_name: str | None = None
    hf_dataset_config: str | None = None
    hf_dataset_split: str = "train"
    hf_dataset_limit: int = 1000
    hf_column_map: Dict[str, tuple[str, ...]] = field(default_factory=dict)


TASKS: Dict[str, TaskDefinition] = {
    "easy_missing_and_dupes": TaskDefinition(
        task_id="easy_missing_and_dupes",
        dataset_id="sales_small_v1",
        difficulty="easy",
        step_budget=8,
        initial_quality_report={
            "missing_values": 12,
            "duplicates": 5,
            "invalid_types": 0,
            "category_inconsistency": 0,
            "outliers": 1,
        },
        target_quality_report={
            "missing_values": 0,
            "duplicates": 0,
            "invalid_types": 0,
            "category_inconsistency": 0,
            "outliers": 0,
        },
        grader="env.graders:grade_easy_missing_and_dupes",
        work_objective="Resolve missing values and duplicate records quickly while preserving valid schema.",
        primary_operations=("inspect_schema", "clean_missing", "deduplicate", "validate_constraints", "submit"),
        schema_constraints={
            "required_columns": ["order_id", "amount", "region", "timestamp"],
            "allowed_regions": ["North", "South", "East", "West"],
            "amount_min": 0.0,
            "amount_max": 5000.0,
            "require_unique_order_id": True,
            "require_valid_timestamps": True,
        },
        dataset_mode="real_world_ready",
        hf_dataset_name="phihung/titanic",
        hf_dataset_split="train",
        hf_dataset_limit=891,
        hf_column_map={
            "order_id": ("PassengerId",),
            "amount": ("Fare",),
            "region": ("Embarked",),
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
        grader="env.graders:grade_medium_type_and_category",
        work_objective="Correct invalid types and inconsistent categories with controlled outlier handling.",
        primary_operations=("inspect_schema", "profile_column", "cast_type", "normalize_categories", "validate_constraints", "submit"),
        schema_constraints={
            "required_columns": ["order_id", "amount", "region", "timestamp"],
            "allowed_regions": ["North", "South", "East", "West"],
            "amount_min": 0.0,
            "amount_max": 5000.0,
            "require_unique_order_id": True,
            "require_valid_timestamps": True,
        },
        dataset_mode="real_world_ready",
        hf_dataset_name="scikit-learn/adult-census-income",
        hf_dataset_split="train",
        hf_dataset_limit=1000,
        hf_column_map={
            "amount": ("capital.gain", "capital.loss", "hours.per.week"),
            "region": ("native.country",),
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
        grader="env.graders:grade_hard_conflicts_and_budget",
        work_objective="Balance deep conflict cleanup under budget while meeting strict validation constraints.",
        primary_operations=("inspect_schema", "profile_column", "clean_missing", "deduplicate", "cast_type", "normalize_categories", "cap_outliers", "validate_constraints", "submit"),
        schema_constraints={
            "required_columns": ["order_id", "amount", "region", "timestamp"],
            "allowed_regions": ["North", "South", "East", "West"],
            "amount_min": -5000.0,
            "amount_max": 5000.0,
            "require_unique_order_id": True,
            "require_valid_timestamps": True,
        },
        dataset_mode="real_world_ready",
        hf_dataset_name="cestwc/bank-marketing",
        hf_dataset_split="train",
        hf_dataset_limit=1000,
        hf_column_map={
            "amount": ("balance",),
            "region": ("job", "education"),
        },
    ),
}

# Compatibility metadata for validators that scan Python modules directly.
TASK_CONFIGS = [
    {
        "task_id": task.task_id,
        "grader": task.grader,
        "work_objective": task.work_objective,
        "primary_operations": list(task.primary_operations),
        "difficulty": task.difficulty,
        "step_budget": task.step_budget,
    }
    for task in TASKS.values()
]

# Lowercase aliases for validators that import module-level task registries.
TASK_DEFINITIONS = list(TASKS.values())
tasks = TASK_DEFINITIONS
task_definitions = TASK_DEFINITIONS
task_catalog = TASK_CONFIGS


def get_task(task_id: str) -> TaskDefinition:
    if task_id not in TASKS:
        available = ", ".join(sorted(TASKS.keys()))
        raise ValueError(f"Unknown task_id '{task_id}'. Available: {available}")
    return TASKS[task_id]


__all__ = [
    "TaskDefinition",
    "TASKS",
    "TASK_CONFIGS",
    "TASK_DEFINITIONS",
    "tasks",
    "task_definitions",
    "task_catalog",
    "get_task",
]
