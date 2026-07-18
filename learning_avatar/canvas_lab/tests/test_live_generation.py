"""Live LLM generation test — calls the real configured LLM, not a fake
client. Deliberately kept separate from test_pipeline.py (which never makes
a real network call) so the default `uv run pytest` stays fast, free, and
credential-free: this file is automatically skipped unless LLM_BASE_URL /
LLM_API_KEY / LLM_MODEL are all set.

Run it explicitly once you have those set:

    uv run pytest tests/test_live_generation.py -v -s

Add --clear-cache to force a fresh generation instead of serving whatever's
already cached for this (skill, modality) from a previous run:

    uv run pytest tests/test_live_generation.py -v -s --clear-cache

-s is important — it disables pytest's output capture so you actually see
the generated lesson printed, not just a pass/fail line.
"""

import json
import os

import pytest

import db
import pipeline

pytestmark = pytest.mark.skipif(
    not (os.environ.get("LLM_BASE_URL") and os.environ.get("LLM_API_KEY") and os.environ.get("LLM_MODEL")),
    reason="LLM_BASE_URL/LLM_API_KEY/LLM_MODEL not set — skipping live LLM test",
)

SKILL = "Use a pizza slices example to explain vector offsets?"
MODALITY = "Flipped Analogy"


def test_live_pizza_slices_vector_offset_generation(request):
    clear_cache = request.config.getoption("--clear-cache")
    cache_key = pipeline.compute_cache_key(SKILL, MODALITY, None)

    if clear_cache:
        with db.get_conn() as conn:
            deleted = conn.execute(
                "DELETE FROM generated_lessons WHERE cache_key = ?", (cache_key,)
            ).rowcount
        print(f"\n--clear-cache: removed {deleted} cached row(s) for cache_key={cache_key!r}")

    with db.get_conn() as conn:
        student_id = conn.execute(
            "INSERT INTO students (name, age, grade, favorite_sport, friend_names) VALUES (?, ?, ?, ?, ?)",
            ("TestStudent", 12, "Gr 7", "soccer", "Sam"),
        ).lastrowid
        request_id = conn.execute(
            """INSERT INTO lesson_requests (student_id, skill, modality, status)
               VALUES (?, ?, ?, 'pending')""",
            (student_id, SKILL, MODALITY),
        ).lastrowid

    # Runs synchronously here (no BackgroundTasks involved) — real LLM calls
    # happen inline, so by the time this returns the request is ready/failed.
    pipeline.run(request_id)

    with db.get_conn() as conn:
        req = conn.execute("SELECT * FROM lesson_requests WHERE id = ?", (request_id,)).fetchone()
        trace_rows = conn.execute(
            "SELECT role, status, latency_ms FROM llm_call_trace WHERE request_id = ?", (request_id,)
        ).fetchall()

    print("\n" + "=" * 70)
    print(f"request_id={request_id}  cache_key={cache_key!r}")
    print(f"status={req['status']}")
    for row in trace_rows:
        print(f"  llm_call_trace: role={row['role']} status={row['status']} latency_ms={row['latency_ms']}")
    if req["status"] == "failed":
        print(f"failure_reason={req['failure_reason']}")
    print("=" * 70)

    assert req["status"] == "ready", f"generation failed: {req['failure_reason']}"

    lesson = pipeline.get_ready_lesson(request_id)
    print(json.dumps(lesson, indent=2, ensure_ascii=False))
    print("=" * 70)

    assert lesson["content_type"] in ("slideshow", "story")
    assert lesson["evaluation"]["type"] in ("multiple_choice", "free_text", "dropdown")
