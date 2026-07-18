# Learning Avatar

## Major update summary

This release turns the project into a more complete end-to-end agentic learning experience. The core app now includes a working backend, a real MCP-backed content service, a FastAPI web interface, and an initial LangGraph-based orchestrator for interactive hints.

## What changed

### 1. End-to-end lesson delivery
- Added a web backend that serves the frontend and exposes session and lesson APIs.
- Implemented session management with persisted state.
- Connected lesson requests to a content service instead of relying on static embedded data.

### 2. MCP-based content access
- Added a standalone MCP server that exposes lesson content as tools.
- The teaching flow can retrieve content through this service, creating a cleaner separation between app logic and content storage.

### 3. Multi-agent orchestration foundation
- Introduced a LangGraph-based orchestrator for hint generation.
- Added a worker/critic flow for producing and validating hints.
- The /forces-lab experience now supports a real hint path with graceful fallback behavior.

### 4. Better structure and testing
- Organized the project around a clearer package layout with reusable agents, schemas, and config handling.
- Added tests around the core agent and orchestration behavior.
- Kept mock-mode support so the app can run without an API key.

## Project highlights

- Three hand-rolled agents with explicit orchestration logic
- FastAPI-based web app serving the frontend from the same origin
- MCP server for content retrieval
- SQLite-backed session state
- LangGraph-based hint orchestration slice
- Mock and live LLM modes

## Quick start

With uv:

```bash
uv sync
uv run learning-avatar-mcp-server
uv run learning-avatar-serve
```

Then open the web app in the browser and use the main experience or the /forces-lab page for the hint workflow.

## Testing

```bash
uv sync --extra dev
uv run pytest -v
```

## Optional: `canvas_lab/` (independent third surface)

`canvas_lab/` is a self-contained sibling project — a dual-layered
interactive lesson canvas (Alpine.js frontend, FastAPI backend) with its
own LLM generate → validate → critique pipeline for on-the-fly lessons,
cached in its own SQLite file. It does not share content schema, session
state, or a database with the rest of this app — it's a separate service
you can run alongside the main app and the MCP server, not a replacement
for either. See `canvas_lab/README.md` and
`canvas_lab/docs/llm-lesson-generation-spec.md` for its own architecture.

```bash
cd canvas_lab
uv sync
uv run uvicorn main:app --reload   # serves on :8000, clear of :8100/:9000
```

## Notes

- Mock mode works without a live API key.
- To enable real LLM generation, set the app to live mode and provide an OpenAI API key.
- The content server must be running before lesson requests can succeed.

- `assessment_agent._generate_via_llm` — parse + validate an LLM-generated
  quiz, mirroring `teaching_agent.py`'s pattern exactly.
- `web/main.py`'s `/diagnostic` route doesn't yet re-check the submitted
  answer against the real lesson record (it's hardcoded to treat `"a"` as
  correct) — the frontend currently checks correctness locally instead,
  using the record it already fetched, so this only matters once you want
  server-side XP/mistake-genome bookkeeping to be authoritative.
- A TypeScript conversion of `frontend/adaptive_learning_avatar_demo_v4.html`
  — now that the fetch contracts are stable, this is a good time to define
  matching `.ts` interfaces for `LessonScreen`/`QuizItem` and let the
  compiler catch a frontend/backend shape mismatch instead of a runtime bug.
- DSPy signatures, GRPO/RLVR fine-tuning, and a broader MCP server
  (retrieval/classification/calendar) are out of scope for this scaffold on
  purpose — this piece is just the orchestration skeleton those build on top
