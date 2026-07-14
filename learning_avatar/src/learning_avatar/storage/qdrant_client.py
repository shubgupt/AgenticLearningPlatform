"""
Project VectorDB & Storage Layer (plan doc section 2.1.5) -- the Qdrant
half of it. STUB ONLY. Nothing in this file is implemented; nothing in the
rest of the codebase calls it yet.

What this is for, when it's built: semantic search over teacher-uploaded
curriculum documents and the "child chunk" (~50 token) / "parent chunk"
(~500 token) retrieval pattern described in the plan doc section 5.2 --
feeding the Self-RAG / CRAG / GraphRAG-Lite nodes that also don't exist yet
(see orchestrator/nodes.py's TODOs). SQLite (core/state_store.py) already
handles session/profile storage and isn't affected by any of this.

Deliberately not stubbed with a fake in-memory implementation -- that would
look like it works and hide the fact that nothing is wired to a real vector
index yet. NotImplementedError is the honest state.
"""
from __future__ import annotations
from typing import Any


class QdrantNotConfiguredError(NotImplementedError):
    """Raised by every function in this module. There's no Qdrant instance,
    collection schema, or embedding pipeline set up in this scaffold yet --
    see plan doc section 5.2 for the intended chunking design when someone
    picks this up."""


def upsert_document_chunks(document_id: str, chunks: list[dict[str, Any]]) -> None:
    raise QdrantNotConfiguredError("storage.qdrant_client.upsert_document_chunks is not implemented yet")


def semantic_search(query: str, top_k: int = 5) -> list[dict[str, Any]]:
    raise QdrantNotConfiguredError("storage.qdrant_client.semantic_search is not implemented yet")
