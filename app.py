from pathlib import Path
from typing import Any, Dict

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, RedirectResponse
from pydantic import BaseModel, Field

from env.environment import DataQualityTriageEnv
from env.models import Action

app = FastAPI(title="Data Quality Triage Assistant - #TEAM Hack-with-Pals", version="0.1.0")
UI_FILE = Path(__file__).resolve().parent / "dataqa_bench_ui_spec.html"

_env = DataQualityTriageEnv(task_id="easy_missing_and_dupes")
_env.reset()


class ResetRequest(BaseModel):
    task_id: str = "easy_missing_and_dupes"


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
    return {"status": "ok"}


@app.post("/reset")
def reset(req: ResetRequest) -> Dict[str, Any]:
    global _env
    _env = DataQualityTriageEnv(task_id=req.task_id)
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
