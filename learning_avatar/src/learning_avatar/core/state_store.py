"""
Zero-cost session storage: one SQLite file, one table, JSON blob column.
This is deliberately the simplest thing that could work -- the point of the
exercise is agent architecture, not database design. Swap this module out
for Postgres/Redis/whatever later without touching main.py or the agents,
since they only ever call get_session()/save_session().
"""
from __future__ import annotations
import json
import sqlite3
import uuid
from contextlib import contextmanager

from learning_avatar.config import settings
from learning_avatar.core.schemas import SessionState

_SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    session_id TEXT PRIMARY KEY,
    state_json TEXT NOT NULL
);
"""


@contextmanager
def _connect():
    conn = sqlite3.connect(settings.db_path)
    try:
        conn.execute(_SCHEMA)
        yield conn
        conn.commit()
    finally:
        conn.close()


def create_session() -> SessionState:
    session_id = str(uuid.uuid4())
    state = SessionState(session_id=session_id)
    with _connect() as conn:
        conn.execute(
            "INSERT INTO sessions (session_id, state_json) VALUES (?, ?)",
            (session_id, state.model_dump_json()),
        )
    return state


def get_session(session_id: str) -> SessionState | None:
    with _connect() as conn:
        row = conn.execute(
            "SELECT state_json FROM sessions WHERE session_id = ?", (session_id,)
        ).fetchone()
    if row is None:
        return None
    return SessionState.model_validate_json(row[0])


def save_session(state: SessionState) -> None:
    with _connect() as conn:
        conn.execute(
            "UPDATE sessions SET state_json = ? WHERE session_id = ?",
            (state.model_dump_json(), state.session_id),
        )
