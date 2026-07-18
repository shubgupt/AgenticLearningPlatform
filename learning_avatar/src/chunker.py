"""
PDF ingestion orchestrator.

process_document_pipeline(pdf_path) is the single entry point:
  1. Parse (docling)           → structured blocks
  2. Chunk (chonkie semantic)  → Chunk objects
  3. Embed (Jina late-chunk)   → 768-dim vectors
  4. Cards (ollama/llama3.2)   → 7 LearningCard objects per chunk
  5. Link (cosine similarity)  → ChunkLink objects

Each step is independently replaceable. The pipeline can be called directly:
    python src/chunker.py path/to/file.pdf
or imported by the FastAPI ingest routes.
"""
from __future__ import annotations

import logging
import sys
import uuid
from pathlib import Path

logger = logging.getLogger(__name__)


def _init_store():
    from learning_avatar.config import settings
    from pdf_ingestion import store
    store.configure(settings.pdf_db_path)
    return store


def process_document_pipeline(pdf_path: str) -> dict:
    """
    Full ingestion pipeline. Returns a dict with ingestion_id and counts.
    Raises on fatal errors (file not found, parse failure).
    """
    from pdf_ingestion import parser, chunker, embedder, card_generator, linker

    store = _init_store()

    if not Path(pdf_path).exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    ingestion_id = str(uuid.uuid4())
    filename = Path(pdf_path).name
    store.create_ingestion(ingestion_id, filename)
    logger.info("Ingestion %s started for %s", ingestion_id, filename)

    try:
        # ── Step 1: Parse ──────────────────────────────────────────────────
        logger.info("[1/5] Parsing %s with docling…", filename)
        blocks = parser.extract(pdf_path)
        page_count = max((b["page"] for b in blocks), default=0)
        logger.info("      Extracted %d blocks across %d pages", len(blocks), page_count)

        # ── Step 2: Chunk ──────────────────────────────────────────────────
        logger.info("[2/5] Chunking with chonkie SemanticChunker…")
        chunks = chunker.chunk(blocks, ingestion_id)
        store.save_chunks(chunks)
        logger.info("      Created %d chunks", len(chunks))

        # ── Step 3: Embed ──────────────────────────────────────────────────
        logger.info("[3/5] Embedding with jinaai/jina-embeddings-v2-base-en…")
        vectors = [embedder.embed(c) for c in chunks]
        store.save_embeddings(chunks, vectors)
        logger.info("      Stored %d embeddings", len(vectors))

        # ── Step 4: Cards ──────────────────────────────────────────────────
        logger.info("[4/5] Generating learning cards via ollama…")
        cards = card_generator.generate(chunks)
        store.save_cards(cards)
        logger.info("      Generated %d cards", len(cards))

        # ── Step 5: Link ───────────────────────────────────────────────────
        logger.info("[5/5] Computing concept links…")
        links = linker.link(chunks)
        store.save_links(links)
        logger.info("      Found %d links", len(links))

        store.mark_done(ingestion_id, page_count)
        logger.info("Ingestion %s complete.", ingestion_id)

    except Exception as exc:
        store.mark_failed(ingestion_id, str(exc))
        logger.error("Ingestion %s failed: %s", ingestion_id, exc)
        raise

    return {
        "ingestion_id": ingestion_id,
        "filename": filename,
        "page_count": page_count,
        "chunk_count": len(chunks),
        "card_count": len(cards),
        "link_count": len(links),
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    if len(sys.argv) < 2:
        print("Usage: python src/chunker.py path/to/file.pdf")
        sys.exit(1)
    result = process_document_pipeline(sys.argv[1])
    for k, v in result.items():
        print(f"  {k}: {v}")
