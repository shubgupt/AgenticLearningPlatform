from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from .schemas import Chunk, ChunkLink, IngestionRecord, LearningCard, LearnerSignal

_DB_PATH: Path | None = None

_SCHEMA = """
CREATE TABLE IF NOT EXISTS ingestions (
    ingestion_id TEXT PRIMARY KEY,
    filename     TEXT NOT NULL,
    page_count   INTEGER NOT NULL DEFAULT 0,
    status       TEXT NOT NULL,
    error        TEXT,
    created_at   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS chunks (
    chunk_id       TEXT PRIMARY KEY,
    ingestion_id   TEXT NOT NULL,
    text           TEXT NOT NULL,
    context_prefix TEXT NOT NULL DEFAULT '',
    context_suffix TEXT NOT NULL DEFAULT '',
    page_start     INTEGER NOT NULL DEFAULT 1,
    page_end       INTEGER NOT NULL DEFAULT 1,
    heading_path   TEXT NOT NULL DEFAULT '[]'
);

CREATE TABLE IF NOT EXISTS embeddings (
    chunk_id    TEXT PRIMARY KEY,
    vector_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS learning_cards (
    card_id   TEXT PRIMARY KEY,
    chunk_id  TEXT NOT NULL,
    card_type TEXT NOT NULL,
    card_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS chunk_links (
    link_id         TEXT PRIMARY KEY,
    source_chunk_id TEXT NOT NULL,
    target_id       TEXT NOT NULL,
    target_type     TEXT NOT NULL,
    relation        TEXT NOT NULL,
    confidence      REAL NOT NULL,
    evidence        TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS learner_signals (
    signal_id   TEXT PRIMARY KEY,
    session_id  TEXT NOT NULL,
    signal_type TEXT NOT NULL,
    confidence  REAL NOT NULL,
    scope       TEXT NOT NULL,
    evidence    TEXT NOT NULL,
    created_at  TEXT NOT NULL
);
"""


def configure(db_path: str) -> None:
    global _DB_PATH
    _DB_PATH = Path(db_path)


@contextmanager
def _connect():
    if _DB_PATH is None:
        raise RuntimeError("call store.configure(db_path) before using the store")
    conn = sqlite3.connect(str(_DB_PATH))
    try:
        conn.executescript(_SCHEMA)
        yield conn
        conn.commit()
    finally:
        conn.close()


# ── ingestions ───────────────────────────────────────────────────────────────

def create_ingestion(ingestion_id: str, filename: str) -> None:
    with _connect() as conn:
        conn.execute(
            "INSERT INTO ingestions (ingestion_id, filename, status, created_at) VALUES (?,?,?,?)",
            (ingestion_id, filename, "pending", datetime.now(timezone.utc).isoformat()),
        )


def mark_done(ingestion_id: str, page_count: int) -> None:
    with _connect() as conn:
        conn.execute(
            "UPDATE ingestions SET status='done', page_count=? WHERE ingestion_id=?",
            (page_count, ingestion_id),
        )


def mark_failed(ingestion_id: str, error: str) -> None:
    with _connect() as conn:
        conn.execute(
            "UPDATE ingestions SET status='failed', error=? WHERE ingestion_id=?",
            (error, ingestion_id),
        )


def get_ingestion(ingestion_id: str) -> IngestionRecord | None:
    with _connect() as conn:
        row = conn.execute(
            "SELECT ingestion_id, filename, page_count, status, error, created_at "
            "FROM ingestions WHERE ingestion_id=?", (ingestion_id,)
        ).fetchone()
    if row is None:
        return None
    return IngestionRecord(
        ingestion_id=row[0], filename=row[1], page_count=row[2],
        status=row[3], error=row[4], created_at=row[5],
    )


# ── chunks ───────────────────────────────────────────────────────────────────

def save_chunks(chunks: list[Chunk]) -> None:
    if not chunks:
        return
    with _connect() as conn:
        conn.executemany(
            "INSERT OR REPLACE INTO chunks "
            "(chunk_id, ingestion_id, text, context_prefix, context_suffix, page_start, page_end, heading_path) "
            "VALUES (?,?,?,?,?,?,?,?)",
            [
                (c.chunk_id, c.ingestion_id, c.text, c.context_prefix, c.context_suffix,
                 c.page_start, c.page_end, json.dumps(c.heading_path))
                for c in chunks
            ],
        )


def get_chunks(ingestion_id: str) -> list[Chunk]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT chunk_id, ingestion_id, text, context_prefix, context_suffix, "
            "page_start, page_end, heading_path FROM chunks WHERE ingestion_id=?",
            (ingestion_id,),
        ).fetchall()
    return [
        Chunk(
            chunk_id=r[0], ingestion_id=r[1], text=r[2],
            context_prefix=r[3], context_suffix=r[4],
            page_start=r[5], page_end=r[6],
            heading_path=json.loads(r[7]),
        )
        for r in rows
    ]


def get_all_chunks_with_embeddings() -> list[tuple[Chunk, list[float]]]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT c.chunk_id, c.ingestion_id, c.text, c.context_prefix, c.context_suffix, "
            "c.page_start, c.page_end, c.heading_path, e.vector_json "
            "FROM chunks c JOIN embeddings e ON c.chunk_id = e.chunk_id"
        ).fetchall()
    result = []
    for r in rows:
        chunk = Chunk(
            chunk_id=r[0], ingestion_id=r[1], text=r[2],
            context_prefix=r[3], context_suffix=r[4],
            page_start=r[5], page_end=r[6], heading_path=json.loads(r[7]),
        )
        vector = json.loads(r[8])
        result.append((chunk, vector))
    return result


