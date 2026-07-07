"""
Tests the Root Agent's orchestration logic in isolation from the Teaching
Agent entirely -- a different mocking boundary than test_teaching_agent.py.
There, we mocked the MCP client (one layer down). Here, we mock
teaching_agent.generate_lesson itself (one layer up), because what we're
testing is "does Root Agent's critic-and-retry logic behave correctly,"
which shouldn't care how the Teaching Agent produced its answer.

This is the "scenario loops that exercise the full reasoning pipeline
without hitting external services" goal in miniature: two agents, chained,
zero network calls, deterministic.
"""
import pytest

from learning_avatar.agents import root_agent, teaching_agent
from learning_avatar.core.schemas import LessonResponse, LessonScreen


def _valid_record(**overrides) -> LessonScreen:
    base = dict(
        id="test_record", subject="physics", topic="newtons_laws_of_motion",
        concept="law_1_inertia", gradeBand="grade5", theme="soccer",
        hook={"kicker": "k", "text": "t", "options": ["go"]},
        sandbox={"kicker": "k", "prompt": "p", "scene_ref": "rolling_object_scene", "token": "⚽", "options": ["a"]},
        concept_screen={"kicker": "k", "text_by_grade": {"grade5": "text"}},
        diagnostic={
            "kicker": "k", "prompt_by_grade": {"grade5": "q"},
            "options": [
                {"label": "right", "correct": True, "value": "a"},
                {"label": "wrong", "correct": False, "value": "b", "misconception": "m1"},
            ],
        },
        mistake_genome={"m1": {"message": "msg", "recommended_support": ["show_picture"]}},
    )
    base.update(overrides)
    return LessonScreen.model_validate(base)


@pytest.mark.asyncio
async def test_valid_lesson_passes_critic_on_first_try(monkeypatch, session, ctx_grade5_soccer_law1, mock_llm):
    async def fake_generate_lesson(ctx, llm):
        return LessonResponse(record=_valid_record(), content_source="library")

    monkeypatch.setattr(teaching_agent, "generate_lesson", fake_generate_lesson)

    result = await root_agent.get_lesson(session, ctx_grade5_soccer_law1, mock_llm)

    assert result.content_source == "library"
    assert session.xp == 150


@pytest.mark.asyncio
async def test_critic_rejects_and_retries_once_then_raises(monkeypatch, session, ctx_grade5_soccer_law1, mock_llm):
    """A record with an incorrect option that has no matching mistake_genome
    entry should fail the critic check every time -- proving the retry
    doesn't just get lucky twice, and that a persistent problem surfaces as
    CriticRejectedError rather than reaching the student."""
    broken = _valid_record(mistake_genome={})  # misconception "m1" now dangling

    call_count = {"value": 0}

    async def fake_generate_lesson(ctx, llm):
        call_count["value"] += 1
        return LessonResponse(record=broken, content_source="library")

    monkeypatch.setattr(teaching_agent, "generate_lesson", fake_generate_lesson)

    with pytest.raises(root_agent.CriticRejectedError):
        await root_agent.get_lesson(session, ctx_grade5_soccer_law1, mock_llm)

    assert call_count["value"] == 2  # first attempt + exactly one retry
