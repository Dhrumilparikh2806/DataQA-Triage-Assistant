from env.environment import DataQualityTriageEnv
from env.models import Action


def _run(env: DataQualityTriageEnv, actions: list[Action]) -> tuple[float, float]:
    env.reset()
    cumulative = 0.0
    done = False
    info = {"final_score": 0.0}

    for action in actions:
        _obs, reward, done, info = env.step(action)
        cumulative += reward.total
        if done:
            break

    if not done:
        _obs, reward, done, info = env.step(Action(operation="submit"))
        cumulative += reward.total

    return cumulative, float(info["final_score"])


def test_good_trajectory_beats_bad_trajectory() -> None:
    env = DataQualityTriageEnv(task_id="medium_type_and_category")

    good_actions = [
        Action(operation="inspect_schema"),
        Action(operation="clean_missing", target_columns=["amount"]),
        Action(operation="deduplicate"),
        Action(operation="cast_type", target_columns=["amount"]),
        Action(operation="normalize_categories", target_columns=["region"]),
        Action(operation="cap_outliers", target_columns=["amount"]),
        Action(operation="validate_constraints"),
        Action(operation="submit"),
    ]

    bad_actions = [
        Action(operation="clean_missing"),
        Action(operation="clean_missing"),
        Action(operation="profile_column"),
        Action(operation="profile_column"),
        Action(operation="submit"),
    ]

    good_cum_reward, good_final_score = _run(env, good_actions)
    bad_cum_reward, bad_final_score = _run(env, bad_actions)

    assert good_cum_reward > bad_cum_reward
    assert good_final_score > bad_final_score
