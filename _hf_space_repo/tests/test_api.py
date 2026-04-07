from env.environment import DataQualityTriageEnv
from env.models import Action


def test_reset_returns_initial_observation() -> None:
    env = DataQualityTriageEnv(task_id="easy_missing_and_dupes")
    obs = env.reset()

    assert obs.task_id == "easy_missing_and_dupes"
    assert obs.step_budget_remaining == 8
    # Quality report should have valid structure (works for both synthetic and real datasets)
    assert isinstance(obs.quality_report, dict)
    assert all(k in obs.quality_report for k in ["missing_values", "duplicates", "invalid_types", "category_inconsistency", "outliers"])


def test_step_progresses_and_updates_state() -> None:
    env = DataQualityTriageEnv(task_id="easy_missing_and_dupes")
    obs_before = env.reset()
    
    category_inconsistency_before = obs_before.quality_report["category_inconsistency"]

    obs, reward, done, info = env.step(Action(operation="normalize_categories", target_columns=["region"]))

    assert done is False
    assert reward.quality_delta > 0
    assert info["step_count"] == 1
    # Category inconsistency should decrease or stay same after normalize_categories
    assert obs.quality_report["category_inconsistency"] <= category_inconsistency_before


def test_invalid_action_is_penalized() -> None:
    env = DataQualityTriageEnv(task_id="easy_missing_and_dupes")
    env.reset()

    _obs, reward, _done, info = env.step(Action(operation="clean_missing"))

    assert info["invalid_action"] is True
    assert reward.safety_penalty >= 0.05
