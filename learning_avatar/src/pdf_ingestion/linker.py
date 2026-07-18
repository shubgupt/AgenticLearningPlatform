"""
Phase 7: Cosine-similarity linker over stored Jina embeddings.

Thresholds (tunable):
  > 0.82  → same_concept
  0.70–0.82 → supports
  < 0.70  → not linked

Also checks chunk text against concept_definitions.json misconception strings
to produce misconception_match links.
"""
from __future__ import annotations

import json
import logging
import uuid
from pathlib import Path

from .schemas import Chunk, ChunkLink

logger = logging.getLogger(__name__)

_SAME_CONCEPT_THRESHOLD = 0.82
_SUPPORTS_THRESHOLD = 0.70


def link(chunks: list[Chunk]) -> list[ChunkLink]:
    """
    Compute chunk-to-chunk links for this ingestion's chunks.
    Returns [] if no embeddings are stored yet (embedder hasn't run).
    """
    from . import store

    if not chunks:
        return []

    all_embedded = store.get_all_chunks_with_embeddings()
    if not all_embedded:
        logger.info("No embeddings found — skipping link computation")
        return []

    # Build lookup: chunk_id → vector
    vec_map: dict[str, list[float]] = {c.chunk_id: v for c, v in all_embedded}

    # IDs of this ingestion's chunks that have embeddings
    local_ids = {c.chunk_id for c in chunks if c.chunk_id in vec_map}
    if not local_ids:
        return []

    links: list[ChunkLink] = []
    seen_pairs: set[frozenset] = set()

    for chunk in chunks:
        if chunk.chunk_id not in vec_map:
            continue
        q_vec = vec_map[chunk.chunk_id]

        similar = store.find_top_k_similar(q_vec, top_k=10)
        for target_id, score in similar:
            if target_id == chunk.chunk_id:
                continue
            pair = frozenset({chunk.chunk_id, target_id})
            if pair in seen_pairs:
                continue
            seen_pairs.add(pair)

            if score >= _SAME_CONCEPT_THRESHOLD:
                relation = "same_concept"
            elif score >= _SUPPORTS_THRESHOLD:
                relation = "supports"
            else:
                continue

            links.append(ChunkLink(
                link_id=str(uuid.uuid4()),
                source_chunk_id=chunk.chunk_id,
                target_id=target_id,
                target_type="chunk",
                relation=relation,
                confidence=round(score, 4),
                evidence=f"cosine_similarity={score:.4f}",
            ))

    # Misconception matching against concept_definitions.json
    links.extend(_misconception_links(chunks, vec_map))

    return links


def _misconception_links(chunks: list[Chunk], vec_map: dict) -> list[ChunkLink]:
    """Tag chunks whose text contains a known misconception description."""
    concept_defs = _load_concept_definitions()
    if not concept_defs:
        return []

    links: list[ChunkLink] = []
    for chunk in chunks:
        text_lower = chunk.text.lower()
        for concept in concept_defs:
            for misconception in concept.get("common_misconceptions", []):
                desc = misconception.get("description", "").lower()
                mc_id = misconception.get("id", "")
                if desc and desc in text_lower:
                    links.append(ChunkLink(
                        link_id=str(uuid.uuid4()),
                        source_chunk_id=chunk.chunk_id,
                        target_id=mc_id,
                        target_type="chunk",
                        relation="misconception_match",
                        confidence=0.75,
                        evidence=f"text contains known misconception: {mc_id}",
                    ))
    return links


def _load_concept_definitions() -> list[dict]:
    try:
        from learning_avatar.config import settings
        path = settings.content_dir / "concept_definitions.json"
        with open(path) as f:
            return json.load(f)
    except Exception as exc:
        logger.warning("Could not load concept_definitions.json: %s", exc)
        return []


def find_related_for_text(query_text: str, top_k: int = 5) -> list[ChunkLink]:
    """
    Find chunks related to arbitrary query text (used by Teaching Agent
    when library lookup misses).
    Returns [] if embeddings store is empty.
    """
    from . import store, embedder

    try:
        # Build a temporary Chunk-like object for embedding
        class _TmpChunk:
            text = query_text
            context_prefix = ""
            context_suffix = ""
            chunk_id = "__query__"
            ingestion_id = "__query__"

        q_vec = embedder.embed(_TmpChunk())
    except Exception as exc:
        logger.warning("Could not embed query text: %s", exc)
        return []

    similar = store.find_top_k_similar(q_vec, top_k=top_k)
    links: list[ChunkLink] = []
    for target_id, score in similar:
        if score < _SUPPORTS_THRESHOLD:
            continue
        relation = "same_concept" if score >= _SAME_CONCEPT_THRESHOLD else "supports"
        links.append(ChunkLink(
            link_id=str(uuid.uuid4()),
            source_chunk_id="__query__",
            target_id=target_id,
            target_type="chunk",
            relation=relation,
            confidence=round(score, 4),
            evidence=f"cosine_similarity={score:.4f}",
        ))
    return links
