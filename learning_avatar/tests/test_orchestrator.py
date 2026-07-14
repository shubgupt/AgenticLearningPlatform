"""
Closes another Phase 2 coverage gap: orchestrator/ had zero tests.

Two tiers here, deliberately separated:
1. Node functions (orchestrator/nodes.py) tested directly -- these don't
   import langgraph at all, so they run regardless of whether that
   dependency is installed.
2. The compiled graph (orchestrator/graph.py) tested through
   run_hint_orchestrator -- this DOES need langgraph installed
   (`uv sync --extra dev`, see README). Skipped cleanly if it isn't, rather
   than failing the whole test file's collection.
"""
import pytest

from learning_avatar.orchestrator import nodes


# --- Node functions, no langgraph dependency ---------------------------------

@pytest.mark.asyncio
async def test_router_node_always_classifies_hint():
    """Documents current (stub) behavior: every request is treated as a
    hint request, since that's the only intent this graph implements yet.
    See nodes.py's TODO -- this assertion should start failing on purpose
    once real intent classification is added, as a reminder to update it."""
    result = await nodes.router_node({}, {})
    assert result == {"intent": "Hint"}


@pytest.mark.asyncio
async def test_policy_node_always_passes():
    """Same as above -- documents the stub, not a real safety guarantee."""
    result = await nodes.policy_node({}, {})
    assert result == {"policy_verdict": "Fully Appropriate"}


@pytest.mark.asyncio
async def test_critic_node_accepts_a_good_hint():
    state = {"hint_text": "Think about which force is bigger.", "static_hint_fallback": "fallback text"}
    result = await nodes.critic_node(state, {})
    assert result["critic_problems"] == []
    assert result["source"] == "orchestrator"


@pytest.mark.asyncio
async def test_critic_node_falls_back_on_empty_hint():
    """If the Worker produces nothing usable, the Critic should reject it
    and the node should hand back the static fallback, not the empty
    string -- this is the exact failure mode web/main.py's /hint route
    relies on labmodel.critic to catch before a response ever reaches the
    student."""
    state = {"hint_text": "", "static_hint_fallback": "Think about a tug-of-war."}
    result = await nodes.critic_node(state, {})
    assert result["source"] == "static"
    assert result["hint_text"] == "Think about a tug-of-war."
    assert result["critic_problems"] == ["empty hint"]


@pytest.mark.asyncio
async def test_worker_node_calls_labmodel_worker(mock_llm):
    state = {
        "task_question": "What happens when two equal forces act from opposite sides?",
        "grade_band": "Elementary",
        "attention_score": 7,
        "motivation_score": 7,
        "static_hint_fallback": "Think about a tug-of-war.",
    }
    config = {"configurable": {"llm": mock_llm, "model": "mock-model"}}
    result = await nodes.worker_node(state, config)
    assert "hint_text" in result
    assert result["hint_text"].strip() != ""


# --- Compiled graph, requires langgraph ---------------------------------

langgraph = pytest.importorskip(
    "langgraph",
    reason="langgraph isn't installed in this environment -- run `uv sync` to pick it up (see README).",
)


@pytest.mark.asyncio
async def test_run_hint_orchestrator_end_to_end(mock_llm):
    """The one real vertical slice, exercised through the actual compiled
    LangGraph graph rather than by calling nodes directly -- this is the
    test that would catch a graph-wiring mistake (wrong edge order, a node
    key typo) that unit-testing nodes.py in isolation cannot."""
    from learning_avatar.orchestrator.graph import run_hint_orchestrator

    result = await run_hint_orchestrator(
        llm=mock_llm,
        model="mock-model",
        task_number=1,
        task_question="What happens when two equal forces act from opposite sides?",
        grade_band="Elementary",
        attention_score=7,
        motivation_score=7,
        static_hint_fallback="Think about a tug-of-war.",
    )
    assert result["source"] in ("orchestrator", "static")
    assert result["hint_text"].strip() != ""
    assert result["critic_problems"] == []
