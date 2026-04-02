from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, computed_field

Operation = Literal[
    "inspect_schema",
    "profile_column",
    "clean_missing",
    "deduplicate",
    "cast_type",
    "normalize_categories",
    "cap_outliers",
    "validate_constraints",
    "submit",
]


class Action(BaseModel):
    operation: Operation
    target_columns: List[str] = Field(default_factory=list)
    parameters: Dict[str, Any] = Field(default_factory=dict)


class Observation(BaseModel):
    dataset_id: str
    task_id: str
    schema_summary: Dict[str, str]
    quality_report: Dict[str, int]
    validation_passed: bool
    action_history: List[str] = Field(default_factory=list)
    step_budget_remaining: int


class Reward(BaseModel):
    immediate_reward: float
    quality_delta: float = 0.0
    progress_reward: float = 0.0
    validation_bonus: float = 0.0
    efficiency_penalty: float = 0.0
    safety_penalty: float = 0.0
    terminal_bonus: float = 0.0

    @computed_field  # type: ignore
    @property
    def total(self) -> float:
        return (
            self.immediate_reward
            + self.quality_delta
            + self.progress_reward
            + self.validation_bonus
            - self.efficiency_penalty
            - self.safety_penalty
            + self.terminal_bonus
        )


class StepResult(BaseModel):
    observation: Observation
    reward: Reward
    done: bool
    info: Dict[str, Any] = Field(default_factory=dict)


class EnvState(BaseModel):
    dataset_id: str
    task_id: str
    step_count: int
    step_budget: int
    quality_report: Dict[str, int]
    validation_passed: bool
    submitted: bool
    action_history: List[str]
    notes: Optional[Dict[str, Any]] = None
