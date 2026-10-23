from pathlib import Path

from lulustudio.config import Settings
from lulustudio.database import Database
from lulustudio.harness import AgentHarness
from lulustudio.models import CharacterInstance, EpisodeSpec, RunStatus, ShotSpec


def make_settings(tmp_path: Path) -> Settings:
    return Settings(
        db_path=tmp_path / "test.db",
        artifact_root=tmp_path / "artifacts",
        comfyui_url="http://127.0.0.1:6006",
        dry_run=True,
        max_attempts=4,
        default_budget=20,
    )


def test_recovery_and_checkpoint(tmp_path: Path) -> None:
    settings = make_settings(tmp_path)
    harness = AgentHarness(settings)
    spec = EpisodeSpec(
        episode_id="ep-test",
        title="test",
        budget=3,
        shots=[
            ShotSpec(
                shot_id="shot-1",
                scene_id="scene-1",
                prompt="two characters",
                duration_ms=8000,
                character_instances=[
                    CharacterInstance(instance_id="lulu-left", identity_id="lulu"),
                    CharacterInstance(instance_id="lumei-right", identity_id="lumei"),
                ],
                expected_instance_count=2,
            )
        ],
    )
    harness.create_episode(spec)
    result = harness.run_episode(spec.episode_id)

    assert result["status"] == RunStatus.SUCCEEDED
    attempts = Database(settings.db_path).attempts_for_shot("shot-1")
    assert len(attempts) == 2
    assert attempts[1]["action"] == "apply_region_conditioning"

    resumed = harness.run_episode(spec.episode_id)
    assert resumed["status"] == RunStatus.SUCCEEDED
    assert len(Database(settings.db_path).attempts_for_shot("shot-1")) == 2


def test_budget_stops_run(tmp_path: Path) -> None:
    settings = make_settings(tmp_path)
    harness = AgentHarness(settings)
    spec = EpisodeSpec(
        episode_id="ep-budget",
        title="budget",
        budget=0.1,
        shots=[ShotSpec(shot_id="shot-budget", scene_id="scene", prompt="long", duration_ms=8000)],
    )
    harness.create_episode(spec)
    result = harness.run_episode(spec.episode_id)
    assert result["status"] == RunStatus.FAILED
