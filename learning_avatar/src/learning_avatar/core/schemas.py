"""
Pydantic models. These are the TypeScript-interfaces-but-for-Python version of
the JSON contracts already written down in app/agents/prompts/ui_prompt.md.

Keeping these as real Pydantic models (not just dicts) is what gives you two
things a plain-dict version never would:
  1. FastAPI auto-validates every request/response against these shapes.
  2. Any agent that returns something malformed fails loudly, at the boundary,
     instead of silently reaching the browser broken.
"""
from __future__ import annotations
from typing import Literal, Optional
from pydantic import BaseModel, Field


# --- Shared subject/content addressing -------------------------------------

class SubjectContext(BaseModel):
    subject: str = "physics"
    topic: str = "newtons_laws_of_motion"
    concept: str
    gradeBand: Literal["grade5", "high"]
    theme: Literal["soccer", "creative_play"]


# --- LessonScreen (Teaching Agent output) -----------------------------------

class DiagnosticOption(BaseModel):
    label: str
    correct: bool
    value: str
    misconception: Optional[str] = None


class MistakeGenomeEntry(BaseModel):
    message: str
    recommended_support: list[str] = Field(default_factory=list)


class LessonScreen(BaseModel):
    id: str
    subject: str
    topic: str
    concept: str
    gradeBand: str
    theme: str
    hook: dict
    sandbox: dict
    concept_screen: dict
    diagnostic: dict
    mistake_genome: dict[str, MistakeGenomeEntry]
    image_prompt: Optional[str] = None
    image_alt: Optional[str] = None


class LessonResponse(BaseModel):
    record: LessonScreen
    content_source: Literal["library", "generated"]


# --- QuizItem (Assessment Agent output) -------------------------------------

class QuizOption(BaseModel):
    label: str
    correct: bool
    misconception: Optional[str] = None


class QuizItem(BaseModel):
    id: str
    prompt: str
    gradeBand: str
    difficulty: Literal["warmup", "steady", "challenge"] = "steady"
    options: list[QuizOption]
    hint_ladder: list[str] = Field(default_factory=list)


class AssessmentResponse(BaseModel):
    assessment_id: str
    items: list[QuizItem]
    mistake_genome_map: dict[str, MistakeGenomeEntry]


# --- Session / Root Agent state ---------------------------------------------

class Profile(BaseModel):
    """Qualitative profile read by the Phase 1 lesson pipeline
    (root_agent.py / teaching_agent.py). See StudentProfile below for the
    unrelated, more detailed numeric profile Phase 2 added -- SessionState
    carries both, with no conversion between them yet."""
    ageBand: str = "unknown"
    energy: str = "unknown"
    interest: str = "unknown"
    preferredBlend: list[str] = Field(default_factory=list)
    profileConfidence: float = 0.1


# --- Phase 2: multi-agent evolution (orchestrator/labmodel/forces_lab) ------
#
# StudentProfile is the richer telemetry captured by
# frontend/forces_lab.html's onboarding modal (grade, ability, tiredness,
# attention, stress, motivation, prior knowledge). It's a deliberately
# separate model from Profile above, not a replacement for it -- Profile is
# what the existing lesson pipeline reads and is covered by tests; this one
# is additive, used only by the new orchestrator hint slice, so it can
# evolve without touching the working code path.

class StudentProfile(BaseModel):
    name: str = "Candidate_Node"
    age: int = 10
    grade: int = 4
    ability: str = "Elementary"
    tiredness: int = Field(3, ge=0, le=10)
    attention: int = Field(7, ge=0, le=10)
    stress: int = Field(2, ge=0, le=10)
    motivation: int = Field(7, ge=0, le=10)
    prior_knowledge: int = Field(3, ge=0, le=10)


class SessionState(BaseModel):
    session_id: str
    xp: int = 0
    profile: Profile = Field(default_factory=Profile)
    student_profile: Optional[StudentProfile] = None
    subjectContext: Optional[SubjectContext] = None
    mistakeGenome: list[dict] = Field(default_factory=list)


class CreateSessionResponse(BaseModel):
    session_id: str
    state: SessionState


class CreateSessionRequest(BaseModel):
    """Optional body for POST /api/session. Old callers (frontend/
    adaptive_learning_avatar_demo_v4.html) send no body at all, which is
    still valid -- every field here is optional so that keeps working
    unchanged."""
    profile: Optional[StudentProfile] = None


# NOTE -- known duplication, not yet resolved: these fields are redeclared
# almost verbatim in orchestrator/graph.py's HintGraphState (a TypedDict,
# since LangGraph's StateGraph needs that shape rather than a Pydantic
# model). There is currently no single source of truth for "what a hint
# request/response looks like" -- if you add/rename a field here, go check
# HintGraphState too, and vice versa. Worth collapsing into one shared
# definition (e.g. deriving the TypedDict from this model, or vice versa)
# before this drifts further.
class HintRequest(BaseModel):
    task_number: int
    task_question: str
    grade_band: str
    static_hint_fallback: str = ""


class HintResponse(BaseModel):
    hint_text: str
    source: Literal["orchestrator", "static"] = "orchestrator"
    reward_metric: float = 0.0


class LessonRequest(BaseModel):
    concept: str
    gradeBand: Literal["grade5", "high"]
    theme: Literal["soccer", "creative_play"]


class DiagnosticAnswer(BaseModel):
    concept: str
    option_value: str
