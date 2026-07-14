"""
AgentState -- modeled on the plan doc's section 3.1 central state contract.

CURRENTLY UNUSED. This was written as "the state object that flows through
orchestrator/graph.py's LangGraph nodes," but graph.py actually defines and
uses its own separate `HintGraphState` TypedDict instead (LangGraph's
StateGraph needs a TypedDict/dataclass-like schema, and this is a Pydantic
BaseModel). Nothing in this codebase imports AgentState. Keeping it around
as a faithful, unused reference to the plan doc's shape was a mistake to
present as "the" state contract without wiring it in -- either delete this
file, or make it true by having graph.py convert to/from it at the
orchestrator's boundary (HintGraphState stays the internal LangGraph
representation, AgentState becomes the public in/out shape). Not resolved
here; flagged so it doesn't get mistaken for live code.

SessionState (schemas.py) is the model that's actually used everywhere --
FastAPI routes, SQLite store, Root Agent, the v4 frontend, and the new
/hint route via session.student_profile.

Field-for-field mapped to the plan doc's `state.py` where possible; a few
plan fields (trace_parent_id/OpenTelemetry, rl_reward_metric) are kept as
plain placeholders since the tracing/RL machinery they'd feed doesn't exist
yet in this scaffold.
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class AgentState(BaseModel):
    # --- 1. Core session identity ---
    user_id: str = "anonymous"
    session_id: str
    character_hook: str = "none"
    grade_band: str = "Elementary"
    current_subject: str = "physics"
    current_mode: str = "hint"  # only mode this slice's graph implements so far
    current_index: int = 0

    # --- 2. Telemetry (populated from StudentProfile at request time) ---
    focus_loss_count: int = 0
    click_latency_ms: int = 0
    attention_score: int = Field(7, ge=0, le=10)
    motivation_score: int = Field(7, ge=0, le=10)
    score_xp: int = 0
    attempt_history: Dict[int, int] = Field(default_factory=dict)
    rl_reward_metric: float = 0.0

    # --- 3. Generative payloads this slice actually reads/writes ---
    active_task: Dict[str, Any] = Field(default_factory=dict)
    evaluation_feedback: Dict[str, Any] = Field(default_factory=dict)

    # --- Declared per the plan doc, not yet produced by any node here ---
    generated_slides: List[Dict[str, Any]] = Field(default_factory=list)
    trace_parent_id: Optional[str] = None
