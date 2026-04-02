---
title: Data Quality Triage Assistant
emoji: "📊"
colorFrom: blue
colorTo: green
sdk: docker
app_port: 7860
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
- baseline runner and test suite

Planned next:
- full OpenEnv validator integration
- Hugging Face Space deployment wiring

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

Example CI usage:
```bash
python scripts/evaluate_all.py
```

The output includes per-policy evaluation decisions and failed gate names.

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

## Baseline Scores (Current Scripted Baseline)
- easy_missing_and_dupes: 0.2444444444
- medium_type_and_category: 0.3259740260
- hard_conflicts_and_budget: 0.2037931034
- aggregate_score: 0.2580705246

Scores source: scripts/baseline_results.json

## Quick Start
```bash
pip install -r requirements.txt
pytest -q
python scripts/run_baseline.py
python scripts/validate_project.py
```

## OpenAI Baseline Mode
If OPENAI_API_KEY is set, scripts/run_baseline.py runs an OpenAI model policy.

Optional environment variable:
- OPENAI_MODEL (default: gpt-4.1-mini)

Without OPENAI_API_KEY, the script uses a deterministic scripted baseline.

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
5. Set OPENAI_API_KEY in Space secrets if running LLM baseline mode.

## Evaluation Utilities
```bash
python scripts/evaluate_all.py
```

This compares good and bad trajectories and stores results in scripts/trajectory_eval_results.json.

## API Endpoints
- GET /health
- POST /reset
- POST /step
- GET /state
- GET /report
- POST /evaluate

## Validation Note
Local tests pass, but OpenEnv CLI validation currently depends on the correct validator binary/package for this runtime. Once the exact CLI distribution is finalized, run:

```bash
openenv validate
```

Until then, run the local project structure validator:

```bash
python scripts/validate_project.py
```
