"""
SQLite storage for two things:
  1. Chat sessions + message history (so follow-up questions have memory)
  2. Evaluation run results (so the Evaluation Dashboard can show past
     runs, not just the most recent one - "timestamped evaluation runs")

SQLite is used instead of Postgres so the whole project runs with zero
external database servers - just a local .db file, which is what makes
"no Docker, local venv only" actually practical.
"""

import json
import logging
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone

from app.core.config import settings

logger = logging.getLogger(__name__)


def _ensure_dir() -> None:
    os.makedirs(os.path.dirname(settings.sqlite_path) or ".", exist_ok=True)


@contextmanager
def get_conn():
    _ensure_dir()
    conn = sqlite3.connect(settings.sqlite_path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with get_conn() as conn:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                created_at TEXT
            )"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                role TEXT,
                content TEXT,
                created_at TEXT
            )"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS eval_runs (
                id TEXT PRIMARY KEY,
                created_at TEXT,
                aggregate_json TEXT,
                results_json TEXT
            )"""
        )
    logger.info("SQLite tables ensured at %s", settings.sqlite_path)


# ---------------------------------------------------------------------------
# Chat memory
# ---------------------------------------------------------------------------
def ensure_session(session_id: str) -> None:
    with get_conn() as conn:
        row = conn.execute("SELECT id FROM sessions WHERE id = ?", (session_id,)).fetchone()
        if not row:
            conn.execute(
                "INSERT INTO sessions (id, created_at) VALUES (?, ?)",
                (session_id, datetime.now(timezone.utc).isoformat()),
            )


def save_message(session_id: str, role: str, content: str) -> None:
    ensure_session(session_id)
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO messages (session_id, role, content, created_at) VALUES (?, ?, ?, ?)",
            (session_id, role, content, datetime.now(timezone.utc).isoformat()),
        )


def get_history(session_id: str, limit: int = 20) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT role, content FROM messages WHERE session_id = ? ORDER BY id DESC LIMIT ?",
            (session_id, limit),
        ).fetchall()
    rows = list(reversed(rows))
    return [{"role": r["role"], "content": r["content"]} for r in rows]


# ---------------------------------------------------------------------------
# Evaluation run persistence
# ---------------------------------------------------------------------------
def save_eval_run(run_id: str, aggregate: dict, results: list[dict]) -> None:
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO eval_runs (id, created_at, aggregate_json, results_json) VALUES (?, ?, ?, ?)",
            (
                run_id,
                datetime.now(timezone.utc).isoformat(),
                json.dumps(aggregate),
                json.dumps(results),
            ),
        )


def list_eval_runs() -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT id, created_at, aggregate_json FROM eval_runs ORDER BY created_at DESC"
        ).fetchall()
    return [
        {"run_id": r["id"], "created_at": r["created_at"], "aggregate": json.loads(r["aggregate_json"])}
        for r in rows
    ]


def get_eval_run(run_id: str) -> dict | None:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT id, created_at, aggregate_json, results_json FROM eval_runs WHERE id = ?",
            (run_id,),
        ).fetchone()
    if not row:
        return None
    return {
        "run_id": row["id"],
        "created_at": row["created_at"],
        "aggregate": json.loads(row["aggregate_json"]),
        "results": json.loads(row["results_json"]),
    }
