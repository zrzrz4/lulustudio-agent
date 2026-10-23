from __future__ import annotations

from collections import Counter

from .models import Defect, DefectType, RecoveryAction


class RecoveryPlanner:
    """Bounded recovery policy. It returns executable actions, not free-form advice."""

    def choose(self, defects: list[Defect], attempt_no: int, previous_actions: list[str]) -> RecoveryAction:
        if not defects:
            return RecoveryAction.RETRY_SAME
        if attempt_no >= 4:
            return RecoveryAction.HUMAN_REVIEW

        types = {item.type for item in defects}
        counts = Counter(previous_actions)

        if DefectType.EXTRA_SUBJECT in types or DefectType.INSTANCE_BINDING in types:
            if counts[RecoveryAction.REGION_CONDITIONING] == 0:
                return RecoveryAction.REGION_CONDITIONING
            return RecoveryAction.SPLIT_LAYERS
        if DefectType.CHARACTER_DRIFT in types:
            if counts[RecoveryAction.REUSE_LAST_FRAME] == 0:
                return RecoveryAction.REUSE_LAST_FRAME
            return RecoveryAction.SPLIT_SHOT
        if DefectType.DURATION_MISMATCH in types:
            if counts[RecoveryAction.ADJUST_VOICE_SPEED] == 0:
                return RecoveryAction.ADJUST_VOICE_SPEED
            return RecoveryAction.SPLIT_DIALOGUE
        if DefectType.TOOL_ERROR in types:
            return RecoveryAction.RETRY_SAME
        return RecoveryAction.REWRITE_PROMPT
