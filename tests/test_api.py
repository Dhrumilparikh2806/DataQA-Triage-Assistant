from env.environment import DataQualityTriageEnv
from env.models import Action


def test_reset_returns_initial_observation() -> None:
    env = DataQualityTriageEnv(task_id="easy_missing_and_dupes")
    obs = env.reset()

    assert obs.task_id == "easy_missing_and_dupes"
    assert obs.step_budget_remaining == 8
    assert obs.quality_report["missing_values"] == 12


def test_step_progresses_and_updates_state() -> None:
    env = DataQualityTriageEnv(task_id="easy_missing_and_dupes")
    env.reset()

    obs, reward, done, info = env.step(Action(operation="clean_missing", target_columns=["amount"]))

    assert done is False
    assert reward.quality_delta > 0
    assert info["step_count"] == 1
    assert obs.quality_report["missing_values"] == 8


def test_invalid_action_is_penalized() -> None:
    env = DataQualityTriageEnv(task_id="easy_missing_and_dupes")
    env.reset()

    _obs, reward, _done, info = env.step(Action(operation="clean_missing"))

    assert info["invalid_action"] is True
    assert reward.safety_penalty >= 0.05
