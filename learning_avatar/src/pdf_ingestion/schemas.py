from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class IngestionRecord(BaseModel):
    ingestion_id: str
    filename: str
    page_count: int = 0
    status: Literal["pending", "done", "failed"]
    error: str | None = None
    created_at: str


class Chunk(BaseModel):
    chunk_id: str
    ingestion_id: str
    text: str
    context_prefix: str = ""
    context_suffix: str = ""
    page_start: int = 1
    page_end: int = 1
    heading_path: list[str] = Field(default_factory=list)


class CardType(str, Enum):
    standard = "standard"
    simplified = "simplified"
    analogy = "analogy"
    hint = "hint"
    quiz = "quiz"
    teacher_note = "teacher_note"
    recap = "recap"


class QuizContent(BaseModel):
    question: str
    options: list[str]
    correct_index: int
    hint: str


class LearningCard(BaseModel):
    card_id: str
    chunk_id: str
    card_type: CardType
    title: str
    body: str
    quiz: QuizContent | None = None


class ChunkLink(BaseModel):
    link_id: str
    source_chunk_id: str
    target_id: str
    target_type: Literal["chunk", "video_artifact"]
    relation: Literal[
        "same_concept", "prerequisite", "supports",
        "misconception_match", "matches_video"
    ]
    confidence: float
    evidence: str


class LearnerSignal(BaseModel):
    signal_id: str
    session_id: str
    signal_type: Literal[
        "reading_tolerance_may_be_low", "visual_examples_help",
        "shorter_chunks_help", "needs_more_time_today", "break_requested"
    ]
    confidence: float
    scope: Literal["session", "concept", "today"]
    evidence: str
    created_at: str


class PipelineResult(BaseModel):
    ingestion_id: str
    chunk_count: int
    card_count: int
    link_count: int
