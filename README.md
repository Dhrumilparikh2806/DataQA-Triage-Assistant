---
title: Data Quality Triage Assistant
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

Data Quality Triage Assistant is a real-world data-analysis environment where an agent performs dataset triage: inspect, clean, validate, and submit.

## Motivation
Analysts spend significant effort preparing low-quality datasets before meaningful analysis can begin. This environment simulates that practical workflow with objective scoring and deterministic constraints.

## Current Status
Implemented:
- typed Pydantic models for observation/action/reward
- deterministic step/reset/state API
- easy/medium/hard task registry
- deterministic reward and grader modules
- CSV-backed fixtures with per-task schema constraints
- OpenEnv validation and Hugging Face Space deployment

Planned next:
- expand domain-specific constraints per task
- add richer per-column profiling observations

## Environment API
- reset() -> initial observation
- step(action) -> observation, reward, done, info
- state() -> current internal state snapshot

## Action Space
Primary operations:
- inspect_schema
- profile_column
- clean_missing
- deduplicate
- cast_type
- normalize_categories
- cap_outliers
- validate_constraints
- submit

Action schema is defined in env/models.py.

## Observation Space
Each observation contains:
- dataset_id
- task_id
- schema_summary
- quality_report
- validation_passed
- action_history
- step_budget_remaining

Observation schema is defined in env/models.py.

## Reward Design
Reward combines:
- quality improvement delta
- efficiency penalty for late-stage over-steps
- safety penalties for repeated and invalid actions
- terminal bonus/penalty on submit based on validation status

Reward schema and logic:
- env/models.py
- env/rewards.py

## Standout Feature: Governance and Audit Intelligence
This project includes an industry-style governance layer for trust, QA, and compliance workflows:
- per-step risk scoring with risk levels (low/medium/high)
- risk flags for invalid actions, repeated actions, late no-progress behavior, and unsafe submit patterns
- actionable recommendations at each step
- full run report export with telemetry, action counts, reward history, quality trajectory, and governance summary

Core files:
- env/governance.py
- env/environment.py (generate_run_report)
- app.py (/report endpoint)

## Premium Feature: Leaderboard and CI Evaluator
This project now includes a leaderboard-ready evaluator schema with automatic pass/fail gates.

What it does:
- evaluates each run against threshold gates (score, risk, invalid actions, quality reduction)
- emits a strict decision: approved or rejected
- produces a stable leaderboard record payload for tracking and ranking
- supports custom threshold overrides for stricter CI policies

Core files:
- env/evaluator.py
- env/environment.py (evaluate_run)
- app.py (/evaluate endpoint)

## Task Suite
- easy_missing_and_dupes (easy)
- medium_type_and_category (medium)
- hard_conflicts_and_budget (hard)

Task registry: env/tasks.py

## Deterministic Grading
Each task is graded from 0.0 to 1.0 using:
- distance to target quality constraints
- validation success
- budget efficiency

Grader: env/graders.py

### Task Descriptions
- easy_missing_and_dupes:
	- objective: eliminate missing values and duplicates, then validate and submit.
	- challenge profile: straightforward quality defects and larger step budget.
- medium_type_and_category:
	- objective: handle missingness, type casting, category normalization, and outlier capping.
	- challenge profile: multi-issue triage requiring ordered operations.
- hard_conflicts_and_budget:
	- objective: maximize quality gains under strict step budget with non-zero target tolerances.
	- challenge profile: constrained planning with tradeoffs.

## Baseline Runtime
Use the required `inference.py` script for baseline/runtime checks.

## Quick Start
```bash
pip install -r requirements.txt
openenv validate
python inference.py
```

## OpenAI Baseline Mode
`inference.py` uses the OpenAI client with these variables:

- API_BASE_URL
- MODEL_NAME
- HF_TOKEN

Optional environment variable:
- API_KEY (fallback if HF_TOKEN is not set)

Defaults:
- API_BASE_URL: https://router.huggingface.co/v1
- MODEL_NAME: Qwen/Qwen2.5-72B-Instruct

## Docker
```bash
docker build -t data-quality-openenv .
docker run --rm -p 7860:7860 data-quality-openenv
```

## Hugging Face Space Deployment
1. Create a new Hugging Face Space with Docker SDK.
2. Push this repository content to the Space.
3. Ensure README front matter includes sdk: docker and app_port: 7860.
4. Add Space topic/tag openenv.
5. Set HF_TOKEN in Space secrets for inference runtime.

## API Endpoints
- GET /health
- POST /reset
- POST /step
- GET /state
- GET /report
- POST /evaluate

## Validation Note
```bash
openenv validate
```

For inference runtime validation:

```bash
python inference.py
```
