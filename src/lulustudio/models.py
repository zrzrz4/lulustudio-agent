from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, model_validator


class RunStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    WAITING_HUMAN = "waiting_human"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class DefectType(StrEnum):
    CHARACTER_DRIFT = "character_drift"
    FUR_DETAIL_LOSS = "fur_detail_loss"
    EXTRA_SUBJECT = "extra_subject"
    INSTANCE_BINDING = "instance_binding_error"
    DURATION_MISMATCH = "duration_mismatch"
    VOICE_IDENTITY = "voice_identity_mismatch"
    EMOTION_MISMATCH = "emotion_mismatch"
    TOOL_ERROR = "tool_error"


class RecoveryAction(StrEnum):
    RETRY_SAME = "retry_same"
    REWRITE_PROMPT = "rewrite_prompt"
    REUSE_LAST_FRAME = "reuse_last_accepted_frame"
    SPLIT_SHOT = "split_shot"
    REDUCE_MOTION = "reduce_motion_complexity"
    REGION_CONDITIONING = "apply_region_conditioning"
    SPLIT_LAYERS = "split_character_layers"
    ADJUST_VOICE_SPEED = "adjust_voice_speed"
    SPLIT_DIALOGUE = "split_dialogue"
    HUMAN_REVIEW = "human_review"


class CharacterInstance(BaseModel):
    instance_id: str
    identity_id: str
    region: str | None = None
    action: str | None = None
    reference_asset_id: str | None = None


class DialogueSpec(BaseModel):
    text: str
    speaker_instance_id: str
    voice_id: str
    emotion: str = "neutral"
    target_duration_ms: int | None = Field(default=None, gt=0)


class ShotSpec(BaseModel):
    shot_id: str
    scene_id: str
    prompt: str
    duration_ms: int = Field(gt=0)
    character_instances: list[CharacterInstance] = Field(default_factory=list)
    dialogue: list[DialogueSpec] = Field(default_factory=list)
    expected_instance_count: int | None = Field(default=None, ge=0)
    forbid_extra_subjects: bool = True
    workflow_path: str | None = None
    parameters: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_dialogue_speakers(self) -> "ShotSpec":
        instance_ids = {item.instance_id for item in self.character_instances}
        invalid = {item.speaker_instance_id for item in self.dialogue} - instance_ids
        if invalid:
            raise ValueError(f"dialogue references unknown character instances: {sorted(invalid)}")
        return self


class EpisodeSpec(BaseModel):
    episode_id: str
    title: str
    shots: list[ShotSpec]
    budget: float = Field(default=20.0, gt=0)

    @model_validator(mode="after")
    def unique_shot_ids(self) -> "EpisodeSpec":
        ids = [shot.shot_id for shot in self.shots]
        if len(ids) != len(set(ids)):
            raise ValueError("shot_id must be unique within an episode")
        return self


class Defect(BaseModel):
    type: DefectType
    severity: str = "medium"
    confidence: float = Field(default=1.0, ge=0, le=1)
    evidence: dict[str, Any] = Field(default_factory=dict)


class ToolResult(BaseModel):
    success: bool
    artifacts: dict[str, str] = Field(default_factory=dict)
    metrics: dict[str, float] = Field(default_factory=dict)
    defects: list[Defect] = Field(default_factory=list)
    cost: float = Field(default=0.0, ge=0)
    latency_sec: float = Field(default=0.0, ge=0)
    metadata: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None


class FeedbackRequest(BaseModel):
    attempt_id: str
    accepted: bool
    reasons: list[str] = Field(default_factory=list)
    preferred_over_attempt_id: str | None = None
