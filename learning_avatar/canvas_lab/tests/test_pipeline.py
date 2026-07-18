import json

import pytest

import db
import pipeline

VALID_STEP_JSON = json.dumps(
    {
        "content_type": "slideshow",
        "scenario_text": "A quick recap before the challenge.",
        "slides": [{"image": "bg.stadium", "caption": "Hi {{friend_name}}, remember this?"}],
        "evaluation": {
            "type": "multiple_choice",
            "question": "What is 1+1?",
            "hint": "Count on fingers.",
            "options": [{"id": "A", "text": "1"}, {"id": "B", "text": "2", "is_correct": True}],
        },
    }
)

INVALID_STEP_JSON = json.dumps(
    {
        "content_type": "interactive_scene",  # not allowed for generated lessons
        "evaluation": {"type": "multiple_choice", "question": "x?", "options": [{"id": "A", "text": "a", "is_correct": True}]},
    }
)

APPROVED_CRITIC_JSON = json.dumps(
    {"relevance_score": 95, "safety_score": 95, "decision": "APPROVED", "feedback": "Looks great."}
)

REJECTED_CRITIC_JSON = json.dumps(
    {"relevance_score": 40, "safety_score": 90, "decision": "REJECTED", "feedback": "Off-topic."}
)


class FakeLLMClient:
    model = "fake-model"

    def __init__(self, generator_responses, critic_responses=None):
        self.generator_responses = list(generator_responses)
        self.critic_responses = list(critic_responses) if critic_responses else [APPROVED_CRITIC_JSON]
        self.calls: list[tuple[str, str]] = []

    def complete(self, system: str, user: str) -> str:
        self.calls.append((system, user))
        if "pedagogical content critic" in system:
            return self.critic_responses.pop(0)
        if not self.generator_responses:
            raise AssertionError("generator called more times than expected")
        return self.generator_responses.pop(0)


class NeverCallLLMClient:
    """Used to assert a code path makes zero LLM calls (the cache-hit path)."""

    model = "should-not-be-used"

    def complete(self, system: str, user: str) -> str:
        raise AssertionError("LLM should not have been called on a cache hit")


@pytest.fixture()
def isolated_db(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "test_lessons.db")
    db.init_db()
    return db


@pytest.fixture()
def student_and_request(isolated_db):
    with db.get_conn() as conn:
        student_id = conn.execute(
            "INSERT INTO students (name, age, grade, favorite_sport, friend_names) VALUES (?, ?, ?, ?, ?)",
            ("Alex", 12, "Gr 7", "soccer", "Sam"),
        ).lastrowid
        request_id = conn.execute(
            """INSERT INTO lesson_requests
               (student_id, skill, modality, mastery_pct, prereq_threshold, negative_constraint_token, status)
               VALUES (?, ?, ?, ?, ?, ?, 'pending')""",
            (student_id, "sci.physics.forces", "Story-Based", 40.0, 80.0, None),
        ).lastrowid
    return student_id, request_id


def _status(request_id: int) -> str:
    with db.get_conn() as conn:
        row = conn.execute("SELECT status FROM lesson_requests WHERE id = ?", (request_id,)).fetchone()
        return row["status"]


def test_cache_hit_makes_zero_llm_calls(student_and_request):
    student_id, request_id = student_and_request
    cache_key = pipeline.compute_cache_key("sci.physics.forces", "Story-Based", None)

    with db.get_conn() as conn:
        conn.execute(
            """INSERT INTO generated_lessons
               (cache_key, skill, modality, content_type, payload_json, critic_status, attempt_count)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (cache_key, "sci.physics.forces", "Story-Based", "slideshow", VALID_STEP_JSON, "APPROVED", 1),
        )

    pipeline.run(request_id, client=NeverCallLLMClient())

    assert _status(request_id) == "ready"
    lesson = pipeline.get_ready_lesson(request_id)
    assert lesson["content_type"] == "slideshow"
    # personalization overlay applied even on a cache hit
    assert "Sam" in lesson["slides"][0]["caption"]


def test_successful_generation_stores_lesson_and_marks_ready(student_and_request):
    student_id, request_id = student_and_request
    client = FakeLLMClient(generator_responses=[VALID_STEP_JSON])

    pipeline.run(request_id, client=client)

    assert _status(request_id) == "ready"
    with db.get_conn() as conn:
        row = conn.execute("SELECT * FROM generated_lessons").fetchone()
        assert row is not None
        assert row["critic_status"] == "APPROVED"
        assert row["attempt_count"] == 1

        trace_rows = conn.execute("SELECT role FROM llm_call_trace WHERE request_id = ?", (request_id,)).fetchall()
        roles = sorted(r["role"] for r in trace_rows)
        assert roles == ["lesson_critic", "lesson_generator"]


def test_validator_failure_triggers_retry_with_feedback(student_and_request):
    student_id, request_id = student_and_request
    client = FakeLLMClient(generator_responses=[INVALID_STEP_JSON, VALID_STEP_JSON])

    pipeline.run(request_id, client=client)

    assert _status(request_id) == "ready"
    # generator called twice (attempt 1 invalid, attempt 2 valid); the second
    # generator call's user prompt should carry feedback from the first failure
    generator_calls = [c for c in client.calls if "lesson-content generator" in c[0]]
    assert len(generator_calls) == 2
    assert "previous attempt was rejected" in generator_calls[1][1]


def test_critic_rejection_triggers_retry(student_and_request):
    student_id, request_id = student_and_request
    client = FakeLLMClient(
        generator_responses=[VALID_STEP_JSON, VALID_STEP_JSON],
        critic_responses=[REJECTED_CRITIC_JSON, APPROVED_CRITIC_JSON],
    )

    pipeline.run(request_id, client=client)

    assert _status(request_id) == "ready"
    with db.get_conn() as conn:
        row = conn.execute("SELECT * FROM generated_lessons").fetchone()
        assert row["attempt_count"] == 2


def test_exhausting_all_attempts_marks_failed(student_and_request):
    student_id, request_id = student_and_request
    client = FakeLLMClient(generator_responses=[INVALID_STEP_JSON] * 3)

    pipeline.run(request_id, client=client)

    assert _status(request_id) == "failed"
    with db.get_conn() as conn:
        row = conn.execute("SELECT failure_reason FROM lesson_requests WHERE id = ?", (request_id,)).fetchone()
        assert "exhausted 3 attempts" in row["failure_reason"]
        assert conn.execute("SELECT COUNT(*) AS n FROM generated_lessons").fetchone()["n"] == 0
