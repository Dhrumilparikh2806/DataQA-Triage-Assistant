import argparse
import json
import re
import urllib.error
import urllib.request
from typing import Any, Dict

from fastmcp import FastMCP

mcp = FastMCP("space-audit")


REQUIRED_SCREENS = [
    "screen-runner",
    "screen-dashboard",
    "screen-dataset",
    "screen-governance",
    "screen-leaderboard",
    "screen-report",
    "screen-api-settings",
    "screen-task-library",
]

REQUIRED_HOOKS = [
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


def _get(base_url: str, path: str) -> tuple[int, str, Dict[str, str]]:
    with urllib.request.urlopen(base_url + path, timeout=30) as resp:
        body = resp.read().decode("utf-8", "ignore")
        return getattr(resp, "status", 200), body, dict(resp.headers.items())


def _post(base_url: str, path: str, payload: Dict[str, Any]) -> tuple[int, Dict[str, Any]]:
    req = urllib.request.Request(
        base_url + path,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        body = resp.read().decode("utf-8", "ignore")
        return getattr(resp, "status", 200), json.loads(body)


@mcp.tool()
def audit_space(base_url: str) -> Dict[str, Any]:
    """Audit a deployed Space UI + API behavior and return a detailed report."""
    report: Dict[str, Any] = {
        "base_url": base_url,
        "routes": {},
        "headers": {},
        "ui": {},
        "api": {},
        "negative_cases": {},
    }

    for p in ["/", "/ui", "/health", "/state", "/report"]:
        try:
            code, body, _ = _get(base_url, p)
            report["routes"][p] = {"ok": True, "status": code, "bytes": len(body)}
        except Exception as exc:  # noqa: BLE001
            report["routes"][p] = {"ok": False, "error": str(exc)}

    try:
        _, html, hdr = _get(base_url, "/ui")
        report["headers"] = {
            "cache-control": hdr.get("cache-control") or hdr.get("Cache-Control"),
            "pragma": hdr.get("pragma") or hdr.get("Pragma"),
            "expires": hdr.get("expires") or hdr.get("Expires"),
        }

        onclick_calls = sorted(set(re.findall(r'onclick="([a-zA-Z_][a-zA-Z0-9_]*)\(', html)))
        defs = set(re.findall(r'function\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(', html))
        report["ui"] = {
            "onclick_calls": onclick_calls,
            "missing_onclick_definitions": sorted(set(onclick_calls) - defs),
            "required_screens_present": {k: (f'id="{k}"' in html) for k in REQUIRED_SCREENS},
            "required_hooks_present": {k: (k in html) for k in REQUIRED_HOOKS},
            "runner_default": ('id="screen-runner" class="screen active"' in html),
            "runner_nav_first": html.find("showScreen('runner')") < html.find("showScreen('dashboard')"),
        }
    except Exception as exc:  # noqa: BLE001
        report["ui"] = {"error": str(exc)}

    try:
        code, reset = _post(base_url, "/reset", {"task_id": "easy_missing_and_dupes"})
        report["api"]["reset"] = {
            "ok": code == 200 and reset.get("task_id") == "easy_missing_and_dupes",
            "status": code,
        }

        code, step = _post(
            base_url,
            "/step",
            {"operation": "clean_missing", "target_columns": ["amount"], "parameters": {}},
        )
        report["api"]["step"] = {
            "ok": code == 200,
            "status": code,
            "reward_has_total": "total" in step.get("reward", {}),
            "has_governance": "governance" in step.get("info", {}),
        }

        code, ev = _post(base_url, "/evaluate", {"thresholds": {}})
        report["api"]["evaluate"] = {
            "ok": code == 200 and "decision" in ev and "gates" in ev,
            "status": code,
            "decision": ev.get("decision"),
        }
    except Exception as exc:  # noqa: BLE001
        report["api"] = {"error": str(exc)}

    try:
        req = urllib.request.Request(
            base_url + "/step",
            data=json.dumps({"operation": "non_existing_op", "target_columns": [], "parameters": {}}).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        urllib.request.urlopen(req, timeout=30)
        report["negative_cases"]["invalid_operation"] = {
            "ok": False,
            "note": "unexpectedly accepted",
        }
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", "ignore")
        report["negative_cases"]["invalid_operation"] = {
            "ok": True,
            "status": exc.code,
            "contains_detail": ("Invalid action" in body or "detail" in body),
        }
    except Exception as exc:  # noqa: BLE001
        report["negative_cases"]["invalid_operation"] = {"ok": False, "error": str(exc)}

    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="MCP Space audit server and CLI checker")
    parser.add_argument("--check", help="Run one audit against the given base URL and print JSON")
    args = parser.parse_args()

    if args.check:
        print(json.dumps(audit_space(args.check.rstrip("/")), indent=2))
        return

    mcp.run()


if __name__ == "__main__":
    main()
