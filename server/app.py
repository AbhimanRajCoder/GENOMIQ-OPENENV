"""
GenomIQ — FastAPI server.

Exposes the RL environment over HTTP on port 7860.

Endpoints:
    POST /reset      — Reset environment (optionally switch task)
    POST /step       — Take one action
    GET  /state      — Get full internal state
    POST /set_task   — Switch the active task
    GET  /health     — Health-check
    GET  /tasks      — List all available tasks
"""

from contextlib import asynccontextmanager
from typing import AsyncIterator

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from env.environment import GenomIQEnv
from env.models import Action
from env.tasks import TASKS


# ── Environment instances ─────────────────────────────────────────────────────

envs: dict[str, GenomIQEnv] = {}
current_task: str = "single_regulator"


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncIterator[None]:
    """Initialize one environment instance per task on startup."""
    global envs
    for task_name in TASKS:
        envs[task_name] = GenomIQEnv(config_path="config.yaml", task_name=task_name)
    yield
    envs.clear()


app = FastAPI(
    title="GenomIQ",
    description="Scientific Discovery RL Environment",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request / response schemas ────────────────────────────────────────────────


class ResetRequest(BaseModel):
    task_name: str | None = None
    domain: str | None = None
    objective: str | None = None
    dataset_source: str | None = None
    noise_level: float | None = None
    seed_genes: list[str] | None = None


class StepRequest(BaseModel):
    action_type: int


class SetTaskRequest(BaseModel):
    task_name: str


# ── Endpoints ─────────────────────────────────────────────────────────────────


@app.post("/reset")
async def reset_env(body: ResetRequest | None = None):
    """Reset the environment. Optionally set the active task and runtime overrides."""
    global current_task
    if body and body.task_name:
        if body.task_name not in TASKS:
            raise HTTPException(status_code=422, detail=f"Unknown task: {body.task_name}")
        current_task = body.task_name

    env = envs[current_task]

    # Apply runtime overrides from the request
    if body:
        if body.domain:
            env.config["scenario"]["domain"] = body.domain
            env.domain = body.domain
        if body.objective:
            env.config["scenario"]["objective"] = body.objective
            env.objective = body.objective
        if body.dataset_source:
            env.config.setdefault("dataset", {})["source"] = body.dataset_source
        if body.noise_level is not None:
            env.config.setdefault("constraints", {})["noise_level"] = body.noise_level
            env.noise_sigma = body.noise_level
        if body.seed_genes is not None:
            env.config.setdefault("prior_knowledge", {})["seed_genes"] = body.seed_genes
            env.seed_genes = body.seed_genes

    result = await env.reset()
    return result


@app.post("/step")
async def step_env(body: StepRequest):
    """Take one step in the current environment."""
    if body.action_type < 0 or body.action_type > 5:
        raise HTTPException(
            status_code=422,
            detail=f"action_type must be 0–5, got {body.action_type}",
        )
    action = Action(action_type=body.action_type)
    result = await envs[current_task].step(action)
    return result


@app.get("/state")
async def get_state():
    """Return the full internal state of the current environment."""
    return await envs[current_task].state()


@app.post("/set_task")
async def set_task(body: SetTaskRequest):
    """Switch the active task."""
    global current_task
    if body.task_name not in TASKS:
        raise HTTPException(status_code=422, detail=f"Unknown task: {body.task_name}")
    current_task = body.task_name
    return {"task": current_task, "status": "ok"}


@app.get("/health")
async def health_check():
    """Health-check endpoint."""
    return {"status": "ok", "current_task": current_task}


@app.get("/tasks")
async def list_tasks():
    """List all available tasks with metadata."""
    return [
        {
            "name": t.name,
            "description": t.description,
            "difficulty": t.difficulty,
            "max_steps": t.max_steps,
        }
        for t in TASKS.values()
    ]


@app.get("/info")
async def info():
    """Return environment metadata for openenv validation."""
    return {
        "name": "genomiq",
        "domain": "gene_expression",
        "version": "1.0.0",
        "tasks": list(TASKS.keys()),
    }


# ── Entrypoint ────────────────────────────────────────────────────────────────


def main() -> None:
    """Run the server — used by pyproject.toml [project.scripts] entry point."""
    uvicorn.run("server.app:app", host="0.0.0.0", port=7860, reload=False)


if __name__ == "__main__":
    main()
