from env.rewards import compute_reward


def test_reward_increases_with_quality_improvement() -> None:
    reward, components = compute_reward(
        quality_before={"missing_values": 10, "duplicates": 2},
        quality_after={"missing_values": 6, "duplicates": 2},
        operation="clean_missing",
        step_count=1,
        step_budget=10,
        submitted=False,
        validation_passed=False,
        repeated_action=False,
        invalid_action=False,
    )

    assert components["improvement"] == 4.0
    assert reward.total > 0.0


def test_invalid_action_has_penalty() -> None:
    reward, components = compute_reward(
        quality_before={"missing_values": 10},
        quality_after={"missing_values": 10},
        operation="clean_missing",
        step_count=2,
        step_budget=10,
        submitted=False,
        validation_passed=False,
        repeated_action=False,
        invalid_action=True,
    )

    assert components["invalid_action"] == 1.0
    assert reward.safety_penalty >= 0.05


def test_validation_bonus_and_progress_shaping() -> None:
    reward, components = compute_reward(
        quality_before={"missing_values": 12, "duplicates": 3, "outliers": 1},
        quality_after={"missing_values": 8, "duplicates": 1, "outliers": 1},
        operation="validate_constraints",
        step_count=4,
        step_budget=10,
        submitted=True,
        validation_passed=True,
        repeated_action=False,
        invalid_action=False,
        repeat_streak=1,
    )

    assert reward.progress_reward > 0.0
    assert reward.validation_bonus > 0.0
    assert components["category_improvements"]["missing_values"] == 4.0