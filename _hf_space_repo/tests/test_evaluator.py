from env.environment import DataQualityTriageEnv
from env.models import Action


def test_evaluator_rejects_bad_trajectory() -> None:
    env = DataQualityTriageEnv(task_id="easy_missing_and_dupes")
    env.reset()

    actions = [
        Action(operation="clean_missing"),
        Action(operation="clean_missing"),
        Action(operation="profile_column"),
        Action(operation="submit"),
    ]
    for action in actions:
        _obs, _reward, done, _info = env.step(action)
        if done:
            break

    result = env.evaluate_run()

    assert result["decision"] == "rejected"
    assert len(result["failed_gates"]) >= 1


def test_evaluator_approves_good_trajectory() -> None:
    env = DataQualityTriageEnv(task_id="easy_missing_and_dupes")
    env.reset()

    actions = [
        Action(operation="inspect_schema"),
        Action(operation="clean_missing", target_columns=["amount"]),
        Action(operation="deduplicate"),
        Action(operation="validate_constraints"),
        Action(operation="submit"),
    ]
    for action in actions:
        _obs, _reward, done, _info = env.step(action)
        if done:
            break

    result = env.evaluate_run()

    assert result["decision"] == "approved"
    assert "leaderboard_record" in result
    assert 0.0 <= float(result["metrics"]["composite_score"])
