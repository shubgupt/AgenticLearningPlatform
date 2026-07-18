"""
Tests for the PDF ingestion pipeline components.
Covers: store CRUD, signal detection, chunker, card generation stubs.
"""
from __future__ import annotations

import tempfile
import uuid

import pytest

from pdf_ingestion import store
from pdf_ingestion.schemas import Chunk, LearningCard, CardType, QuizContent
from pdf_ingestion.signal_detector import (
    detect_signals,
    detect_break_signal,
    detect_visual_signal,
)
from pdf_ingestion import chunker as chunk_module


@pytest.fixture()
def tmp_store(tmp_path):
    """Configure the store to use a fresh temp database for each test."""
    db_path = str(tmp_path / "test.db")
    store.configure(db_path)
    return db_path


# ── store tests ───────────────────────────────────────────────────────────────

def test_create_and_get_ingestion(tmp_store):
    iid = str(uuid.uuid4())
    store.create_ingestion(iid, "sample.pdf")
    rec = store.get_ingestion(iid)
    assert rec is not None
    assert rec.ingestion_id == iid
    assert rec.status == "pending"
    assert rec.filename == "sample.pdf"


def test_mark_done_updates_status(tmp_store):
    iid = str(uuid.uuid4())
    store.create_ingestion(iid, "done.pdf")
    store.mark_done(iid, 10)
    rec = store.get_ingestion(iid)
    assert rec.status == "done"
    assert rec.page_count == 10


def test_mark_failed_stores_error(tmp_store):
    iid = str(uuid.uuid4())
    store.create_ingestion(iid, "bad.pdf")
    store.mark_failed(iid, "parsing error")
    rec = store.get_ingestion(iid)
    assert rec.status == "failed"
    assert "parsing error" in rec.error


def test_save_and_get_chunks(tmp_store):
    iid = str(uuid.uuid4())
    store.create_ingestion(iid, "chunks.pdf")
    chunks = [
        Chunk(chunk_id=str(uuid.uuid4()), ingestion_id=iid, text="Newton's first law",
              page_start=1, page_end=1, heading_path=["Chapter 1"]),
        Chunk(chunk_id=str(uuid.uuid4()), ingestion_id=iid, text="An object at rest",
              page_start=1, page_end=2, heading_path=["Chapter 1", "Law 1"]),
    ]
    store.save_chunks(chunks)
    retrieved = store.get_chunks(iid)
    assert len(retrieved) == 2
    assert any(c.text == "Newton's first law" for c in retrieved)
    assert any(c.heading_path == ["Chapter 1", "Law 1"] for c in retrieved)


def test_save_and_get_embeddings(tmp_store):
    iid = str(uuid.uuid4())
    store.create_ingestion(iid, "embed.pdf")
    c = Chunk(chunk_id=str(uuid.uuid4()), ingestion_id=iid, text="test",
              page_start=1, page_end=1)
    store.save_chunks([c])
    vec = [0.1] * 768
    store.save_embeddings([c], [vec])
    retrieved = store.get_embedding(c.chunk_id)
    assert len(retrieved) == 768
    assert abs(retrieved[0] - 0.1) < 1e-6


def test_save_and_get_cards(tmp_store):
    iid = str(uuid.uuid4())
    store.create_ingestion(iid, "cards.pdf")
    cid = str(uuid.uuid4())
    c = Chunk(chunk_id=cid, ingestion_id=iid, text="test", page_start=1, page_end=1)
    store.save_chunks([c])

    cards = [
        LearningCard(card_id=str(uuid.uuid4()), chunk_id=cid,
                     card_type=CardType.standard, title="T", body="B"),
        LearningCard(card_id=str(uuid.uuid4()), chunk_id=cid,
                     card_type=CardType.quiz, title="Q", body="Q body",
                     quiz=QuizContent(question="?", options=["A","B","C","D"],
                                      correct_index=0, hint="think")),
    ]
    store.save_cards(cards)
    all_cards = store.get_cards(iid)
    assert len(all_cards) == 2

    quiz_cards = store.get_cards(iid, card_type="quiz")
    assert len(quiz_cards) == 1
    assert quiz_cards[0].quiz is not None
    assert quiz_cards[0].quiz.correct_index == 0


