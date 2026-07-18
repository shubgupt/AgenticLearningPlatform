"""
Phase 3: Semantic chunking via chonkie + context window attachment.

Consumes the block list from parser.extract() and returns Chunk objects with:
- Semantic boundaries determined by chonkie's SemanticChunker
- heading_path reconstructed from is_heading=True blocks
- context_prefix / context_suffix: ±200 tokens from neighboring chunks
"""
from __future__ import annotations

import logging
import uuid

from .schemas import Chunk

logger = logging.getLogger(__name__)

_CONTEXT_TOKENS = 200
_CHUNK_SIZE = 300
_OVERLAP = 50


def chunk(blocks: list[dict], ingestion_id: str) -> list[Chunk]:
    """Semantic-chunk the block list and return Chunk objects."""
    if not blocks:
        return []

    # Build a parallel list of (page, is_heading, text) for provenance tracking
    annotated = [(b["page"], b["is_heading"], b["text"]) for b in blocks]

    joined_text = "\n".join(b["text"] for b in blocks)
    raw_chunks = _semantic_split(joined_text)

    chunks: list[Chunk] = []
    current_heading_path: list[str] = []

    for i, raw_text in enumerate(raw_chunks):
        chunk_id = str(uuid.uuid4())

        # Find which blocks belong to this chunk (best-effort text matching)
        page_start, page_end, heading_path = _infer_provenance(
            raw_text, annotated, current_heading_path
        )

        # Update running heading state
        for _page, is_heading, text in annotated:
            if is_heading and text in raw_text:
                if text not in current_heading_path:
                    current_heading_path = current_heading_path + [text]

        # Context window: previous and next raw chunks
        prefix = _tail_tokens(raw_chunks[i - 1], _CONTEXT_TOKENS) if i > 0 else ""
        suffix = _head_tokens(raw_chunks[i + 1], _CONTEXT_TOKENS) if i < len(raw_chunks) - 1 else ""

        chunks.append(Chunk(
            chunk_id=chunk_id,
            ingestion_id=ingestion_id,
            text=raw_text,
            context_prefix=prefix,
            context_suffix=suffix,
            page_start=page_start,
            page_end=page_end,
            heading_path=heading_path,
        ))

    return chunks


def _semantic_split(text: str) -> list[str]:
    """
    Use chonkie SemanticChunker. Falls back to paragraph splitting if
    chonkie is unavailable or fails.
    """
    try:
        from chonkie import SemanticChunker
        chunker = SemanticChunker(
            embedding_model="all-MiniLM-L6-v2",
            chunk_size=_CHUNK_SIZE,
            chunk_overlap=_OVERLAP,
        )
        result = chunker.chunk(text)
        # chonkie Chunk objects have a .text attribute
        texts = [c.text for c in result if hasattr(c, "text") and c.text.strip()]
        if texts:
            return texts
        logger.warning("chonkie returned empty chunks; falling back to paragraph split")
    except Exception as exc:
        logger.warning("chonkie unavailable (%s); falling back to paragraph split", exc)

    return _paragraph_split(text)


def _paragraph_split(text: str) -> list[str]:
    """Simple double-newline paragraph splitter."""
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    return paragraphs or [text]


def _infer_provenance(
    chunk_text: str,
    annotated: list[tuple[int, bool, str]],
    current_heading_path: list[str],
) -> tuple[int, int, list[str]]:
    """Return (page_start, page_end, heading_path) by scanning annotated blocks."""
    pages = []
    headings_in_chunk: list[str] = []

    for page, is_heading, text in annotated:
        if text in chunk_text:
            pages.append(page)
            if is_heading:
                headings_in_chunk.append(text)

    page_start = min(pages) if pages else 1
    page_end = max(pages) if pages else 1

    # Carry forward current heading path, then add any new headings in this chunk
    heading_path = list(current_heading_path)
    for h in headings_in_chunk:
        if h not in heading_path:
            heading_path.append(h)

    return page_start, page_end, heading_path


def _tail_tokens(text: str, n: int) -> str:
    """Return approximately the last n whitespace-delimited tokens."""
    tokens = text.split()
    return " ".join(tokens[-n:]) if len(tokens) > n else text


def _head_tokens(text: str, n: int) -> str:
    """Return approximately the first n whitespace-delimited tokens."""
    tokens = text.split()
    return " ".join(tokens[:n]) if len(tokens) > n else text
