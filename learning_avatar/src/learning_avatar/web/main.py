"""
FastAPI app -- the thin HTTP boundary between the browser and the Root
Agent. Routes do almost nothing themselves: load session, call root_agent,
save session, return response. All the actual decisions happen in
learning_avatar/agents/.

This is also where the frontend is served *from the same origin* as the
API (see the StaticFiles mount at the bottom of this file). That single
choice is what lets the browser call `fetch("/api/session")` with no CORS
configuration at all -- browser and server are, as far as the browser is
concerned, the same website.

Run it (after starting the MCP content server separately -- see
mcp/server.py and README "Running it"):
    uv run uvicorn learning_avatar.web.main:app --reload
    (or: uv run learning-avatar-serve, see pyproject.toml [project.scripts])

Then open http://<server.host>:<server.port>/ as set in config.yaml
(defaults to 127.0.0.1:8000, but check config.yaml -- it's the single
source of truth for the port, not this comment).

Try the API directly (LLM_MODE=mock by default, so this costs $0):
    curl -X POST localhost:<port>/api/session
    curl -X POST localhost:<port>/api/session/<id>/lesson \
        -H "Content-Type: application/json" \
        -d '{"concept": "law_1_inertia", "gradeBand": "grade5", "theme": "soccer"}'
"""
from __future__ import annotations

from fastapi import Body, Depends, FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles

from learning_avatar.agents import root_agent
from learning_avatar.config import settings
from learning_avatar.core.schemas import (
    CreateSessionRequest,
    CreateSessionResponse,
    DiagnosticAnswer,
    HintRequest,
    HintResponse,
    LessonRequest,
    LessonResponse,
    SessionState,
    SubjectContext,
)
from learning_avatar.core.state_store import create_session, get_session, save_session
from learning_avatar.llm_client import LLMClient, get_llm_client
from learning_avatar.mcp.client import MCPServerUnavailableError
from learning_avatar.orchestrator.graph import run_hint_orchestrator

app = FastAPI(title="Learning Avatar — Agentic Backend")


def _require_session(session_id: str) -> SessionState:
    session = get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@app.post("/api/session", response_model=CreateSessionResponse)
def new_session(req: CreateSessionRequest | None = Body(default=None)):
    """`req` is optional so the existing v4 frontend (which POSTs with no
    body at all) keeps working unchanged. frontend/forces_lab.html sends
    `{"profile": {...}}` -- when present, it's stored on the session as
    `student_profile` for the new hint orchestrator route below to read."""
    state = create_session()
    if req is not None and req.profile is not None:
        state.student_profile = req.profile
        save_session(state)
    return CreateSessionResponse(session_id=state.session_id, state=state)


@app.get("/api/session/{session_id}", response_model=SessionState)
def read_session(session_id: str):
    return _require_session(session_id)


@app.post("/api/session/{session_id}/lesson", response_model=LessonResponse)
async def lesson(session_id: str, req: LessonRequest, llm: LLMClient = Depends(get_llm_client)):
    """This is the endpoint that replaces the frontend's old embedded
    LESSON_LIBRARY array. The browser now asks for a lesson by
    (concept, gradeBand, theme); the Root Agent decides whether that comes
    from the pre-authored library or gets generated fresh."""
    session = _require_session(session_id)
    ctx = SubjectContext(concept=req.concept, gradeBand=req.gradeBand, theme=req.theme)

    try:
        result = await root_agent.get_lesson(session, ctx, llm)
    except root_agent.CriticRejectedError as exc:
        # Never let a raw agent failure reach the student -- degrade to a
        # clear, honest error instead of a broken screen.
        raise HTTPException(status_code=422, detail={"message": "Lesson failed guardrail checks", "problems": exc.problems})
    except MCPServerUnavailableError as exc:
        # The content-retrieval MCP server is a separate process the student
        # (or whoever's running this) is expected to have started already.
        # 503 = "the site is fine, a dependency it needs isn't up yet."
        raise HTTPException(status_code=503, detail={"message": str(exc)})

    save_session(session)
    return result


