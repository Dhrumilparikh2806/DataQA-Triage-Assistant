import json
import os
import sys
from typing import Dict, List

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from env.environment import DataQualityTriageEnv
from env.models import Action

TASKS = [
    "easy_missing_and_dupes",
    "medium_type_and_category",
    "hard_conflicts_and_budget",
]


def _good_policy() -> List[Action]:
    return [
        Action(operation="inspect_schema"),
        Action(operation="clean_missing", target_columns=["amount"]),
        Action(operation="deduplicate"),
        Action(operation="cast_type", target_columns=["amount"]),
        Action(operation="normalize_categories", target_columns=["region"]),
        Action(operation="cap_outliers", target_columns=["amount"]),
        Action(operation="validate_constraints"),
        Action(operation="submit"),
    ]


def _bad_policy() -> List[Action]:
    return [
        Action(operation="clean_missing"),
        Action(operation="clean_missing"),
        Action(operation="clean_missing"),
        Action(operation="profile_column"),
        Action(operation="profile_column"),
        Action(operation="submit"),
    ]


def run_policy(task_id: str, policy: List[Action]) -> Dict[str, object]:
    env = DataQualityTriageEnv(task_id=task_id)
    env.reset()

    cumulative_reward = 0.0
    done = False
    info = {"final_score": 0.0}

    for action in policy:
        _obs, reward, done, info = env.step(action)
        cumulative_reward += reward.total
        if done:
            break

    if not done:
        _obs, reward, done, info = env.step(Action(operation="submit"))
        cumulative_reward += reward.total

    return {
        "cumulative_reward": cumulative_reward,
        "final_score": float(info.get("final_score", 0.0)),
        "evaluation": env.evaluate_run(),
    }


def main() -> None:
    results: Dict[str, Dict[str, Dict[str, float]]] = {}

    for task_id in TASKS:
        good = run_policy(task_id, _good_policy())
        bad = run_policy(task_id, _bad_policy())
        results[task_id] = {
            "good_policy": good,
            "bad_policy": bad,
        }

    output = {
        "results": results,
    }

    out_path = os.path.join("scripts", "trajectory_eval_results.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)

    print(json.dumps(output, indent=2))
    print(f"Saved trajectory evaluation results to {out_path}")


if __name__ == "__main__":
    main()
