from pathlib import Path
from typing import Any, Dict

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, RedirectResponse
from pydantic import BaseModel, Field

from env.environment import DataQualityTriageEnv
from env.graders import GRADERS
from env.models import Action

app = FastAPI(title="Data Quality Triage Assistant - #TEAM Hack-with-Pals", version="0.1.0")
UI_FILE = Path(__file__).resolve().parent / "dataqa_bench_ui_spec.html"

_env = DataQualityTriageEnv(task_id="easy_missing_and_dupes")
_env.reset()


class ResetRequest(BaseModel):
    task_id: str | None = None
    task: str | None = None
    task_name: str | None = None


class StepRequest(BaseModel):
    operation: str
    target_columns: list[str] = Field(default_factory=list)
    parameters: Dict[str, Any] = Field(default_factory=dict)


class EvaluateRequest(BaseModel):
    thresholds: Dict[str, float] = Field(default_factory=dict)


def _ensure_env_ready() -> None:
    try:
        _env.state()
    except RuntimeError:
        _env.reset()


def _resolve_task_id(req: ResetRequest | None) -> str:
    if req is None:
        return "easy_missing_and_dupes"
    for candidate in (req.task_id, req.task, req.task_name):
        if candidate:
            return candidate
    return "easy_missing_and_dupes"


@app.get("/")
def root() -> RedirectResponse:
    version = int(UI_FILE.stat().st_mtime) if UI_FILE.exists() else 0
    return RedirectResponse(url=f"/ui?v={version}")


@app.get("/web")
def web_root() -> RedirectResponse:
    version = int(UI_FILE.stat().st_mtime) if UI_FILE.exists() else 0
    return RedirectResponse(url=f"/ui?v={version}")


@app.get("/web/")
def web_root_slash() -> RedirectResponse:
    version = int(UI_FILE.stat().st_mtime) if UI_FILE.exists() else 0
    return RedirectResponse(url=f"/ui?v={version}")


@app.get("/ui")
def ui() -> FileResponse:
    if not UI_FILE.exists():
        raise HTTPException(status_code=404, detail="UI file not found")
    return FileResponse(
        UI_FILE,
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache",
            "Expires": "0",
        },
    )

@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "healthy"}


@app.get("/tasks")
def tasks() -> Dict[str, Any]:
    catalog = DataQualityTriageEnv.task_catalog()
    grader_registry = DataQualityTriageEnv.task_grader_registry()
    return {
        "task_count": len(catalog),
        "tasks": catalog,
        "task_graders": grader_registry,
        "graders": grader_registry,
        "grader_count": len(grader_registry),
    }


@app.get("/metadata")
def metadata() -> Dict[str, Any]:
    catalog = DataQualityTriageEnv.task_catalog()
    grader_registry = DataQualityTriageEnv.task_grader_registry()
    return {
        "name": "data-quality-triage-assistant",
        "description": "Data Quality Triage Assistant OpenEnv - Made by #TEAM Hack-with-Pals",
        "default_task": "easy_missing_and_dupes",
        "task_count": len(catalog),
        "tasks": catalog,
        "task_graders": grader_registry,
        "graders": grader_registry,
        "grader_count": len(grader_registry),
        "grader_names": sorted(GRADERS.keys()),
    }


@app.get("/schema")
def schema() -> Dict[str, Any]:
    return {
        "action": {
            "type": "object",
            "properties": {
                "operation": {"type": "string"},
                "target_columns": {"type": "array", "items": {"type": "string"}},
                "parameters": {"type": "object"},
            },
        },
        "observation": {
            "type": "object",
            "properties": {
                "dataset_id": {"type": "string"},
                "task_id": {"type": "string"},
                "quality_report": {"type": "object"},
                "validation_passed": {"type": "boolean"},
                "step_budget_remaining": {"type": "integer"},
            },
        },
        "state": {
            "type": "object",
            "properties": {
                "dataset_id": {"type": "string"},
                "task_id": {"type": "string"},
                "step_count": {"type": "integer"},
                "step_budget": {"type": "integer"},
            },
        },
    }


@app.post("/mcp")
def mcp() -> Dict[str, Any]:
    return {"jsonrpc": "2.0", "result": {"status": "ok"}, "id": None}


@app.post("/reset")
def reset(req: ResetRequest | None = None) -> Dict[str, Any]:
    global _env
    task_id = _resolve_task_id(req)
    _env = DataQualityTriageEnv(task_id=task_id)
    obs = _env.reset()
    return obs.model_dump()


@app.post("/step")
def step(req: StepRequest) -> Dict[str, Any]:
    _ensure_env_ready()
    try:
        action = Action(
            operation=req.operation,
            target_columns=req.target_columns,
            parameters=req.parameters,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid action: {exc}") from exc

    try:
        obs, reward, done, info = _env.step(action)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {
        "observation": obs.model_dump(),
        "reward": reward.model_dump(),
        "done": done,
        "info": info,
    }


@app.get("/state")
def state() -> Dict[str, Any]:
    _ensure_env_ready()
    try:
        return _env.state()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/report")
def report() -> Dict[str, Any]:
    _ensure_env_ready()
    try:
        return _env.generate_run_report()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/evaluate")
def evaluate(req: EvaluateRequest) -> Dict[str, Any]:
    _ensure_env_ready()
    try:
        return _env.evaluate_run(thresholds=req.thresholds)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