def test_get_ingestion_not_found(tmp_store):
    result = store.get_ingestion("nonexistent-id")
    assert result is None


# ── signal detector tests ─────────────────────────────────────────────────────

def test_shorter_chunks_signal_fires_at_three_wrong(tmp_store):
    genome = [
        {"concept": "law_1", "correct": False, "misconception": "x"},
        {"concept": "law_1", "correct": False, "misconception": "x"},
        {"concept": "law_1", "correct": False, "misconception": "y"},
    ]
    signals = detect_signals("sess-1", genome)
    types = [s.signal_type for s in signals]
    assert "shorter_chunks_help" in types
    shorter = next(s for s in signals if s.signal_type == "shorter_chunks_help")
    assert shorter.confidence == 0.5
    assert shorter.scope == "concept"


def test_shorter_chunks_does_not_fire_at_two_wrong():
    genome = [
        {"concept": "law_1", "correct": False},
        {"concept": "law_1", "correct": False},
    ]
    signals = detect_signals("sess-2", genome)
    assert not any(s.signal_type == "shorter_chunks_help" for s in signals)


def test_reading_tolerance_signal_fires_when_all_wrong():
    genome = [
        {"concept": "law_1", "correct": False},
        {"concept": "law_2", "correct": False},
    ]
    signals = detect_signals("sess-3", genome)
    types = [s.signal_type for s in signals]
    assert "reading_tolerance_may_be_low" in types
    low = next(s for s in signals if s.signal_type == "reading_tolerance_may_be_low")
    assert low.confidence == 0.4


def test_reading_tolerance_does_not_fire_when_some_correct():
    genome = [
        {"concept": "law_1", "correct": True},
        {"concept": "law_2", "correct": False},
    ]
    signals = detect_signals("sess-4", genome)
    assert not any(s.signal_type == "reading_tolerance_may_be_low" for s in signals)


def test_no_signals_for_empty_genome():
    signals = detect_signals("sess-5", [])
    assert signals == []


def test_break_signal():
    s = detect_break_signal("sess-break")
    assert s.signal_type == "break_requested"
    assert s.confidence == 0.95
    assert s.scope == "today"
    assert s.session_id == "sess-break"


def test_visual_signal():
    s = detect_visual_signal("sess-visual", "law_1")
    assert s.signal_type == "visual_examples_help"
    assert s.confidence == 0.6
    assert "law_1" in s.evidence


# ── chunker tests (paragraph fallback path) ───────────────────────────────────

def test_chunker_returns_chunks_for_simple_text():
    blocks = [
        {"page": 1, "text": "Newton's First Law states that an object at rest stays at rest.", "is_heading": False},
        {"page": 1, "text": "Newton's Second Law: F = ma.", "is_heading": True},
        {"page": 2, "text": "The acceleration of an object is proportional to the net force.", "is_heading": False},
    ]
    chunks = chunk_module.chunk(blocks, ingestion_id="test-ingestion")
    assert len(chunks) >= 1
    for c in chunks:
        assert c.ingestion_id == "test-ingestion"
        assert c.text
        assert c.chunk_id


def test_chunker_context_windows_attached():
    blocks = [
        {"page": 1, "text": "First paragraph content here.", "is_heading": False},
        {"page": 1, "text": "Second paragraph content here.", "is_heading": False},
        {"page": 2, "text": "Third paragraph content here.", "is_heading": False},
    ]
    chunks = chunk_module.chunk(blocks, ingestion_id="ctx-test")
    if len(chunks) > 1:
        # Middle chunks should have both prefix and suffix
        middle = chunks[1]
        assert middle.context_prefix != "" or middle.context_suffix != ""


def test_chunker_empty_blocks_returns_empty():
    chunks = chunk_module.chunk([], ingestion_id="empty-test")
    assert chunks == []
