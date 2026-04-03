from env.environment import DataQualityTriageEnv
from env.models import Action


def test_governance_info_present_on_step() -> None:
    env = DataQualityTriageEnv(task_id="easy_missing_and_dupes")
    env.reset()

    _obs, _reward, _done, info = env.step(Action(operation="clean_missing"))

    assert "governance" in info
    assert "risk_score" in info["governance"]
    assert "risk_level" in info["governance"]
    assert "flags" in info["governance"]


def test_generate_run_report_contains_audit_sections() -> None:
    env = DataQualityTriageEnv(task_id="easy_missing_and_dupes")
    env.reset()

    actions = [
        Action(operation="inspect_schema"),
        Action(operation="normalize_categories", target_columns=["region"]),
        Action(operation="validate_constraints"),
        Action(operation="submit"),
    ]
    for action in actions:
        _obs, _reward, done, _info = env.step(action)
        if done:
            break

    report = env.generate_run_report()

    assert "task" in report
    assert "episode" in report
    assert "quality_outcome" in report
    assert "governance" in report
    assert "telemetry" in report
    assert report["episode"]["step_count"] > 0
    assert 0.0 <= report["episode"]["final_score"] <= 1.0