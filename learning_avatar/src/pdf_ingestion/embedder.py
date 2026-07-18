"""
Phase 4: Late-chunked embeddings using BAAI/bge-base-en-v1.5 locally.

We target Jina-quality embeddings (768-dim, strong MTEB scores for English)
using BGE-base as the local model. BGE loads cleanly via sentence-transformers
without custom remote code or onnx dependencies, making it the most reliable
local alternative for the course stack.

"Late chunking": each chunk is embedded with its full context window
(context_prefix + text + context_suffix) so the vector captures surrounding
document meaning, not just the isolated chunk text.

The model is lazy-loaded on first call and cached for the process lifetime.
"""
from __future__ import annotations

import logging
import math

logger = logging.getLogger(__name__)

_MODEL_ID = "BAAI/bge-base-en-v1.5"

_model = None


def _load_model():
    global _model
    if _model is not None:
        return

    try:
        from sentence_transformers import SentenceTransformer
    except ImportError:
        raise RuntimeError("sentence-transformers required — run: uv sync")

    logger.info("Loading embedding model %s…", _MODEL_ID)
    _model = SentenceTransformer(_MODEL_ID)
    logger.info("Embedding model loaded (768-dim)")


def embed(chunk) -> list[float]:
    """
    Embed a single Chunk using late-chunking: concatenate context_prefix,
    chunk text, and context_suffix before encoding.

    Returns a normalized 768-dim float list.
    """
    _load_model()

    late_text = " ".join(filter(None, [chunk.context_prefix, chunk.text, chunk.context_suffix]))

    # BGE recommends a query prefix for retrieval; for passages we use no prefix
    embedding = _model.encode(late_text, normalize_embeddings=True, show_progress_bar=False)
    return embedding.tolist()


def cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    return dot / (na * nb) if na and nb else 0.0

