from copy import deepcopy
from typing import Any, Dict, Tuple

from .evaluator import evaluate_report
from .graders import grade_task
from .governance import assess_step_risk, summarize_episode
from .models import Action, EnvState, Observation, Reward
from .rewards import compute_reward
from .rubrics import DataQualityTriageRubric
from .simulator import apply_action, build_task_dataset, compute_quality_report, validate_task_constraints
from .tasks import TASK_CONFIGS, TASKS as TASK_MAP, get_task


class DataQualityTriageEnv:
    # Class-level aliases for validators that introspect environment objects directly.
    TASKS = [entry["task_id"] for entry in TASK_CONFIGS]
    TASK_CONFIGS = TASK_CONFIGS
    TASK_DEFINITIONS = list(TASK_MAP.values())
    TASK_GRADERS = {entry["task_id"]: entry["grader"] for entry in TASK_CONFIGS}

    def __init__(self, task_id: str = "easy_missing_and_dupes") -> None:
        self.task_id = task_id
        self._task = get_task(task_id)
        self._state: EnvState | None = None
        self._dataset: list[dict[str, Any]] = []
        self.rubric = DataQualityTriageRubric()

    @staticmethod
    def task_catalog() -> list[dict[str, Any]]:
        return deepcopy(TASK_CONFIGS)

    @staticmethod
    def task_graders() -> dict[str, str]:
        return {entry["task_id"]: entry["grader"] for entry in TASK_CONFIGS}

    @staticmethod
    def task_grader_registry() -> dict[str, str]:
        return DataQualityTriageEnv.task_graders()

    @staticmethod
    def graders() -> dict[str, str]:
        return DataQualityTriageEnv.task_graders()

    @staticmethod
    def tasks() -> list[dict[str, Any]]:
        return DataQualityTriageEnv.task_catalog()

    def reset(self) -> Observation:
        self._task = get_task(self.task_id)
        self._dataset = build_task_dataset(self._task.task_id, self._task.initial_quality_report)
        quality_report = compute_quality_report(self._dataset)
        self._state = EnvState(
            dataset_id=self._task.dataset_id,
            task_id=self._task.task_id,
            step_count=0,
            step_budget=self._task.step_budget,
            quality_report=deepcopy(quality_report),
            validation_passed=False,
            submitted=False,
            action_history=[],
            notes={
                "difficulty": self._task.difficulty,
                "quality_history": [deepcopy(quality_report)],
                "reward_history": [],
                "reward_components_history": [],
                "governance_events": [],
                "invalid_action_count": 0,
                "dataset_rows": len(self._dataset),
                "governance_warning": None,
            },
        )
        return self._to_observation()

    def step(self, action: Action) -> Tuple[Observation, Reward, bool, Dict[str, Any]]:
        if self._state is None:
            raise RuntimeError("Environment must be reset before step().")

        state = self._state
        if state.submitted or state.step_count >= state.step_budget:
            reward, components = compute_reward(
                quality_before=state.quality_report,
                quality_after=state.quality_report,
                operation=action.operation,
                step_count=state.step_count,
                step_budget=state.step_budget,
                submitted=state.submitted,
                validation_passed=state.validation_passed,
                repeated_action=False,
                invalid_action=True,
                repeat_streak=1,
            )
            info: Dict[str, Any] = {
                "reward_components": components,
                "step_count": state.step_count,
                "step_budget": state.step_budget,
                "validation_passed": state.validation_passed,
                "submitted": state.submitted,
                "final_score": grade_task(
                    task=self._task,
                    quality_report=state.quality_report,
                    validation_passed=state.validation_passed,
                    submitted=state.submitted,
                    step_count=state.step_count,
                ),
                "error": "episode_already_done",
                "governance": {
                    "risk_score": 80,
                    "risk_level": "high",
                    "flags": ["episode_already_done"],
                    "quality_improvement": 0,
                    "recommendations": ["Reset the environment before taking new actions."],
                },
            }
            return self._to_observation(), reward, True, info

        state.step_count += 1
        repeat_streak = 1
        for previous_operation in reversed(state.action_history):
            if previous_operation != action.operation:
                break
            repeat_streak += 1
        repeated_action = repeat_streak > 1
        invalid_action = False

        quality_before = deepcopy(state.quality_report)
        if not self._is_action_valid(action):
            invalid_action = True
        else:
            self._dataset = apply_action(self._dataset, action)
            state.quality_report = compute_quality_report(self._dataset)

        if action.operation == "validate_constraints":
            state.validation_passed = self._constraints_satisfied(state.quality_report)
        if action.operation == "submit":
            state.submitted = True

        state.action_history.append(action.operation)

        reward_obj, reward_components = compute_reward(
            quality_before=quality_before,
            quality_after=state.quality_report,
            operation=action.operation,
            step_count=state.step_count,
            step_budget=state.step_budget,
            submitted=state.submitted,
            validation_passed=state.validation_passed,
            repeated_action=repeated_action,
            invalid_action=invalid_action,
            repeat_streak=repeat_streak,
        )

        governance = assess_step_risk(
            operation=action.operation,
            invalid_action=invalid_action,
            repeated_action=repeated_action,
            step_count=state.step_count,
            step_budget=state.step_budget,
            quality_before=quality_before,
            quality_after=state.quality_report,
            validation_passed=state.validation_passed,
            submitted=state.submitted,
        )

        notes = state.notes or {}
        if invalid_action:
            notes["invalid_action_count"] = int(notes.get("invalid_action_count", 0)) + 1
        quality_history = list(notes.get("quality_history", []))
        quality_history.append(deepcopy(state.quality_report))
        notes["quality_history"] = quality_history
        reward_history = list(notes.get("reward_history", []))
        reward_history.append(reward_obj.total)
        notes["reward_history"] = reward_history
        reward_components_history = list(notes.get("reward_components_history", []))
        reward_components_history.append(deepcopy(reward_components))
        notes["reward_components_history"] = reward_components_history
        governance_events = list(notes.get("governance_events", []))
        governance_events.append(governance)
        notes["governance_events"] = governance_events
        notes["governance_warning"] = governance.get("recommendations", [None])[0] if governance.get("flags") else None
        state.notes = notes

        done = state.submitted or state.step_count >= state.step_budget
        final_score = grade_task(
            task=self._task,
            quality_report=state.quality_report,
            validation_passed=state.validation_passed,
            submitted=state.submitted,
            step_count=state.step_count,
        ) if done else 0.001

        info: Dict[str, Any] = {
            "reward_components": reward_components,
            "step_count": state.step_count,
            "step_budget": state.step_budget,
            "validation_passed": state.validation_passed,
            "submitted": state.submitted,
            "final_score": final_score,
            "invalid_action": invalid_action,
            "governance": governance,
        }
        return self._to_observation(), reward_obj, done, info

    def generate_run_report(self) -> Dict[str, Any]:
        if self._state is None:
            raise RuntimeError("Environment has no state. Call reset() first.")

        state = self._state
        notes = state.notes or {}
        quality_history = notes.get("quality_history", [])
        reward_history = notes.get("reward_history", [])
        reward_components_history = notes.get("reward_components_history", [])
        governance_events = notes.get("governance_events", [])

        final_score = grade_task(
            task=self._task,
            quality_report=state.quality_report,
            validation_passed=state.validation_passed,
            submitted=state.submitted,
            step_count=state.step_count,
        )

        initial_total = sum(self._task.initial_quality_report.values())
        final_total = sum(state.quality_report.values())
        reduction = max(0, initial_total - final_total)

        action_counts: Dict[str, int] = {}
        for op in state.action_history:
            action_counts[op] = action_counts.get(op, 0) + 1

        governance_summary = summarize_episode(governance_events)

        return {
            "task": {
                "task_id": self._task.task_id,
                "dataset_id": self._task.dataset_id,
                "difficulty": self._task.difficulty,
                "step_budget": self._task.step_budget,
            },
            "episode": {
                "step_count": state.step_count,
                "submitted": state.submitted,
                "validation_passed": state.validation_passed,
                "final_score": final_score,
                "cumulative_reward": float(sum(reward_history)) if reward_history else 0.0,
            },
            "quality_outcome": {
                "initial_total_issues": initial_total,
                "final_total_issues": final_total,
                "issue_reduction": reduction,
                "target_quality_report": deepcopy(self._task.target_quality_report),
                "final_quality_report": deepcopy(state.quality_report),
            },
            "governance": {
                "summary": governance_summary,
                "invalid_action_count": int(notes.get("invalid_action_count", 0)),
                "events": governance_events,
            },
            "telemetry": {
                "action_counts": action_counts,
                "quality_history": quality_history,
                "reward_history": reward_history,
                "reward_components_history": reward_components_history,
            },
        }

    def evaluate_run(self, thresholds: Dict[str, float] | None = None) -> Dict[str, Any]:
        report = self.generate_run_report()
        return evaluate_report(report, custom_thresholds=thresholds)

    def state(self) -> Dict[str, Any]:
        if self._state is None:
            raise RuntimeError("Environment has no state. Call reset() first.")
        return self._state.model_dump()

    def _to_observation(self) -> Observation:
        if self._state is None:
            raise RuntimeError("Environment has no state. Call reset() first.")
        state = self._state
        schema_summary = {
            "order_id": "string",
            "amount": "float",
            "region": "category",
            "timestamp": "datetime",
        }
        if self._dataset:
            first_row = self._dataset[0]
            schema_summary = {k: type(v).__name__ for k, v in first_row.items()}
        return Observation(
            dataset_id=state.dataset_id,
            task_id=state.task_id,
            schema_summary=schema_summary,
            quality_report=deepcopy(state.quality_report),
            validation_passed=state.validation_passed,
            governance_warning=(state.notes or {}).get("governance_warning"),
            action_history=deepcopy(state.action_history),
            step_budget_remaining=max(0, state.step_budget - state.step_count),
        )

    def _constraints_satisfied(self, quality_report: Dict[str, int]) -> bool:
        for key, target in self._task.target_quality_report.items():
            if quality_report.get(key, 0) > target:
                return False
        if not validate_task_constraints(self._dataset, self._task.schema_constraints):
            return False
        return True

    def _is_action_valid(self, action: Action) -> bool:
        # Column-specific operations must include at least one target column.
        requires_columns = {
            "profile_column",
            "clean_missing",
            "cast_type",
            "normalize_categories",
            "cap_outliers",
        }
        if action.operation in requires_columns and not action.target_columns:
            return False
        valid_columns = {
            "order_id",
            "amount",
            "region",
            "timestamp",
            "*",
            "sales",
            "revenue",
            "sale_amount",
            "amount_usd",
            "date",
            "time",
            "sale_date",
            "id",
        }
        for col in action.target_columns:
            if col not in valid_columns:
                return False
        return True
