from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _bool_env(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    db_path: Path
    artifact_root: Path
    comfyui_url: str
    dry_run: bool
    max_attempts: int
    default_budget: float

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            db_path=Path(os.getenv("LULU_DB_PATH", "data/lulustudio.db")),
            artifact_root=Path(os.getenv("LULU_ARTIFACT_ROOT", "data/artifacts")),
            comfyui_url=os.getenv("LULU_COMFYUI_URL", "http://127.0.0.1:6006").rstrip("/"),
            dry_run=_bool_env("LULU_DRY_RUN", True),
            max_attempts=int(os.getenv("LULU_MAX_ATTEMPTS", "4")),
            default_budget=float(os.getenv("LULU_DEFAULT_BUDGET", "20")),
        )
