---
title: Data Quality Triage Assistant - Made by #TEAM Hack-with-Pals
emoji: "📊"
colorFrom: blue
colorTo: green
sdk: docker
app_port: 7860
base_path: /ui
tags:
  - openenv
  - data-analysis
  - evaluation
---

# Data Quality Triage Assistant (OpenEnv)

Made by #TEAM Hack-with-Pals.

## Run Locally (Start Here)

This is the fastest way to run the final project locally.

### 1) Prerequisites
- Python 3.11+
- Docker Desktop (for container run checks)
- OpenEnv CLI available in your environment

### 2) Install dependencies
```bash
pip install -r requirements.txt
```

### 3) Validate project structure
```bash
openenv validate
```

### 4) Run the web app locally
```bash
uvicorn app:app --host 0.0.0.0 --port 7860
```
Open in browser: http://localhost:7860/ui

### 5) Run required inference script
Set required variables:
- API_BASE_URL
- MODEL_NAME
- HF_TOKEN (or API_KEY fallback)

Example:
```bash
python inference.py
```

The script prints strict structured logs:
- [START]
- [STEP]
- [END]

### 6) Optional Docker verification
```bash
docker build -t data-quality-openenv:precheck .
docker run --rm -p 7860:7860 data-quality-openenv:precheck
```

## What This Project Is

Data Quality Triage Assistant by #TEAM Hack-with-Pals is an OpenEnv benchmark environment where an agent performs realistic data quality triage:
1. Inspect data quality state
2. Apply cleaning actions
3. Validate constraints
4. Submit within step budget

This repository is tailored for hackathon evaluation with:
- deterministic behavior
- typed action/observation/reward models
- 3 task difficulties
- governance risk signals
- evaluator gates and leaderboard-compatible metrics

## Project Layout

- app.py: FastAPI server and UI/API routes
- inference.py: required baseline inference script
- openenv.yaml: OpenEnv environment metadata
- env/: core environment implementation
	- env/environment.py: reset/step/report/evaluate flow
	- env/models.py: typed schemas
	- env/tasks.py: task definitions and constraints
	- env/simulator.py: data-backed action effects and quality metrics
	- env/rewards.py: step-level reward decomposition
	- env/graders.py: final episode score in [0.0, 1.0]
	- env/evaluator.py: pass/fail gates and composite scoring
	- env/governance.py: risk flags and recommendations
	- env/fixtures/*.csv: task datasets used at runtime

## Environment Contract

Core methods:
- reset() -> Observation
- step(Action) -> Observation, Reward, done, info
- state() -> internal snapshot
- generate_run_report() -> run summary
- evaluate_run() -> gate-based decision payload

Action operations:
- inspect_schema
- profile_column
- clean_missing
- deduplicate
- cast_type
- normalize_categories
- cap_outliers
- validate_constraints
- submit

Target column wildcard:
- You can pass target_columns=["*"] to apply an operation across the whole dataset.
- This is especially useful for deduplicate when you want full-row duplicate removal.

## Tasks

Configured tasks:
- easy_missing_and_dupes
- medium_type_and_category
- hard_conflicts_and_budget

Each task defines:
- initial quality report
- target quality report
- step budget
- schema constraints (required columns, type/range rules, uniqueness, category constraints)

## Grading and Scoring Logic (Detailed)

This section explains exactly how scores are produced.

### A) Step reward (dense signal during episode)

Defined in env/rewards.py.

For each step, reward is composed of:
- immediate_reward
- quality_delta
- progress_reward
- validation_bonus
- terminal_bonus
- minus efficiency_penalty
- minus safety_penalty

Total formula:

total = immediate_reward + quality_delta + progress_reward + validation_bonus - efficiency_penalty - safety_penalty + terminal_bonus

Key behaviors:
1. Quality improvement adds positive reward.
2. Category-weighted improvements add extra progress reward.
3. validate_constraints adds bonus only when constraints actually pass.
4. Repeated/invalid actions increase safety penalties.
5. Late, low-progress behavior adds efficiency penalties.
6. submit gets terminal bonus if validated, penalty if not.

This creates a non-sparse learning signal while preserving final-objective pressure.

### B) Final task grade (episode score in [0, 1])

Defined in env/graders.py.

Important rule:
- If the agent never submits, final score is 0.0.

When submitted, score blends three components:
1. Quality target score (50%)
2. Validation score (30%)
3. Budget efficiency (20%)

Details:
1. Quality target score measures remaining gap to target issues.
2. Validation score is 1.0 only if validation_passed is true.
3. Budget efficiency rewards completing in fewer steps.

Final grade formula:

score = 0.5 * quality_target_score + 0.3 * validation_score + 0.2 * budget_efficiency

The score is always clamped to [0.0, 1.0].

### C) Evaluation gates (approve/reject decision)

Defined in env/evaluator.py.

After the episode, gates evaluate:
- min_final_score
- max_invalid_actions
- max_risk_score
- min_issue_reduction_ratio

Decision:
- approved if all gates pass
- rejected otherwise

Also produced:
- composite_score for ranking
- leaderboard_record payload

## API Endpoints

- GET /health
- POST /reset
- POST /step
- GET /state
- GET /report
- POST /evaluate
- GET /ui

## Inference Requirements

The submitted inference script is inference.py at repo root.

Required environment variables:
- API_BASE_URL
- MODEL_NAME
- HF_TOKEN

Optional fallback:
- API_KEY

Defaults in script:
- API_BASE_URL = https://router.huggingface.co/v1
- MODEL_NAME = Qwen/Qwen2.5-72B-Instruct

Prompting tip for better baseline quality:
- Explicitly use target_columns=["*"] for global operations (especially deduplicate) instead of hallucinating per-column lists.

## Reproducibility

This project is deterministic by design:
- fixed task definitions
- deterministic fixture loading
- deterministic environment transitions for identical action sequences

Expected outcomes:
- repeated runs of the same action plan on same task yield same final score and step count

## Real Dataset Mode

The environment now prefers real Hugging Face datasets at reset time and falls back to the deterministic fixtures only when loading fails.

Default task sources:
- easy_missing_and_dupes -> `phihung/titanic`
- medium_type_and_category -> `scikit-learn/adult-census-income`
- hard_conflicts_and_budget -> `cestwc/bank-marketing`

You can override the dataset source with these env vars:
- REAL_DATASET_NAME
- REAL_DATASET_CONFIG
- REAL_DATASET_SPLIT (defaults to the task's split or `train`)
- REAL_DATASET_LIMIT

The loader canonicalizes the source rows into the benchmark schema, then computes the baseline quality report directly from the loaded data at `reset()`.
That means the difficulty profile is driven by the actual dataset rows, not by a synthetic error counter.
If the dataset library is unavailable or the remote dataset cannot be loaded, the environment falls back to the built-in fixtures so the benchmark still runs deterministically.

## Hugging Face Space Deployment

This repo is already configured for Docker Space deployment.

Deployment command used in this project:
```bash
openenv push . --private
```

Space should respond to:
- POST /reset (HTTP 200)

## Final Pre-Submission Checklist

Use this exact order:
1. openenv validate
2. docker build -t data-quality-openenv:precheck .
3. python inference.py
4. Verify 3 tasks and grader outputs in [0.0, 1.0]
5. Verify Space /reset returns 200

If all pass, the project is ready for submission.
