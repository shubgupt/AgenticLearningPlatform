"""
AgentState -- the LangGraph orchestrator's central state contract, per the
plan doc's section 3.1. This is deliberately a *separate* model from
SessionState (schemas.py), not a replacement for it:

- SessionState is what the existing FastAPI routes / SQLite store / Root
  Agent already use for the working lesson pipeline (session.py, tests,
  the v4 frontend). It stays untouched.
- AgentState is the state object that flows through orchestrator/graph.py's
  LangGraph nodes for the new "hint" vertical slice. It's scoped down from
  the plan doc's full version to just the fields that slice actually reads
  or writes -- the rest (score_xp, attempt_history, generated_slides, etc.)
  are included as declared-but-currently-unused, matching the plan's shape,
  so extending the graph later (assessment, full lesson generation via
  LangGraph) doesn't require a schema migration, just wiring a node that
  reads/writes a field that was already sitting here.

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
