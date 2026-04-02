import os
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

REQUIRED_FILES = [
    "openenv.yaml",
    "README.md",
    "Dockerfile",
    "env/models.py",
    "env/environment.py",
    "env/tasks.py",
    "env/graders.py",
    "env/rewards.py",
    "scripts/run_baseline.py",
]


def main() -> int:
    missing = [path for path in REQUIRED_FILES if not os.path.exists(os.path.join(PROJECT_ROOT, path))]
    if missing:
        print("Validation failed. Missing required files:")
        for path in missing:
            print(f"- {path}")
        return 1

    print("Project structure validation passed.")
    print("Note: official openenv validate CLI is unavailable in this runtime.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
