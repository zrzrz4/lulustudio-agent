from __future__ import annotations

import uuid
from typing import Any

from .config import Settings
from .database import Database
from .models import EpisodeSpec, RecoveryAction, RunStatus, ShotSpec, ToolResult
from .recovery import RecoveryPlanner
from .tools import ComfyUITool, MockProductionTool, ToolContext, ToolRegistry


class AgentHarness:
    def __init__(self, settings: Settings, db: Database | None = None):
        self.settings = settings
        self.db = db or Database(settings.db_path)
        self.db.init_schema()
        self.tools = ToolRegistry()
        if settings.dry_run:
            self.tools.register(MockProductionTool(settings.artifact_root))
        else:
            self.tools.register(ComfyUITool(settings.comfyui_url))
        self.recovery = RecoveryPlanner()

    def create_episode(self, spec: EpisodeSpec) -> dict[str, Any]:
        self.db.create_episode(spec)
        episode = self.db.get_episode(spec.episode_id)
        assert episode is not None
        return episode

    def run_episode(self, episode_id: str) -> dict[str, Any]:
        episode = self.db.get_episode(episode_id)
        if episode is None:
            raise KeyError(f"episode not found: {episode_id}")
        self.db.mark_episode(episode_id, RunStatus.RUNNING)

        for row in self.db.pending_shots(episode_id):
            if not self._has_budget(episode_id):
                self.db.mark_episode(episode_id, RunStatus.FAILED)
                break
            status = self.run_shot(episode_id, ShotSpec.model_validate(row["spec"]))
            if status == RunStatus.WAITING_HUMAN:
                self.db.mark_episode(episode_id, RunStatus.WAITING_HUMAN)
                break

        final = self.db.get_episode(episode_id)
        assert final is not None
        statuses = {item["status"] for item in final["shots"]}
        if statuses == {RunStatus.SUCCEEDED}:
            self.db.mark_episode(episode_id, RunStatus.SUCCEEDED)
        elif RunStatus.WAITING_HUMAN not in statuses and not self._has_budget(episode_id):
            self.db.mark_episode(episode_id, RunStatus.FAILED)
        result = self.db.get_episode(episode_id)
        assert result is not None
        return result

    def run_shot(self, episode_id: str, shot: ShotSpec) -> RunStatus:
        attempts = self.db.attempts_for_shot(shot.shot_id)
        previous_actions = [item["action"] for item in attempts if item.get("action")]
        action: RecoveryAction | None = None
        if attempts:
            previous_result = ToolResult.model_validate(attempts[-1]["output"])
            action = self.recovery.choose(previous_result.defects, len(attempts), previous_actions)

        while len(attempts) < self.settings.max_attempts:
            if action == RecoveryAction.HUMAN_REVIEW:
                self.db.mark_shot(episode_id, shot.shot_id, RunStatus.WAITING_HUMAN)
                return RunStatus.WAITING_HUMAN
            attempt_no = len(attempts) + 1
            result = self.tools.get("production").run(
                ToolContext(
                    episode_id=episode_id,
                    shot=shot,
                    attempt_no=attempt_no,
                    action=action.value if action else None,
                    state={"previous_attempts": len(attempts)},
                )
            )
            attempt_id = str(uuid.uuid4())
            status = RunStatus.SUCCEEDED if result.success and not result.defects else RunStatus.RUNNING
            self.db.record_attempt(
                attempt_id=attempt_id,
                episode_id=episode_id,
                shot_id=shot.shot_id,
                attempt_no=attempt_no,
                action=action.value if action else None,
                input_data=shot.model_dump(mode="json"),
                output_data=result.model_dump(mode="json"),
                status=status,
                cost=result.cost,
            )
            if status == RunStatus.SUCCEEDED:
                self.db.mark_shot(episode_id, shot.shot_id, status, attempt_id)
                return status
            if not self._has_budget(episode_id):
                self.db.mark_shot(episode_id, shot.shot_id, RunStatus.FAILED)
                return RunStatus.FAILED
            attempts = self.db.attempts_for_shot(shot.shot_id)
            previous_actions = [item["action"] for item in attempts if item.get("action")]
            action = self.recovery.choose(result.defects, attempt_no, previous_actions)

        self.db.mark_shot(episode_id, shot.shot_id, RunStatus.WAITING_HUMAN)
        return RunStatus.WAITING_HUMAN

    def _has_budget(self, episode_id: str) -> bool:
        episode = self.db.get_episode(episode_id)
        if episode is None:
            return False
        return float(episode["budget_spent"]) < float(episode["budget_total"])
