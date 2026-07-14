"""
Closes a real gap: Phase 2's labmodel/ (Worker + Critic) had zero test
coverage until now, despite being the one piece of the new architecture
that's actually wired end-to-end. Same mocking boundary discipline as
test_teaching_agent.py -- mock_llm (from conftest.py) costs nothing and
returns deterministic output.
"""
import pytest

from learning_avatar.labmodel import critic, worker


# --- LabModel-Critic (pure functions, no mocking needed) --------------------

def test_review_hint_passes_normal_hint():
    assert critic.review_hint("Think about which force is bigger.") == []


def test_review_hint_rejects_empty():
    problems = critic.review_hint("")
    assert problems == ["empty hint"]


def test_review_hint_rejects_whitespace_only():
    problems = critic.review_hint("   \n\t  ")
    assert problems == ["empty hint"]


def test_review_hint_rejects_too_long():
    problems = critic.review_hint("x" * (critic.MAX_HINT_CHARS + 1))
    assert len(problems) == 1
    assert "too long" in problems[0]


# --- LabModel-Worker (uses mock_llm from conftest.py) ------------------------

@pytest.mark.asyncio
async def test_generate_hint_returns_nonempty_text(mock_llm):
    """With MockLLMClient, this exercises the "generic completion" branch
    added to llm_client.py specifically so hint requests don't get a fake
    LessonScreen JSON blob back (see llm_client.py's _mock_generic_completion)."""
    result = await worker.generate_hint(
        llm=mock_llm,
        model="mock-model",
        task_question="What happens when two equal forces act from opposite sides?",
        grade_band="Elementary",
        attention_score=7,
        motivation_score=7,
        static_hint_fallback="Think about a tug-of-war.",
    )
    assert isinstance(result, str)
    assert result.strip() != ""
    # The mock's generic-completion path should never accidentally return
    # the lesson-JSON mock shape -- that would indicate the request/response
    # dispatch in MockLLMClient.complete() regressed.
    assert not result.strip().startswith("{")
