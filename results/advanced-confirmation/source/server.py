"""Local-only dashboard API. Jobs are serialized to preserve RNG determinism."""

import json
import os
import re
import threading
import uuid
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .config import Config
from .fdm import solve
from .physics import truth_parameters

ROOT = Path(__file__).resolve().parents[1]
app = FastAPI(title="PINN-CANON local laboratory", version="0.2.0")
jobs = {}
job_lock = threading.Lock()


class SimulationRequest(BaseModel):
    model_config = {"extra": "forbid"}
    scenario: Literal["uniform", "local_loss", "variable_alpha", "temperature_alpha"] = "uniform"
    alpha: float = Field(1e-4, ge=1e-6, le=1e-3)
    beta: float = Field(0.01, ge=1e-5, le=0.1)
    amplitude: float = Field(60, ge=10, le=70)
    off: float = Field(230, ge=30, le=380)


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "provenance": "synthetic",
        "version": "0.2.0",
        "read_only": os.environ.get("CANON_READ_ONLY") == "1",
    }


def completed_results():
    paths = sorted((ROOT / "results").glob("*/results.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    complete = []
    for path in paths:
        try:
            content = json.loads(path.read_text())
            if content.get("schema_version", 1) >= 2 and not (path.parent / "COMPLETE.json").exists():
                continue
            complete.append(path)
        except (OSError, json.JSONDecodeError):
            continue
    return complete


def result_path(run: str | None = None):
    if run is not None:
        if not re.fullmatch(r"[A-Za-z0-9_-]+", run):
            raise HTTPException(422, "Invalid experiment identifier")
        path = ROOT / "results" / run / "results.json"
        if path not in completed_results():
            raise HTTPException(404, "Experiment unavailable")
        return path
    paths = completed_results()
    if not paths:
        raise HTTPException(404, "No benchmark yet. Run an experiment first.")
    return paths[0]


@app.get("/api/experiments")
def experiments():
    entries = []
    for path in completed_results():
        try:
            result = json.loads(path.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        entries.append(
            {
                "id": path.parent.name,
                "scenario": result["config"]["scenario"],
                "seeds": len(result["config"]["seeds"]),
                "edition": "advanced" if result["config"].get("boundary_mode") == "hard" else "original",
            }
        )
    return entries


@app.get("/api/results")
def results(run: str | None = None):
    path = result_path(run)
    result = json.loads(path.read_text())
    result["artifact_id"] = path.parent.name
    return result


@app.post("/api/simulate")
def simulate(request: SimulationRequest):
    try:
        cfg = Config(scenario=request.scenario, alpha=request.alpha, beta=request.beta)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    kind, raw = truth_parameters(cfg)
    x, t, T = solve(cfg, kind, raw, request.amplitude, request.off, nx=81)
    return dict(
        provenance="synthetic",
        solver="Conservative finite difference + BDF",
        x_m=x.tolist(),
        time_s=t.tolist(),
        temperature_C=T.tolist(),
    )


class JobRequest(BaseModel):
    model_config = {"extra": "forbid"}
    preset: Literal["demo", "advanced"] = "demo"


@app.post("/api/jobs", status_code=202)
def create_job(request: Request, body: JobRequest = JobRequest()):
    if os.environ.get("CANON_READ_ONLY") == "1":
        raise HTTPException(403, "Training is disabled in this read-only deployment")
    origin = request.headers.get("origin")
    if origin and origin.rstrip("/") != str(request.base_url).rstrip("/"):
        raise HTTPException(403, "Cross-origin training requests are not allowed")
    # Fixed, bounded interactive preset. Larger research budgets use the CLI.
    if not job_lock.acquire(blocking=False):
        raise HTTPException(409, "A benchmark is already running")
    job_id = uuid.uuid4().hex
    jobs[job_id] = {"id": job_id, "status": "running", "message": "Initialisation", "result": None}

    def work():
        try:
            from .experiment import run_experiment

            preset_path = "advanced-demo.json" if body.preset == "advanced" else "demo.json"
            cfg = Config.model_validate_json((ROOT / "configs" / preset_path).read_text())

            def progress(message):
                jobs[job_id]["message"] = message

            result = run_experiment(cfg, ROOT / "results" / f"web-{job_id}", progress)
            result["artifact_id"] = f"web-{job_id}"
            jobs[job_id].update(status="completed", message="Benchmark complete", result=result)
        except Exception as exc:
            jobs[job_id].update(status="failed", message=str(exc))
        finally:
            job_lock.release()

    threading.Thread(target=work, daemon=True).start()
    return {"id": job_id, "status": "running"}


@app.get("/api/jobs/{job_id}")
def job(job_id: str):
    if job_id not in jobs:
        raise HTTPException(404, "Unknown job")
    return jobs[job_id]


@app.get("/api/download/{name}")
def download(name: str, run: str | None = None):
    if name not in [
        "results.json",
        "metrics.csv",
        "benchmark.png",
        "benchmark.svg",
        "losses.png",
        "config.json",
        "fields.npz",
        "summary.json",
        "protocol.json",
        "artifacts.json",
        "comparison-summary.svg",
        "parameter-stability.svg",
        "training-diagnostics.png",
    ]:
        raise HTTPException(404, "Unknown artifact")
    path = result_path(run).parent / name
    if not path.exists():
        raise HTTPException(404, "Artifact unavailable")
    return FileResponse(path, filename=name)


app.mount("/", StaticFiles(directory=ROOT / "web", html=True), name="web")
