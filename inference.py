"""
Inference Script for Data Quality Triage Assistant
Compliant with hackathon requirements.
"""

import os
import textwrap
import json
import re
from typing import List, Optional

from openai import OpenAI

from env.environment import DataQualityTriageEnv
from env.models import Action

# MANDATORY: Environment variables
HF_TOKEN = os.getenv("HF_TOKEN")
API_BASE_URL = os.getenv("API_BASE_URL", "https://api.openai.com/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "gpt-4.1-mini")

# Task and benchmark configuration
TASK_NAME = os.getenv("TASK_NAME", "easy_missing_and_dupes")
BENCHMARK = os.getenv("BENCHMARK", "data-quality-triage-assistant")
MAX_STEPS = 16
TEMPERATURE = 0.7
MAX_TOKENS = 200
SUCCESS_SCORE_THRESHOLD = 0.5

JSON_FENCE_RE = re.compile(r"```(?:json)?\s*([\s\S]*?)\s*```", re.IGNORECASE)

SYSTEM_PROMPT = textwrap.dedent(
    """
    You are an expert data quality analyst. Your task is to triage and clean a dataset
    by fixing quality issues. You have a limited action budget.
    
    Available operations:
    - inspect_schema: View the dataset schema
    - profile_column: Analyze a specific column
    - clean_missing: Handle missing values in columns
    - deduplicate: Remove duplicate rows
    - cast_type: Change column data types
    - normalize_categories: Standardize categorical values
    - cap_outliers: Handle extreme values
    - validate_constraints: Validate data constraints
    - submit: Submit the cleaned dataset

    Target column guidance:
    - Use target_columns=["*"] when an operation should apply to the whole dataset.
    - deduplicate often works best with target_columns=["*"] unless a specific subset is required.
    
    For each action, respond with a JSON dict:
    {"operation": "<op>", "target_columns": [...], "parameters": {...}}
    
    Analyze the quality report, identify critical issues, and fix them efficiently.
    """
).strip()


def log_start(task: str, env: str, model: str) -> None:
    """Log episode start."""
    print(f"[START] task={task} env={env} model={model}", flush=True)


def log_step(
    step: int, action: str, reward: float, done: bool, error: Optional[str]
) -> None:
    """Log step result."""
    error_val = error if error else "null"
    done_val = str(done).lower()
    print(
        f"[STEP] step={step} action={action} reward={reward:.2f} done={done_val} error={error_val}",
        flush=True,
    )


def log_end(success: bool, steps: int, rewards: List[float]) -> None:
    """Log episode end."""
    rewards_str = ",".join(f"{r:.2f}" for r in rewards)
    print(
        f"[END] success={str(success).lower()} steps={steps} rewards={rewards_str}",
        flush=True,
    )


def build_user_prompt(
    step: int, obs_dict: dict, last_reward: float, history: List[str]
) -> str:
    """Build user prompt with current observation."""
    history_block = "\n".join(history[-3:]) if history else "None"
    return textwrap.dedent(
        f"""
        Step: {step}
        Dataset: {obs_dict.get('dataset_id', 'unknown')}
        Quality Report: {obs_dict.get('quality_report', {})}
        Validation Status: {obs_dict.get('validation_passed', False)}
        Governance Warning: {obs_dict.get('governance_warning', None)}
        Steps Remaining: {obs_dict.get('step_budget_remaining', 0)}
        Last Reward: {last_reward:.2f}
        
        Recent Actions:
        {history_block}
        
        Decide your next action. Respond with JSON.
        """
    ).strip()


def extract_action_payload(raw_text: str) -> dict:
    """Parse action payload from plain or markdown-fenced JSON text."""
    candidates: list[str] = []
    text = (raw_text or "").strip()
    if text:
        candidates.append(text)

    fence_match = JSON_FENCE_RE.search(text)
    if fence_match:
        fenced = (fence_match.group(1) or "").strip()
        if fenced:
            candidates.append(fenced)

    decoder = json.JSONDecoder()
    for candidate in candidates:
        try:
            payload = json.loads(candidate)
            if isinstance(payload, dict):
                return payload
        except Exception:
            pass

        for idx, ch in enumerate(candidate):
            if ch != "{":
                continue
            try:
                payload, _end = decoder.raw_decode(candidate[idx:])
                if isinstance(payload, dict):
                    return payload
            except Exception:
                continue

    raise ValueError("No valid JSON object found in model response")


def get_model_action(
    client: OpenAI,
    step: int,
    obs_dict: dict,
    last_reward: float,
    history: List[str],
) -> tuple[dict, Optional[str]]:
    """Get next action from LLM model."""
    user_prompt = build_user_prompt(step, obs_dict, last_reward, history)
    try:
        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=TEMPERATURE,
            max_tokens=MAX_TOKENS,
            stream=False,
        )
        text = (completion.choices[0].message.content or "").strip()
        action_dict = extract_action_payload(text)
        return action_dict, None
    except Exception as exc:
        # Controlled fallback with explicit error marker for STEP logging.
        return (
            {"operation": "inspect_schema", "target_columns": [], "parameters": {}},
            f"model_request_failed:{type(exc).__name__}",
        )


