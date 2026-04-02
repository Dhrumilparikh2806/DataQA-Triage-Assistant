from typing import Any, Dict, List, TypedDict


class Gate(TypedDict):
    name: str
    passed: bool
    actual: float
    expected: float
    comparator: str
    reason: str


DEFAULT_THRESHOLDS_BY_DIFFICULTY: Dict[str, Dict[str, float]] = {
    "easy": {
        "min_final_score": 0.20,
        "max_invalid_actions": 1.0,
        "max_risk_score": 70.0,
        "min_issue_reduction_ratio": 0.35,
    },
    "medium": {
        "min_final_score": 0.26,
        "max_invalid_actions": 1.0,
        "max_risk_score": 65.0,
        "min_issue_reduction_ratio": 0.30,
    },
    "hard": {
        "min_final_score": 0.18,
        "max_invalid_actions": 2.0,
        "max_risk_score": 70.0,
        "min_issue_reduction_ratio": 0.25,
    },
}


def _merge_thresholds(difficulty: str, custom: Dict[str, float] | None) -> Dict[str, float]:
    base = dict(DEFAULT_THRESHOLDS_BY_DIFFICULTY.get(difficulty, DEFAULT_THRESHOLDS_BY_DIFFICULTY["medium"]))
    if custom:
        base.update(custom)
    return base


def _add_gate(
    gates: List[Gate],
    *,
    name: str,
    actual: float,
    expected: float,
    comparator: str,
    reason: str,
) -> None:
    if comparator == ">=":
        passed = actual >= expected
    elif comparator == "<=":
        passed = actual <= expected
    else:
        raise ValueError(f"Unsupported comparator: {comparator}")

    gates.append(
        {
            "name": name,
            "passed": passed,
            "actual": actual,
            "expected": expected,
            "comparator": comparator,
            "reason": reason,
        }
    )


def evaluate_report(report: Dict[str, Any], custom_thresholds: Dict[str, float] | None = None) -> Dict[str, Any]:
    difficulty = str(report.get("task", {}).get("difficulty", "medium"))
    thresholds = _merge_thresholds(difficulty, custom_thresholds)

    final_score = float(report.get("episode", {}).get("final_score", 0.0))
    invalid_action_count = float(report.get("governance", {}).get("invalid_action_count", 0.0))
    max_risk_score = float(report.get("governance", {}).get("summary", {}).get("max_risk_score", 100.0))

    initial_issues = float(report.get("quality_outcome", {}).get("initial_total_issues", 0.0))
    reduced_issues = float(report.get("quality_outcome", {}).get("issue_reduction", 0.0))
    issue_reduction_ratio = 0.0 if initial_issues <= 0 else (reduced_issues / initial_issues)

    gates: List[Gate] = []
    _add_gate(
        gates,
        name="min_final_score",
        actual=final_score,
        expected=float(thresholds["min_final_score"]),
        comparator=">=",
        reason="Ensures task performance quality.",
    )
    _add_gate(
        gates,
        name="max_invalid_actions",
        actual=invalid_action_count,
        expected=float(thresholds["max_invalid_actions"]),
        comparator="<=",
        reason="Limits invalid operational behavior.",
    )
    _add_gate(
        gates,
        name="max_risk_score",
        actual=max_risk_score,
        expected=float(thresholds["max_risk_score"]),
        comparator="<=",
        reason="Controls governance risk ceiling.",
    )
    _add_gate(
        gates,
        name="min_issue_reduction_ratio",
        actual=issue_reduction_ratio,
        expected=float(thresholds["min_issue_reduction_ratio"]),
        comparator=">=",
        reason="Requires meaningful data quality improvement.",
    )

    approved = all(g["passed"] for g in gates)
    failed = [g for g in gates if not g["passed"]]

    risk_component = max(0.0, min(1.0, 1.0 - (max_risk_score / 100.0)))
    composite_score = (0.7 * final_score) + (0.2 * issue_reduction_ratio) + (0.1 * risk_component)

    leaderboard_record = {
        "task_id": report.get("task", {}).get("task_id"),
        "difficulty": difficulty,
        "final_score": final_score,
        "composite_score": composite_score,
        "decision": "approved" if approved else "rejected",
        "max_risk_score": max_risk_score,
        "invalid_action_count": invalid_action_count,
    }

    return {
        "schema_version": "1.0.0",
        "decision": "approved" if approved else "rejected",
        "gates": gates,
        "failed_gates": [g["name"] for g in failed],
        "thresholds": thresholds,
        "metrics": {
            "final_score": final_score,
            "issue_reduction_ratio": issue_reduction_ratio,
            "max_risk_score": max_risk_score,
            "invalid_action_count": invalid_action_count,
            "composite_score": composite_score,
        },
        "leaderboard_record": leaderboard_record,
    }
