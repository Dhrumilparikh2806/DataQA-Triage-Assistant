import json
import os
import sys
from typing import List

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from openai import OpenAI

from env.environment import DataQualityTriageEnv
from env.models import Action

TASKS: List[str] = [
    "easy_missing_and_dupes",
    "medium_type_and_category",
    "hard_conflicts_and_budget",
]

DEFAULT_MODEL = "gpt-4.1-mini"
MAX_TURNS = 10
FALLBACK_TARGETS = {
    "clean_missing": ["amount"],
    "cast_type": ["amount"],
    "normalize_categories": ["region"],
    "cap_outliers": ["amount"],
    "profile_column": ["amount"],
}


def _run_single_task(task_id: str) -> float:
    env = DataQualityTriageEnv(task_id=task_id)
    env.reset()

    # Deterministic scripted baseline policy as placeholder for LLM policy.
    policy = [
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
    idx = 0
    while not done and idx < len(policy):
        _obs, _reward, done, info = env.step(policy[idx])
        idx += 1

    return float(info.get("final_score", 0.0))


def _fallback_policy(step_idx: int) -> Action:
    sequence = [
        "inspect_schema",
        "clean_missing",
        "deduplicate",
        "cast_type",
        "normalize_categories",
        "cap_outliers",
        "validate_constraints",
        "submit",
    ]
    operation = sequence[min(step_idx, len(sequence) - 1)]
    return Action(operation=operation, target_columns=FALLBACK_TARGETS.get(operation, []))


def _llm_action(client: OpenAI, model: str, observation_text: str, step_idx: int) -> Action:
    prompt = (
        "You are controlling a data quality triage environment. "
        "Respond with JSON only: {\"operation\": string, \"target_columns\": string[]}. "
        "Choose one operation that best progresses cleanup and validation. "
        "Never include markdown.\n"
        f"Step: {step_idx}\n"
        f"Observation: {observation_text}"
    )

    resp = client.responses.create(
        model=model,
        temperature=0,
        input=prompt,
    )
    raw_text = (resp.output_text or "").strip()
    try:
        payload = json.loads(raw_text)
        return Action(
            operation=payload.get("operation", "inspect_schema"),
            target_columns=payload.get("target_columns", []),
            parameters=payload.get("parameters", {}),
        )
    except Exception:
        return _fallback_policy(step_idx)


def _run_single_task_with_openai(task_id: str, client: OpenAI, model: str) -> float:
    env = DataQualityTriageEnv(task_id=task_id)
    obs = env.reset()

    done = False
    info = {"final_score": 0.0}
    step_idx = 0
    while not done and step_idx < MAX_TURNS:
        observation_text = json.dumps(obs.model_dump(), sort_keys=True)
        action = _llm_action(client, model, observation_text, step_idx)
        obs, _reward, done, info = env.step(action)
        step_idx += 1

    if not done:
        obs, _reward, done, info = env.step(Action(operation="submit"))

    return float(info.get("final_score", 0.0))


def main() -> None:
    api_key = os.getenv("OPENAI_API_KEY", "")
    model = os.getenv("OPENAI_MODEL", DEFAULT_MODEL)

    if not api_key:
        print("Warning: OPENAI_API_KEY is not set. Running deterministic local baseline policy.")
        scores = {task_id: _run_single_task(task_id) for task_id in TASKS}
    else:
        print(f"Running OpenAI baseline with model={model}, temperature=0, max_turns={MAX_TURNS}")
        client = OpenAI(api_key=api_key)
        scores = {task_id: _run_single_task_with_openai(task_id, client, model) for task_id in TASKS}

    aggregate = sum(scores.values()) / max(1, len(scores))

    result = {
        "scores": scores,
        "aggregate_score": aggregate,
    }

    output_path = os.path.join("scripts", "baseline_results.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    print(json.dumps(result, indent=2))
    print(f"Saved baseline results to {output_path}")


if __name__ == "__main__":
    main()
