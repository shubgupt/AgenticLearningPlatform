"""
FastAPI router for PDF ingestion endpoints.

Mounted in web/main.py as an include_router() call.
All routes are synchronous because the pipeline is CPU/GPU-bound;
a background task queue can be added later if needed.
"""
from __future__ import annotations

import logging
import tempfile
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ingest", tags=["ingest"])


def _store():
    from learning_avatar.config import settings
    from pdf_ingestion import store
    store.configure(settings.pdf_db_path)
    return store


# ── ingest (upload + run pipeline) ───────────────────────────────────────────

@router.post("", status_code=202)
async def ingest_pdf(file: UploadFile):
    """
    Accept a PDF upload, run the full ingestion pipeline, and return counts.
    Runs synchronously — large PDFs will take time while Jina loads.
    """
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")

    # Write upload to a temp file (UploadFile is a stream)
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        from chunker import process_document_pipeline
        result = process_document_pipeline(tmp_path)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.error("Pipeline failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {exc}")
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    return result


# ── status ────────────────────────────────────────────────────────────────────

@router.get("/{ingestion_id}")
def get_ingestion(ingestion_id: str):
    store = _store()
    record = store.get_ingestion(ingestion_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Ingestion not found")
    return record


# ── chunks ────────────────────────────────────────────────────────────────────

@router.get("/{ingestion_id}/chunks")
def get_chunks(ingestion_id: str):
    store = _store()
    return store.get_chunks(ingestion_id)


# ── cards ─────────────────────────────────────────────────────────────────────

@router.get("/{ingestion_id}/cards")
def get_cards(ingestion_id: str, type: str | None = None):
    """Optional ?type= filter: standard|simplified|analogy|hint|quiz|teacher_note|recap"""
    store = _store()
    return store.get_cards(ingestion_id, card_type=type)


# ── links ─────────────────────────────────────────────────────────────────────

@router.get("/{ingestion_id}/links")
def get_links(ingestion_id: str):
    store = _store()
    return store.get_links(ingestion_id)


# ── learner signals ───────────────────────────────────────────────────────────

@router.get("/signals/{session_id}")
def get_signals(session_id: str):
    """Teacher-only: return all behavioral signals for a session."""
    store = _store()
    return store.get_signals(session_id)


@router.post("/signals/{session_id}/break")
def record_break(session_id: str):
    """Record a student-initiated break."""
    from pdf_ingestion.signal_detector import detect_break_signal
    store = _store()
    signal = detect_break_signal(session_id)
    store.save_signals([signal])
    return signal