def main() -> None:
    """Main inference loop."""
    history: List[str] = []
    rewards: List[float] = []
    steps_taken = 0
    success = False
    final_score = 0.001
    terminal_error: Optional[str] = None
    env: Optional[DataQualityTriageEnv] = None

    log_start(task=TASK_NAME, env=BENCHMARK, model=MODEL_NAME)

    try:
        if not HF_TOKEN:
            raise ValueError("HF_TOKEN environment variable not set")

        client = OpenAI(base_url=API_BASE_URL, api_key=HF_TOKEN)
        env = DataQualityTriageEnv(task_id=TASK_NAME)

        # Reset environment
        obs = env.reset()
        obs_dict = obs.model_dump()
        last_reward = 0.0

        for step in range(1, MAX_STEPS + 1):
            # Get action from model
            action_dict, model_error = get_model_action(client, step, obs_dict, last_reward, history)

            controlled_error = model_error

            # Create Action object
            try:
                action = Action(**action_dict)
            except Exception as exc:
                controlled_error = f"invalid_action_payload:{type(exc).__name__}"
                action = Action(operation="inspect_schema", target_columns=[], parameters={})

            # Step environment
            try:
                obs_result, reward_obj, done, info = env.step(action)
            except Exception as exc:
                # Emit a terminal STEP with controlled error to preserve evaluator parsing.
                reward = 0.0
                rewards.append(reward)
                steps_taken = step
                controlled_error = f"env_step_failed:{type(exc).__name__}"
                log_step(
                    step=step,
                    action=f"{action.operation}({','.join(action.target_columns)})",
                    reward=reward,
                    done=True,
                    error=controlled_error,
                )
                terminal_error = controlled_error
                break

            obs_dict = obs_result.model_dump()

            reward = reward_obj.total if hasattr(reward_obj, "total") else 0.0
            info_error = info.get("error") if isinstance(info, dict) else None
            error = controlled_error or info_error

            rewards.append(reward)
            steps_taken = step
            last_reward = reward

            if isinstance(info, dict):
                info_final_score = info.get("final_score")
                if isinstance(info_final_score, (int, float)):
                    final_score = float(info_final_score)

            # Log step
            action_str = f"{action.operation}({','.join(action.target_columns)})"
            log_step(
                step=step,
                action=action_str,
                reward=reward,
                done=done,
                error=error,
            )

            history.append(f"Step {step}: {action_str} -> {reward:+.2f}")

            if done:
                break

        # Compute success from environment final_score on terminal step.
        success = final_score >= SUCCESS_SCORE_THRESHOLD and terminal_error is None

    except Exception as e:
        terminal_error = str(e)
    finally:
        if env is not None and hasattr(env, "close"):
            try:
                env.close()
            except Exception:
                pass
        log_end(success=success, steps=steps_taken, rewards=rewards)


if __name__ == "__main__":
    main()
