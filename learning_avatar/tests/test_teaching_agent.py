"""
Exercises the Teaching Agent's two paths without touching a real model or a
real network call to the MCP server (which, in CI, wouldn't be running).

Note the mocking boundary: we mock the MCP *client* functions
(content_retrieval.fetch_lesson_record / fetch_concept_definition), not the
MCP server itself. That mirrors how you'd test this in a real project --
you trust the protocol library, you fake the specific tool responses your
code depends on.
"""
import pytest

from learning_avatar.agents import teaching_agent
from learning_avatar.mcp import client as content_retrieval


@pytest.mark.asyncio
async def test_library_hit_skips_the_llm_entirely(monkeypatch, ctx_grade5_soccer_law1, mock_llm):
    """When the MCP server has a matching record, the LLM should never be
    called -- this is the cost-control behavior the whole design exists
    for, so it's worth asserting directly."""
    llm_was_called = {"value": False}

    async def fake_complete(*args, **kwargs):
        llm_was_called["value"] = True
        raise AssertionError("LLM should not be called on a library hit")

    monkeypatch.setattr(mock_llm, "complete", fake_complete)

    result = await teaching_agent.generate_lesson(ctx_grade5_soccer_law1, mock_llm)

    assert result.content_source == "library"
    assert result.record.concept == "law_1_inertia"
    assert result.record.theme == "soccer"
    assert not llm_was_called["value"]


@pytest.mark.asyncio
async def test_library_miss_falls_through_to_generation(monkeypatch, ctx_uncovered_combo, mock_llm):
    """When nothing matches, the agent should call the LLM and return
    schema-valid content built from the mock's canned response."""
    async def fake_fetch_lesson_record(**kwargs):
        return None

    async def fake_fetch_concept_definition(concept_id):
        return None

    monkeypatch.setattr(content_retrieval, "fetch_lesson_record", fake_fetch_lesson_record)
    monkeypatch.setattr(content_retrieval, "fetch_concept_definition", fake_fetch_concept_definition)

    result = await teaching_agent.generate_lesson(ctx_uncovered_combo, mock_llm)

    assert result.content_source == "generated"
    assert result.record.concept == "law_4_not_a_real_law"


@pytest.mark.asyncio
async def test_malformed_llm_output_raises_teaching_agent_error(monkeypatch, ctx_uncovered_combo, mock_llm):
    """If the model (or, more likely while you're developing, your own
    prompt) produces something that doesn't match LessonScreen, the agent
    should fail loudly with a typed error -- not hand a broken screen up
    to the Root Agent."""
    async def fake_fetch_lesson_record(**kwargs):
        return None

    async def fake_fetch_concept_definition(concept_id):
        return None

    async def broken_complete(*args, **kwargs):
        return "this is not json"

    monkeypatch.setattr(content_retrieval, "fetch_lesson_record", fake_fetch_lesson_record)
    monkeypatch.setattr(content_retrieval, "fetch_concept_definition", fake_fetch_concept_definition)
    monkeypatch.setattr(mock_llm, "complete", broken_complete)

    with pytest.raises(teaching_agent.TeachingAgentError):
        await teaching_agent.generate_lesson(ctx_uncovered_combo, mock_llm)
