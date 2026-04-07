# DataQA Bench Project Structure

## Overview
Professional Python project structure for the Data Quality Triage Assistant OpenEnv benchmark.

## Directory Organization

```
data-quality-triage-assistant/
├── env/                      # Core environment package
│   ├── __init__.py
│   ├── environment.py       # Main OpenEnv implementation
│   ├── models.py            # Pydantic models (Observation, Action, Reward)
│   ├── evaluator.py         # Episode evaluation and gate logic
│   ├── graders.py           # Task scoring and grading
│   ├── governance.py        # Risk assessment and governance
│   ├── rewards.py           # Step reward computation
│   ├── simulator.py         # Dataset loading and canonicalization
│   ├── tasks.py             # Task definitions and registry
│   └── fixtures/            # Test fixture datasets
│
├── tests/                   # Test suite (24+ test cases)
│   ├── test_api.py
│   ├── test_app.py
│   ├── test_evaluator.py
│   ├── test_governance.py
│   ├── test_graders.py
│   ├── test_determinism.py
│   ├── test_rewards.py
│   ├── test_reward_trajectory.py
│   └── test_tasks.py
│
├── scripts/                 # Utility and audit scripts
│   ├── audit_hf_space.py   # HF Space deployment audit
│   ├── audit_ui.py         # UI compliance audit
│   ├── audit_mcp_space.py  # MCP space audit
│   ├── client.py           # API client utilities
│   ├── evaluate_all.py     # Batch evaluation script
│   ├── run_baseline.py     # Baseline evaluation
│   ├── validate_project.py # Project validation
│   └── baseline_results.json
│
├── docs/                    # Documentation
│   └── VERIFICATION_REPORT.md
│
├── server/                  # Optional server components
│   ├── __init__.py
│   └── app.py
│
├── build/                   # Build artifacts
├── _hf_space_repo/          # HF Space deployment copy
│
├── Root Configuration Files
│   ├── app.py              # FastAPI main application
│   ├── inference.py        # Inference script (entry point)
│   ├── openenv.yaml        # OpenEnv specification
│   ├── pyproject.toml      # Project metadata
│   ├── requirements.txt    # Python dependencies
│   ├── Dockerfile          # Container definition
│   ├── .dockerignore
│   ├── .gitignore
│   ├── README.md           # Main documentation
│   └── dataqa_bench_ui_spec.html
```

## Key Files

- **app.py**: FastAPI web application serving the UI and API endpoints
- **inference.py**: LLM-based agent for automated data quality triage
- **openenv.yaml**: OpenEnv specification with task definitions
- **env/**: Core Python package containing the benchmark environment
- **tests/**: Comprehensive test suite (24 tests, 100% pass rate)

## Design Principles

1. **Modular**: Each component (evaluator, graders, rewards) is independent
2. **Tested**: Full test coverage with determinism and integration tests
3. **Real-world**: Uses real Hugging Face datasets (Titanic, Adult Census, Bank Marketing)
4. **Professional**: Standard Python project structure following PEP conventions

## Quality Metrics

- All task scores strictly bounded in (0, 1) open interval
- Per-step rewards normalized (max 1.5) for large datasets
- Docker build: Python 3.11.9-slim, pinned version
- 24/24 tests passing
- OpenEnv compliant: typed models, deterministic behavior

---

See [README.md](../README.md) for usage instructions.
