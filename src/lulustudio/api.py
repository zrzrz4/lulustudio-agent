from __future__ import annotations

from fastapi import FastAPI, HTTPException

from .config import Settings
from .database import Database
from .harness import AgentHarness
from .models import EpisodeSpec, FeedbackRequest


settings = Settings.from_env()
database = Database(settings.db_path)
harness = AgentHarness(settings, database)
app = FastAPI(title="LuluStudio Agent", version="0.1.0")


@app.get("/health")
def health() -> dict[str, object]:
    return {
        "status": "ok",
        "dry_run": settings.dry_run,
        "tools": harness.tools.names(),
        "comfyui_url": settings.comfyui_url,
    }


@app.post("/episodes", status_code=201)
def create_episode(spec: EpisodeSpec) -> dict:
    try:
        return harness.create_episode(spec)
    except Exception as exc:
        if "UNIQUE constraint" in str(exc):
            raise HTTPException(status_code=409, detail=f"episode already exists: {spec.episode_id}") from exc
        raise


@app.post("/episodes/{episode_id}/run")
def run_episode(episode_id: str) -> dict:
    try:
        return harness.run_episode(episode_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/episodes/{episode_id}")
def get_episode(episode_id: str) -> dict:
    result = database.get_episode(episode_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"episode not found: {episode_id}")
    return result


@app.post("/feedback", status_code=201)
def add_feedback(feedback: FeedbackRequest) -> dict[str, str]:
    database.add_feedback(feedback.model_dump(mode="json"))
    return {"status": "recorded"}


@app.get("/trajectories")
def export_trajectories() -> list[dict]:
    return database.export_trajectories()
