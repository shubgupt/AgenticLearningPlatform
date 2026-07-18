"""Orchestrates the LLM-generated-lesson pipeline: cache check -> generate ->
deterministic validate -> LLM critique -> retry (max 3) -> store -> mark the
lesson_requests row ready/failed. See docs/llm-lesson-generation-spec.md.

Designed to run as a FastAPI BackgroundTask via main.py's
POST /api/lesson-requests route, but `run()` takes an injectable LLMClient
so it's directly unit-testable against a fake (see tests/test_pipeline.py).
"""

import json
import logging
import uuid

import critic
import db
import generator
import validator
from llm_client import LLMClient, OpenAICompatibleClient

logger = logging.getLogger("pipeline")

MAX_ATTEMPTS = 3


def compute_cache_key(skill: str, modality: str, negative_constraint_token: str | None) -> str:
    # Deliberately excludes student-specific personalization — see spec
    # section 5: caching on what constrains *content*, not who's asking.
    return f"{skill}::{modality}::{negative_constraint_token or ''}"


def _apply_personalization_overlay(payload_json: str, student: dict) -> str:
    text = payload_json
    text = text.replace("{{favorite_sport}}", student.get("favorite_sport") or "something you enjoy")
    text = text.replace("{{friend_name}}", student.get("friend_names") or "a friend")
    return text


def _get_asset_manifest() -> dict:
    # Deferred import breaks the circular import: main.py imports pipeline
    # at module load to wire routes, so pipeline can't import main at module
    # load too. By the time run() actually executes (as a background task
    # after app startup), main is fully initialized, so this is safe.
    from main import LESSON_PAYLOAD

    return LESSON_PAYLOAD["asset_manifest"]


def run(request_id: int, client: LLMClient | None = None) -> None:
    """Public entrypoint — runs as a FastAPI BackgroundTask, so nothing here
    can be allowed to leave a request stuck at 'pending'/'generating' with no
    diagnosis. Any unexpected exception (e.g. missing LLM_* env vars) is
    caught here and recorded as a 'failed' status with the error message,
    rather than silently escaping the background task."""
    try:
        _run_inner(request_id, client)
    except Exception as exc:  # noqa: BLE001 - intentionally broad: this is the last line of defense
        logger.exception("request %s crashed", request_id)
        with db.get_conn() as conn:
            conn.execute(
                "UPDATE lesson_requests SET status = 'failed', failure_reason = ? WHERE id = ?",
                (f"{type(exc).__name__}: {exc}", request_id),
            )


