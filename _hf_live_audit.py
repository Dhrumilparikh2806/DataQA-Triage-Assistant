import json
import re
import urllib.request
import urllib.error

BASE = "https://dhrumilparikh-openenv-data-analysis-environment.hf.space"


def get(path: str):
    with urllib.request.urlopen(BASE + path, timeout=30) as resp:
        body = resp.read().decode("utf-8", "ignore")
        return getattr(resp, "status", 200), body, dict(resp.headers.items())


def post(path: str, payload: dict):
    req = urllib.request.Request(
        BASE + path,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        body = resp.read().decode("utf-8", "ignore")
        return getattr(resp, "status", 200), json.loads(body)


def safe_get(path: str):
    try:
        code, body, _ = get(path)
        return {"ok": True, "status": code, "len": len(body)}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


report = {
    "base": BASE,
    "routes": {},
    "headers": {},
    "ui": {},
    "api": {},
    "per_task": {},
    "negative_cases": {},
}

# Routes + headers
for p in ["/", "/ui", "/health", "/state", "/report"]:
    report["routes"][p] = safe_get(p)

try:
    _, _, hdr = get("/ui")
    report["headers"] = {
        "cache-control": hdr.get("Cache-Control"),
        "pragma": hdr.get("Pragma"),
        "expires": hdr.get("Expires"),
    }
except Exception as exc:
    report["headers"] = {"error": str(exc)}

# UI source checks
try:
    _, html, _ = get("/ui")
    onclick_calls = sorted(set(re.findall(r'onclick="([a-zA-Z_][a-zA-Z0-9_]*)\(', html)))
    defs = set(re.findall(r'function\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(', html))
    required_screens = [
        "screen-runner",
        "screen-dashboard",
        "screen-dataset",
        "screen-governance",
        "screen-leaderboard",
        "screen-report",
        "screen-api-settings",
        "screen-task-library",
    ]
    required_hooks = [
        "startNewRun",
        "runAction",
        "downloadRunReport",
        "exportPdf",
        "showScreen",
        "selectTask",
        "selectTaskById",
        "runner-step-log",
        "governance-ci-gates",
        "leaderboard-list",
        "recent-runs-list",
    ]
    report["ui"] = {
        "onclick_calls": onclick_calls,
        "missing_onclick_definitions": sorted(set(onclick_calls) - defs),
        "required_screens_present": {k: (f'id=\"{k}\"' in html) for k in required_screens},
        "required_hooks_present": {k: (k in html) for k in required_hooks},
        "runner_is_default": ('id="screen-runner" class="screen active"' in html),
        "nav_order_runner_first": html.find("showScreen('runner')") < html.find("showScreen('dashboard')"),
    }
except Exception as exc:
    report["ui"] = {"error": str(exc)}

# Core API smoke
try:
    code, payload = post("/reset", {"task_id": "easy_missing_and_dupes"})
    report["api"]["reset"] = {
        "status": code,
        "task_id": payload.get("task_id"),
        "has_quality_report": "quality_report" in payload,
    }

    code, payload = post(
        "/step",
        {"operation": "clean_missing", "target_columns": ["amount"], "parameters": {}},
    )
    report["api"]["step"] = {
        "status": code,
        "has_observation": "observation" in payload,
        "has_reward": "reward" in payload,
        "reward_has_total": "total" in payload.get("reward", {}),
        "has_governance": "governance" in payload.get("info", {}),
    }

    code, payload = post("/evaluate", {"thresholds": {}})
    report["api"]["evaluate"] = {
        "status": code,
        "decision": payload.get("decision"),
        "has_gates": isinstance(payload.get("gates"), list),
    }
except Exception as exc:
    report["api"] = {"error": str(exc)}

# Per-task execution checks
TASKS = [
    "easy_missing_and_dupes",
    "medium_type_and_category",
    "hard_conflicts_and_budget",
]

OPS = [
    ("inspect_schema", []),
    ("clean_missing", ["amount"]),
    ("deduplicate", []),
    ("cast_type", ["amount"]),
    ("normalize_categories", ["region"]),
    ("cap_outliers", ["amount"]),
    ("validate_constraints", []),
    ("submit", []),
]

for task in TASKS:
    task_out = {
        "reset_ok": False,
        "steps_attempted": 0,
        "done_seen": False,
        "report_ok": False,
        "evaluate_ok": False,
        "decision": None,
        "error": None,
    }
    try:
        _, reset = post("/reset", {"task_id": task})
        task_out["reset_ok"] = reset.get("task_id") == task

        for op, cols in OPS:
            _, st = post(
                "/step",
                {"operation": op, "target_columns": cols, "parameters": {}},
            )
            task_out["steps_attempted"] += 1
            if st.get("done"):
                task_out["done_seen"] = True
                break

        code, _, _ = get("/report")
        task_out["report_ok"] = code == 200

        _, ev = post("/evaluate", {"thresholds": {}})
        task_out["evaluate_ok"] = ("decision" in ev and "gates" in ev)
        task_out["decision"] = ev.get("decision")
    except Exception as exc:
        task_out["error"] = str(exc)

    report["per_task"][task] = task_out

# Negative path checks
try:
    req = urllib.request.Request(
        BASE + "/step",
        data=json.dumps({"operation": "non_existing_op", "target_columns": [], "parameters": {}}).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    urllib.request.urlopen(req, timeout=30)
    report["negative_cases"]["invalid_operation"] = {"ok": False, "note": "unexpectedly accepted"}
except urllib.error.HTTPError as exc:
    body = exc.read().decode("utf-8", "ignore")
    report["negative_cases"]["invalid_operation"] = {
        "ok": True,
        "status": exc.code,
        "contains_invalid": ("Invalid action" in body or "detail" in body),
    }
except Exception as exc:
    report["negative_cases"]["invalid_operation"] = {"ok": False, "error": str(exc)}

print(json.dumps(report, indent=2))