@app.post("/api/session/{session_id}/hint", response_model=HintResponse)
async def hint(session_id: str, req: HintRequest, llm: LLMClient = Depends(get_llm_client)):
    """The one real vertical slice through the new Phase 2 architecture
    (see docs/architecture.md "Phase 2"): Router -> Policy -> LabModel-
    Worker -> LabModel-Critic, run as a real LangGraph graph
    (orchestrator/graph.py), calling the same LLMClient/mock-vs-live switch
    every other route already uses. Falls back to the frontend-supplied
    static hint on any failure -- a hint is low-stakes enough that this is
    a 200 with source="static", not an error response."""
    session = _require_session(session_id)
    sp = session.student_profile

    try:
        result = await run_hint_orchestrator(
            llm=llm,
            model=settings.worker_model,
            task_number=req.task_number,
            task_question=req.task_question,
            grade_band=req.grade_band,
            attention_score=sp.attention if sp else 7,
            motivation_score=sp.motivation if sp else 7,
            static_hint_fallback=req.static_hint_fallback,
        )
        return HintResponse(
            hint_text=result.get("hint_text") or req.static_hint_fallback,
            source=result.get("source", "orchestrator"),
            reward_metric=0.0,
        )
    except Exception as exc:  # noqa: BLE001 -- deliberately broad: a hint
        # request degrading to the static fallback should never surface as
        # a 500 to the student, regardless of which layer (LangGraph
        # itself, the LLM call, an unconfigured dependency) failed.
        return HintResponse(hint_text=req.static_hint_fallback, source="static", reward_metric=0.0)


@app.post("/api/session/{session_id}/diagnostic", response_model=SessionState)
def diagnostic(session_id: str, answer: DiagnosticAnswer):
    session = _require_session(session_id)
    # NOTE: this scaffold doesn't re-fetch the lesson record to check
    # `option_value` against it -- wire that up as your next step, following
    # the same MCP lookup pattern teaching_agent.py already demonstrates.
    correct = answer.option_value == "a"  # placeholder until wired up
    root_agent.record_diagnostic_result(session, answer.concept, correct, None if correct else "unwired_misconception")
    save_session(session)
    return session


@app.get("/health")
async def health():
    """Cheap way to check both processes from one place: GET /health tells
    you the web app is up; mcp_reachable tells you whether the separately-
    started content server (uv run learning-avatar-mcp-server) is too."""
    from learning_avatar.mcp import client as mcp_client
    try:
        await mcp_client.fetch_concept_definition("__health_check__")
        mcp_reachable = True
    except MCPServerUnavailableError:
        mcp_reachable = False
    return {"status": "ok", "mcp_reachable": mcp_reachable, "mcp_server_url": settings.mcp_server_url}


# --- Serve the frontend from this same FastAPI process -------------------
# NOTE: frontend/index.html does exist (an earlier, unfinished "Newton's
# Odyssey" canvas-map prototype) but is NOT routed anywhere -- it's dead,
# orphaned code, not a home page. `/` explicitly serves
# adaptive_learning_avatar_demo_v4.html below instead. We deliberately do
# NOT pass `html=True` to StaticFiles here, specifically so index.html can't
# silently become the default response for "/" or any other unmapped path.
# If you want that prototype live, give it its own route the way
# /forces-lab has one; if you don't, it's a candidate for deletion.
if settings.frontend_dir.exists():
    app.mount("/static", StaticFiles(directory=str(settings.frontend_dir)), name="static")

    from fastapi.responses import FileResponse

    @app.get("/")
    def serve_frontend():
        return FileResponse(settings.frontend_dir / "adaptive_learning_avatar_demo_v4.html")

    @app.get("/forces-lab")
    def serve_forces_lab():
        """The Phase 2 UI (cleaned-up version of the uploaded Gemini demo,
        see docs/architecture.md). Served alongside "/", not replacing it --
        v4's Hook/Sandbox/Concept/Diagnostic lesson flow still works exactly
        as before at "/"."""
        return FileResponse(settings.frontend_dir / "forces_lab.html")


def run():
    """Entry point for `uv run learning-avatar-serve` (see pyproject.toml)."""
    import uvicorn
    # Printed explicitly so the URL to open is never a guess or a stale doc
    # comment -- config.yaml's server.host/port is the only source of truth.
    print(f"Learning Avatar web app: open http://{settings.host}:{settings.port}/")
    uvicorn.run("learning_avatar.web.main:app", host=settings.host, port=settings.port, reload=True)


if __name__ == "__main__":
    run()
