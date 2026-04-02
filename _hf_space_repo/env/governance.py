from typing import Any, Dict, List


def _risk_level(score: int) -> str:
    if score >= 60:
        return "high"
    if score >= 30:
        return "medium"
    return "low"


def assess_step_risk(
    *,
    operation: str,
    invalid_action: bool,
    repeated_action: bool,
    step_count: int,
    step_budget: int,
    quality_before: Dict[str, int],
    quality_after: Dict[str, int],
    validation_passed: bool,
    submitted: bool,
) -> Dict[str, Any]:
    before_total = sum(quality_before.values())
    after_total = sum(quality_after.values())
    improvement = max(0, before_total - after_total)

    flags: List[str] = []
    risk_score = 0

    if invalid_action:
        flags.append("invalid_action")
        risk_score += 40

    if repeated_action:
        flags.append("repeated_action")
        risk_score += 15

    if step_count >= int(0.8 * step_budget) and improvement == 0:
        flags.append("late_no_progress")
        risk_score += 20

    if submitted and not validation_passed:
        flags.append("submitted_without_validation")
        risk_score += 25

    if operation == "cap_outliers" and improvement == 0:
        flags.append("ineffective_outlier_handling")
        risk_score += 10

    recommendations: List[str] = []
    if "invalid_action" in flags:
        recommendations.append("Provide required target_columns for column-specific operations.")
    if "late_no_progress" in flags:
        recommendations.append("Prioritize high-impact cleanup operations before budget is exhausted.")
    if "submitted_without_validation" in flags:
        recommendations.append("Run validate_constraints before submit.")
    if not recommendations:
        recommendations.append("Continue current strategy; risk profile acceptable.")

    return {
        "risk_score": risk_score,
        "risk_level": _risk_level(risk_score),
        "flags": flags,
        "quality_improvement": improvement,
        "recommendations": recommendations,
    }


def summarize_episode(governance_events: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not governance_events:
        return {
            "max_risk_score": 0,
            "avg_risk_score": 0.0,
            "high_risk_steps": 0,
            "top_flags": [],
        }

    risk_scores = [int(evt.get("risk_score", 0)) for evt in governance_events]
    high_risk_steps = sum(1 for score in risk_scores if score >= 60)

    flag_counts: Dict[str, int] = {}
    for evt in governance_events:
        for flag in evt.get("flags", []):
            flag_counts[flag] = flag_counts.get(flag, 0) + 1

    top_flags = sorted(flag_counts.items(), key=lambda kv: (-kv[1], kv[0]))[:3]

    return {
        "max_risk_score": max(risk_scores),
        "avg_risk_score": sum(risk_scores) / len(risk_scores),
        "high_risk_steps": high_risk_steps,
        "top_flags": [{"flag": f, "count": c} for f, c in top_flags],
    }
