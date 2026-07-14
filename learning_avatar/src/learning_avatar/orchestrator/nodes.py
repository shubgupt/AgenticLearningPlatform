"""
Node functions for the hint orchestration graph (orchestrator/graph.py).
Each node takes the current graph state (a graph.HintGraphState dict) and a
LangGraph RunnableConfig, and returns a dict of fields to merge into state --
the standard LangGraph node contract.

Real work happens in worker_node (calls labmodel.worker) and critic_node
(calls labmodel.critic). router_node and policy_node are intentionally thin
here: this graph only ever handles hint requests today, so there's nothing
for them to route/gate yet. They're kept as real nodes in the graph -- not
skipped -- so the shape already matches where Router Agent / Policy Engine
sit in the plan doc (section 4.1), ready to grow real logic (multi-intent
routing, actual content-safety classification) without restructuring the
graph later.
"""
from __future__ import annotations
from typing import Any, Dict

from learning_avatar.labmodel import critic, worker


async def router_node(state: Dict[str, Any], config: dict) -> Dict[str, Any]:
    # TODO(plan 4.1): classify into Instruction/Hint/Assessment/
    # Deconstruction/Clarification/Safe Redirect. Every request this graph
    # handles today is already a hint request by construction (see
    # web/main.py's /hint route) -- this is a placeholder assignment, not
    # real classification.
    return {"intent": "Hint"}


async def policy_node(state: Dict[str, Any], config: dict) -> Dict[str, Any]:
    # TODO(plan 4.1): real content-safety gate (Fully Appropriate / Needs
    # Simplification / Needs Context Restriction / Requires Adult Context /
    # Not Appropriate). A hint for a physics forces task has no realistic
    # safety surface, so this always passes -- a stub for something that
    # genuinely doesn't need checking yet, not a shortcut on something that did.
    return {"policy_verdict": "Fully Appropriate"}


async def worker_node(state: Dict[str, Any], config: dict) -> Dict[str, Any]:
    cfg = config.get("configurable", {})
    hint_text = await worker.generate_hint(
        llm=cfg["llm"],
        model=cfg["model"],
        task_question=state["task_question"],
        grade_band=state["grade_band"],
        attention_score=state["attention_score"],
        motivation_score=state["motivation_score"],
        static_hint_fallback=state["static_hint_fallback"],
    )
    return {"hint_text": hint_text}


async def critic_node(state: Dict[str, Any], config: dict) -> Dict[str, Any]:
    problems = critic.review_hint(state.get("hint_text", ""))
    if problems:
        # Critic rejected the Worker's draft -- degrade to the hand-written
        # hint rather than show the student something broken or oversized.
        return {"hint_text": state["static_hint_fallback"], "critic_problems": problems, "source": "static"}
    return {"critic_problems": [], "source": "orchestrator"}