# ── embeddings ───────────────────────────────────────────────────────────────

def save_embeddings(chunks: list[Chunk], vectors: list[list[float]]) -> None:
    if not chunks:
        return
    with _connect() as conn:
        conn.executemany(
            "INSERT OR REPLACE INTO embeddings (chunk_id, vector_json) VALUES (?,?)",
            [(c.chunk_id, json.dumps(v)) for c, v in zip(chunks, vectors)],
        )


def get_embedding(chunk_id: str) -> list[float] | None:
    with _connect() as conn:
        row = conn.execute(
            "SELECT vector_json FROM embeddings WHERE chunk_id=?", (chunk_id,)
        ).fetchone()
    return json.loads(row[0]) if row else None


# ── learning cards ────────────────────────────────────────────────────────────

def save_cards(cards: list[LearningCard]) -> None:
    if not cards:
        return
    with _connect() as conn:
        conn.executemany(
            "INSERT OR REPLACE INTO learning_cards (card_id, chunk_id, card_type, card_json) "
            "VALUES (?,?,?,?)",
            [(c.card_id, c.chunk_id, c.card_type.value, c.model_dump_json()) for c in cards],
        )


def get_cards(ingestion_id: str, card_type: str | None = None) -> list[LearningCard]:
    with _connect() as conn:
        if card_type:
            rows = conn.execute(
                "SELECT card_json FROM learning_cards lc "
                "JOIN chunks ch ON lc.chunk_id = ch.chunk_id "
                "WHERE ch.ingestion_id=? AND lc.card_type=?",
                (ingestion_id, card_type),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT card_json FROM learning_cards lc "
                "JOIN chunks ch ON lc.chunk_id = ch.chunk_id "
                "WHERE ch.ingestion_id=?",
                (ingestion_id,),
            ).fetchall()
    return [LearningCard.model_validate_json(r[0]) for r in rows]


def get_cards_for_chunk(chunk_id: str) -> list[LearningCard]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT card_json FROM learning_cards WHERE chunk_id=?", (chunk_id,)
        ).fetchall()
    return [LearningCard.model_validate_json(r[0]) for r in rows]


# ── chunk links ───────────────────────────────────────────────────────────────

def save_links(links: list[ChunkLink]) -> None:
    if not links:
        return
    with _connect() as conn:
        conn.executemany(
            "INSERT OR REPLACE INTO chunk_links "
            "(link_id, source_chunk_id, target_id, target_type, relation, confidence, evidence) "
            "VALUES (?,?,?,?,?,?,?)",
            [
                (l.link_id, l.source_chunk_id, l.target_id, l.target_type,
                 l.relation, l.confidence, l.evidence)
                for l in links
            ],
        )


def get_links(ingestion_id: str) -> list[ChunkLink]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT cl.link_id, cl.source_chunk_id, cl.target_id, cl.target_type, "
            "cl.relation, cl.confidence, cl.evidence "
            "FROM chunk_links cl "
            "JOIN chunks ch ON cl.source_chunk_id = ch.chunk_id "
            "WHERE ch.ingestion_id=?",
            (ingestion_id,),
        ).fetchall()
    return [
        ChunkLink(
            link_id=r[0], source_chunk_id=r[1], target_id=r[2],
            target_type=r[3], relation=r[4], confidence=r[5], evidence=r[6],
        )
        for r in rows
    ]


def find_top_k_similar(query_vector: list[float], top_k: int = 5) -> list[tuple[str, float]]:
    rows = get_all_chunks_with_embeddings()
    if not rows:
        return []

    import math

    def cosine(a: list[float], b: list[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b))
        na = math.sqrt(sum(x * x for x in a))
        nb = math.sqrt(sum(x * x for x in b))
        return dot / (na * nb) if na and nb else 0.0

    scored = [(chunk.chunk_id, cosine(query_vector, vec)) for chunk, vec in rows]
    scored.sort(key=lambda t: t[1], reverse=True)
    return scored[:top_k]


# ── learner signals ───────────────────────────────────────────────────────────

def save_signals(signals: list[LearnerSignal]) -> None:
    if not signals:
        return
    with _connect() as conn:
        conn.executemany(
            "INSERT OR REPLACE INTO learner_signals "
            "(signal_id, session_id, signal_type, confidence, scope, evidence, created_at) "
            "VALUES (?,?,?,?,?,?,?)",
            [
                (s.signal_id, s.session_id, s.signal_type, s.confidence,
                 s.scope, s.evidence, s.created_at)
                for s in signals
            ],
        )


def get_signals(session_id: str) -> list[LearnerSignal]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT signal_id, session_id, signal_type, confidence, scope, evidence, created_at "
            "FROM learner_signals WHERE session_id=?",
            (session_id,),
        ).fetchall()
    return [
        LearnerSignal(
            signal_id=r[0], session_id=r[1], signal_type=r[2],
            confidence=r[3], scope=r[4], evidence=r[5], created_at=r[6],
        )
        for r in rows
    ]
