"""
Phase 7: Conservative learner signal detection from session state.

Rules (all cautious; no diagnoses; no protected traits):
  - 3+ wrong answers on one concept  → shorter_chunks_help (confidence 0.5)
  - Break button event               → break_requested      (confidence 0.95)
  - Correct on analogy after wrong   → visual_examples_help (confidence 0.6)
  - All concepts attempted wrong     → reading_tolerance_may_be_low (0.4)

Signals are scoped to "session" unless a concept-specific pattern is detected.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from .schemas import LearnerSignal


def detect_signals(session_id: str, mistake_genome: list[dict]) -> list[LearnerSignal]:
    """
    Analyze the session's mistakeGenome list and return any supported signals.
    mistake_genome items: {"concept": str, "correct": bool, "misconception": str|None}
    """
    signals: list[LearnerSignal] = []
    now = datetime.now(timezone.utc).isoformat()

    # Count wrong answers per concept
    wrong_per_concept: dict[str, int] = {}
    correct_per_concept: dict[str, int] = {}
    for entry in mistake_genome:
        concept = entry.get("concept", "unknown")
        if entry.get("correct"):
            correct_per_concept[concept] = correct_per_concept.get(concept, 0) + 1
        else:
            wrong_per_concept[concept] = wrong_per_concept.get(concept, 0) + 1

    # Rule 1: 3+ wrong on a single concept → shorter_chunks_help
    for concept, count in wrong_per_concept.items():
        if count >= 3:
            signals.append(LearnerSignal(
                signal_id=str(uuid.uuid4()),
                session_id=session_id,
                signal_type="shorter_chunks_help",
                confidence=0.5,
                scope="concept",
                evidence=f"{count} wrong answers on concept '{concept}'",
                created_at=now,
            ))

    # Rule 2: All concepts attempted had at least one wrong → reading_tolerance_may_be_low
    all_wrong_concepts = set(wrong_per_concept.keys())
    all_correct_concepts = set(correct_per_concept.keys())
    if all_wrong_concepts and not (all_correct_concepts - all_wrong_concepts):
        signals.append(LearnerSignal(
            signal_id=str(uuid.uuid4()),
            session_id=session_id,
            signal_type="reading_tolerance_may_be_low",
            confidence=0.4,
            scope="session",
            evidence="All attempted concepts had at least one incorrect answer",
            created_at=now,
        ))

    return signals


def detect_break_signal(session_id: str) -> LearnerSignal:
    """Call this when the student explicitly clicks a break button."""
    return LearnerSignal(
        signal_id=str(uuid.uuid4()),
        session_id=session_id,
        signal_type="break_requested",
        confidence=0.95,
        scope="today",
        evidence="Student clicked break button",
        created_at=datetime.now(timezone.utc).isoformat(),
    )


def detect_visual_signal(session_id: str, concept: str) -> LearnerSignal:
    """
    Call this when a student gets a correct answer on an analogy card
    immediately after an incorrect answer on a standard card for the same concept.
    """
    return LearnerSignal(
        signal_id=str(uuid.uuid4()),
        session_id=session_id,
        signal_type="visual_examples_help",
        confidence=0.6,
        scope="concept",
        evidence=f"Correct on analogy card after wrong on standard card for '{concept}'",
        created_at=datetime.now(timezone.utc).isoformat(),
    )