def _run_inner(request_id: int, client: LLMClient | None) -> None:
    with db.get_conn() as conn:
        req = conn.execute("SELECT * FROM lesson_requests WHERE id = ?", (request_id,)).fetchone()
        if req is None:
            logger.error("lesson_requests row %s not found", request_id)
            return
        student = conn.execute("SELECT * FROM students WHERE id = ?", (req["student_id"],)).fetchone()

    skill = req["skill"]
    modality = req["modality"]
    negative_constraint_token = req["negative_constraint_token"]
    cache_key = compute_cache_key(skill, modality, negative_constraint_token)

    with db.get_conn() as conn:
        cached = conn.execute(
            "SELECT * FROM generated_lessons WHERE cache_key = ? AND is_deleted = 0",
            (cache_key,),
        ).fetchone()

    if cached is not None:
        with db.get_conn() as conn:
            conn.execute(
                "UPDATE generated_lessons SET hit_count = hit_count + 1, last_used_at = datetime('now') WHERE id = ?",
                (cached["id"],),
            )
            conn.execute("UPDATE lesson_requests SET status = 'ready' WHERE id = ?", (request_id,))
        logger.info("cache hit for request %s (cache_key=%s) — no LLM calls made", request_id, cache_key)
        return

    # Only reachable on a cache miss — a cache hit above must never require an
    # LLM client to exist, let alone be configured.
    client = client or OpenAICompatibleClient()

    with db.get_conn() as conn:
        conn.execute("UPDATE lesson_requests SET status = 'generating' WHERE id = ?", (request_id,))

    asset_manifest = _get_asset_manifest()
    trace_id = uuid.uuid4().hex
    prior_feedback: list[str] | None = None
    last_errors: list[str] = []

    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            draft = generator.generate(
                client,
                request_id=request_id,
                trace_id=trace_id,
                skill=skill,
                modality=modality,
                mastery_pct=req["mastery_pct"],
                prereq_threshold=req["prereq_threshold"],
                negative_constraint_token=negative_constraint_token,
                asset_manifest=asset_manifest,
                prior_feedback=prior_feedback,
            )
        except generator.GenerationParseError as exc:
            last_errors = [str(exc)]
            prior_feedback = last_errors
            continue

        is_valid, val_errors = validator.validate(draft, asset_manifest, negative_constraint_token)
        if not is_valid:
            last_errors = val_errors
            prior_feedback = val_errors
            continue

        try:
            verdict = critic.review(
                client,
                request_id=request_id,
                trace_id=trace_id,
                skill=skill,
                modality=modality,
                draft_step=draft,
                student_age=student["age"] if student else None,
                student_grade=student["grade"] if student else None,
                negative_constraint_token=negative_constraint_token,
            )
        except critic.CriticParseError as exc:
            last_errors = [str(exc)]
            prior_feedback = last_errors
            continue

        if verdict.get("decision") != "APPROVED":
            feedback = verdict.get("feedback", "critic rejected the draft")
            last_errors = [feedback]
            prior_feedback = [feedback]
            with db.get_conn() as conn:
                conn.execute(
                    "UPDATE lesson_requests SET failure_reason = ? WHERE id = ?",
                    (f"attempt {attempt} rejected: {feedback}", request_id),
                )
            continue

        # Approved — persist and mark ready.
        with db.get_conn() as conn:
            conn.execute(
                """INSERT INTO generated_lessons
                   (cache_key, skill, modality, negative_constraint_token, content_type,
                    payload_json, critic_status, critic_feedback, attempt_count)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    cache_key,
                    skill,
                    modality,
                    negative_constraint_token,
                    draft.get("content_type"),
                    json.dumps(draft),
                    "APPROVED",
                    verdict.get("feedback", ""),
                    attempt,
                ),
            )
            conn.execute("UPDATE lesson_requests SET status = 'ready' WHERE id = ?", (request_id,))
        logger.info("request %s generated successfully on attempt %s", request_id, attempt)
        return

    # Exhausted all attempts.
    with db.get_conn() as conn:
        conn.execute(
            "UPDATE lesson_requests SET status = 'failed', failure_reason = ? WHERE id = ?",
            (f"exhausted {MAX_ATTEMPTS} attempts; last errors: {last_errors}", request_id),
        )
    logger.warning("request %s failed after %s attempts: %s", request_id, MAX_ATTEMPTS, last_errors)


def get_ready_lesson(request_id: int) -> dict | None:
    """Returns the assembled, personalized step JSON for a ready request, or None."""
    with db.get_conn() as conn:
        req = conn.execute("SELECT * FROM lesson_requests WHERE id = ?", (request_id,)).fetchone()
        if req is None or req["status"] != "ready":
            return None
        student = conn.execute("SELECT * FROM students WHERE id = ?", (req["student_id"],)).fetchone()
        cache_key = compute_cache_key(req["skill"], req["modality"], req["negative_constraint_token"])
        lesson = conn.execute(
            "SELECT * FROM generated_lessons WHERE cache_key = ? AND is_deleted = 0",
            (cache_key,),
        ).fetchone()
        if lesson is None:
            return None

    personalized = _apply_personalization_overlay(lesson["payload_json"], dict(student) if student else {})
    return json.loads(personalized)


def get_ready_lesson_payload(request_id: int) -> dict | None:
    """Wraps get_ready_lesson()'s raw step into the same lesson-shaped
    payload /api/lessons/load returns, so the frontend's job is just
    "fetch, set this.lesson" — identical to the static-curriculum path,
    no special-casing in the render engine for generated content."""
    step = get_ready_lesson(request_id)
    if step is None:
        return None

    # Deferred import — see _get_asset_manifest()'s comment: main.py imports
    # pipeline at module load to wire routes, so pipeline can't import main
    # at module load too without a circular import.
    from main import LESSON_PAYLOAD

    return {
        "lesson_id": f"generated-{request_id}",
        "subject": "Generated",
        "topic": (step.get("scenario_text") or "Custom Lesson")[:60],
        "total_steps": 1,
        "user_profile": LESSON_PAYLOAD["user_profile"],
        "character_library": LESSON_PAYLOAD["character_library"],
        "asset_manifest": LESSON_PAYLOAD["asset_manifest"],
        "steps": [step],
    }
