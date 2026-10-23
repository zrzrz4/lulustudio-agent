from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterator

from .models import EpisodeSpec, RunStatus


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


class Database:
    def __init__(self, path: Path | str):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()

    def init_schema(self) -> None:
        with self.connect() as db:
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS episodes (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    spec_json TEXT NOT NULL,
                    status TEXT NOT NULL,
                    budget_total REAL NOT NULL,
                    budget_spent REAL NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS shots (
                    id TEXT PRIMARY KEY,
                    episode_id TEXT NOT NULL REFERENCES episodes(id) ON DELETE CASCADE,
                    position INTEGER NOT NULL,
                    spec_json TEXT NOT NULL,
                    status TEXT NOT NULL,
                    current_attempt INTEGER NOT NULL DEFAULT 0,
                    accepted_attempt_id TEXT,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS attempts (
                    id TEXT PRIMARY KEY,
                    shot_id TEXT NOT NULL REFERENCES shots(id) ON DELETE CASCADE,
                    attempt_no INTEGER NOT NULL,
                    action TEXT,
                    input_json TEXT NOT NULL,
                    output_json TEXT NOT NULL,
                    status TEXT NOT NULL,
                    cost REAL NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    UNIQUE(shot_id, attempt_no)
                );
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    episode_id TEXT NOT NULL,
                    shot_id TEXT,
                    event_type TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS feedback (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    attempt_id TEXT NOT NULL,
                    accepted INTEGER NOT NULL,
                    reasons_json TEXT NOT NULL,
                    preferred_over_attempt_id TEXT,
                    created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_events_episode ON events(episode_id, id);
                CREATE INDEX IF NOT EXISTS idx_attempts_shot ON attempts(shot_id, attempt_no);
                """
            )

    def create_episode(self, spec: EpisodeSpec) -> None:
        now = utc_now()
        with self.connect() as db:
            db.execute(
                "INSERT INTO episodes VALUES (?, ?, ?, ?, ?, 0, ?, ?)",
                (spec.episode_id, spec.title, spec.model_dump_json(), RunStatus.PENDING, spec.budget, now, now),
            )
            for position, shot in enumerate(spec.shots):
                db.execute(
                    "INSERT INTO shots VALUES (?, ?, ?, ?, ?, 0, NULL, ?)",
                    (shot.shot_id, spec.episode_id, position, shot.model_dump_json(), RunStatus.PENDING, now),
                )
            self._append_event(db, spec.episode_id, None, "episode.created", spec.model_dump(mode="json"))

    def get_episode(self, episode_id: str) -> dict[str, Any] | None:
        with self.connect() as db:
            episode = db.execute("SELECT * FROM episodes WHERE id = ?", (episode_id,)).fetchone()
            if episode is None:
                return None
            shots = db.execute(
                "SELECT * FROM shots WHERE episode_id = ? ORDER BY position", (episode_id,)
            ).fetchall()
            result = dict(episode)
            result["spec"] = json.loads(result.pop("spec_json"))
            result["shots"] = []
            for row in shots:
                item = dict(row)
                item["spec"] = json.loads(item.pop("spec_json"))
                result["shots"].append(item)
            return result

    def pending_shots(self, episode_id: str) -> list[dict[str, Any]]:
        with self.connect() as db:
            rows = db.execute(
                "SELECT * FROM shots WHERE episode_id = ? AND status NOT IN (?, ?) ORDER BY position",
                (episode_id, RunStatus.SUCCEEDED, RunStatus.FAILED),
            ).fetchall()
            return [dict(row) | {"spec": json.loads(row["spec_json"])} for row in rows]

    def attempts_for_shot(self, shot_id: str) -> list[dict[str, Any]]:
        with self.connect() as db:
            rows = db.execute(
                "SELECT * FROM attempts WHERE shot_id = ? ORDER BY attempt_no", (shot_id,)
            ).fetchall()
            return [dict(row) | {"output": json.loads(row["output_json"])} for row in rows]

    def record_attempt(
        self,
        *,
        attempt_id: str,
        episode_id: str,
        shot_id: str,
        attempt_no: int,
        action: str | None,
        input_data: dict[str, Any],
        output_data: dict[str, Any],
        status: RunStatus,
        cost: float,
    ) -> None:
        now = utc_now()
        with self.connect() as db:
            db.execute(
                """INSERT INTO attempts
                (id, shot_id, attempt_no, action, input_json, output_json, status, cost, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    attempt_id,
                    shot_id,
                    attempt_no,
                    action,
                    json.dumps(input_data, ensure_ascii=False),
                    json.dumps(output_data, ensure_ascii=False),
                    status,
                    cost,
                    now,
                ),
            )
            db.execute(
                "UPDATE shots SET current_attempt = ?, status = ?, updated_at = ? WHERE id = ?",
                (attempt_no, status, now, shot_id),
            )
            db.execute(
                "UPDATE episodes SET budget_spent = budget_spent + ?, updated_at = ? WHERE id = ?",
                (cost, now, episode_id),
            )
            self._append_event(
                db,
                episode_id,
                shot_id,
                "attempt.completed",
                {"attempt_id": attempt_id, "attempt_no": attempt_no, "action": action, "status": status},
            )

    def mark_shot(self, episode_id: str, shot_id: str, status: RunStatus, attempt_id: str | None = None) -> None:
        now = utc_now()
        with self.connect() as db:
            db.execute(
                "UPDATE shots SET status = ?, accepted_attempt_id = COALESCE(?, accepted_attempt_id), updated_at = ? WHERE id = ?",
                (status, attempt_id, now, shot_id),
            )
            self._append_event(db, episode_id, shot_id, f"shot.{status}", {"attempt_id": attempt_id})

    def mark_episode(self, episode_id: str, status: RunStatus) -> None:
        now = utc_now()
        with self.connect() as db:
            db.execute("UPDATE episodes SET status = ?, updated_at = ? WHERE id = ?", (status, now, episode_id))
            self._append_event(db, episode_id, None, f"episode.{status}", {})

    def add_feedback(self, payload: dict[str, Any]) -> None:
        with self.connect() as db:
            db.execute(
                """INSERT INTO feedback
                (attempt_id, accepted, reasons_json, preferred_over_attempt_id, created_at)
                VALUES (?, ?, ?, ?, ?)""",
                (
                    payload["attempt_id"],
                    int(payload["accepted"]),
                    json.dumps(payload.get("reasons", []), ensure_ascii=False),
                    payload.get("preferred_over_attempt_id"),
                    utc_now(),
                ),
            )

    def export_trajectories(self) -> list[dict[str, Any]]:
        with self.connect() as db:
            rows = db.execute(
                """SELECT a.*, s.episode_id, f.accepted, f.reasons_json, f.preferred_over_attempt_id
                FROM attempts a
                JOIN shots s ON s.id = a.shot_id
                LEFT JOIN feedback f ON f.attempt_id = a.id
                ORDER BY a.created_at"""
            ).fetchall()
            result = []
            for row in rows:
                item = dict(row)
                for field in ("input_json", "output_json", "reasons_json"):
                    if item.get(field) is not None:
                        item[field.removesuffix("_json")] = json.loads(item.pop(field))
                result.append(item)
            return result

    @staticmethod
    def _append_event(
        db: sqlite3.Connection,
        episode_id: str,
        shot_id: str | None,
        event_type: str,
        payload: dict[str, Any],
    ) -> None:
        db.execute(
            "INSERT INTO events (episode_id, shot_id, event_type, payload_json, created_at) VALUES (?, ?, ?, ?, ?)",
            (episode_id, shot_id, event_type, json.dumps(payload, ensure_ascii=False), utc_now()),
        )
