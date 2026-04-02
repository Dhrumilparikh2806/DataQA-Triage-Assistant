from env.environment import DataQualityTriageEnv
from env.models import Action


def _run_fixed_trajectory(task_id: str) -> tuple[float, dict[str, int]]:
    env = DataQualityTriageEnv(task_id=task_id)
    env.reset()

    actions = [
        Action(operation="inspect_schema"),
        Action(operation="clean_missing", target_columns=["amount"]),
        Action(operation="deduplicate"),
        Action(operation="cast_type", target_columns=["amount"]),
        Action(operation="normalize_categories", target_columns=["region"]),
        Action(operation="cap_outliers", target_columns=["amount"]),
        Action(operation="validate_constraints"),
        Action(operation="submit"),
    ]

    done = False
    info = {"final_score": 0.0}
    for action in actions:
        _obs, _reward, done, info = env.step(action)
        if done:
            break

    assert done is True
    final_state = env.state()
    return float(info["final_score"]), final_state["quality_report"]


def test_same_trajectory_produces_same_result() -> None:
    score_1, quality_1 = _run_fixed_trajectory("medium_type_and_category")
    score_2, quality_2 = _run_fixed_trajectory("medium_type_and_category")

    assert score_1 == score_2
    assert quality_1 == quality_2
