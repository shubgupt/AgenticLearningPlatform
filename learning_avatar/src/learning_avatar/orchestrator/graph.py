"""
The LangGraph Orchestration Layer (plan doc section 2.1.1), for real, for
one narrow slice: generating a task hint. Router -> Policy -> LabModel-
Worker -> LabModel-Critic -> END -- a straight line today because this
graph only handles one intent so far. See nodes.py for where branching
logic (conditional edges keyed on `intent`/`policy_verdict`) would go once
this grows beyond hints into lesson generation, assessment, etc.

IMPORTANT -- verification status: this was written with no network access
to `uv sync` the new `langgraph` dependency, so it has only been checked
with `python -m py_compile` and by reading the LangGraph API docs, not
actually run. Run `uv sync` and exercise POST /api/session/<id>/hint
yourself before trusting this end to end -- see README "Verifying the new
orchestrator slice."
"""
from __future__ import annotations
from typing import Any, Dict, List, TypedDict

from langgraph.graph import END, START, StateGraph

from learning_avatar.orchestrator import nodes


class HintGraphState(TypedDict, total=False):
    task_number: int
    task_question: str
    grade_band: str
    attention_score: int
    motivation_score: int
    static_hint_fallback: str
    intent: str
    policy_verdict: str
    hint_text: str
    critic_problems: List[str]
    source: str


def build_hint_graph():
    graph = StateGraph(HintGraphState)
    graph.add_node("router", nodes.router_node)
    graph.add_node("policy", nodes.policy_node)
    graph.add_node("worker", nodes.worker_node)
    graph.add_node("critic", nodes.critic_node)

    graph.add_edge(START, "router")
    graph.add_edge("router", "policy")
    graph.add_edge("policy", "worker")
    graph.add_edge("worker", "critic")
    graph.add_edge("critic", END)

    return graph.compile()


# Compiled once at import time -- a compiled LangGraph graph is stateless
# and reusable across requests; only the per-call `state` dict and `config`
# (which carries the request-scoped LLMClient) change between calls.
hint_graph = build_hint_graph()


async def run_hint_orchestrator(
    llm: Any,
    model: str,
    task_number: int,
    task_question: str,
    grade_band: str,
    attention_score: int,
    motivation_score: int,
    static_hint_fallback: str,
) -> Dict[str, Any]:
    initial_state: HintGraphState = {
        "task_number": task_number,
        "task_question": task_question,
        "grade_band": grade_band,
        "attention_score": attention_score,
        "motivation_score": motivation_score,
        "static_hint_fallback": static_hint_fallback,
    }
    return await hint_graph.ainvoke(
        initial_state,
        config={"configurable": {"llm": llm, "model": model}},
    )
