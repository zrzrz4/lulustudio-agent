from __future__ import annotations

import hashlib
from pathlib import Path

from ..models import Defect, DefectType, ToolResult
from .base import Tool, ToolContext


class MockProductionTool(Tool):
    """Deterministic dry-run backend used to test persistence and recovery."""

    name = "production"

    def __init__(self, artifact_root: Path):
        self.artifact_root = artifact_root

    def run(self, context: ToolContext) -> ToolResult:
        shot = context.shot
        digest = hashlib.sha256(f"{shot.shot_id}:{context.attempt_no}:{context.action}".encode()).hexdigest()[:12]
        target = self.artifact_root / context.episode_id / shot.shot_id
        target.mkdir(parents=True, exist_ok=True)
        manifest = target / f"attempt-{context.attempt_no}-{digest}.json"
        manifest.write_text(shot.model_dump_json(indent=2), encoding="utf-8")

        defects: list[Defect] = []
        if context.attempt_no == 1 and shot.duration_ms >= 7000:
            defects.append(Defect(type=DefectType.CHARACTER_DRIFT, severity="high"))
        if context.attempt_no == 1 and len(shot.character_instances) >= 2:
            defects.append(Defect(type=DefectType.EXTRA_SUBJECT, severity="high"))

        return ToolResult(
            success=not defects,
            artifacts={"manifest": str(manifest)},
            metrics={
                "identity_consistency": 0.72 if defects else 0.91,
                "instance_count_accuracy": 0.5 if any(d.type == DefectType.EXTRA_SUBJECT for d in defects) else 1.0,
            },
            defects=defects,
            cost=0.25,
            latency_sec=0.01,
            metadata={"backend": "mock", "digest": digest},
        )
