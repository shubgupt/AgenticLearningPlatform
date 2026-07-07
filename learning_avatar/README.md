# Learning Avatar 

A runnable starting point for the "architect an end-to-end agentic
application" exercise: three hand-rolled agents (no LangChain/CrewAI/etc.),
one real MCP server exposing the content library as its tools, a thin
FastAPI boundary that also serves the frontend (same-origin, no CORS), and
tests built around mocking from day one. Costs $0 to run as-is
(`llm.mode: mock` in `config.yaml`).

`src/`-layout package (`src/learning_avatar/`), `pyproject.toml`, and
`config.yaml` follow the same shape as a typical `uv`-managed Python
project — swap in `uv sync` / `uv run` if you have `uv` installed, or use
plain `pip` + `requirements.txt`, both work.

## Why it's built this way

- **No agent framework.** `agents/root_agent.py` is plain Python calling
  `agents/teaching_agent.py` directly. The orchestration pattern — "check
  cheap source first, generate only if needed, validate, retry once, fail
  loudly" — is fifteen lines you can read top to bottom, not something
  hidden inside a framework's `Agent.run()`.
- **The lesson content moved server-side, behind a real protocol
  boundary, not an import.** `core/content_library.py` is what used to be
  the frontend's embedded `LESSON_LIBRARY` JavaScript array — now it's the
  Teaching Agent's default input (per `agents/prompts/teaching_agent_prompt.md`
  section 3). `mcp/server.py` is a standalone MCP server — its own
  long-running process, started by hand (`uv run learning-avatar-mcp-server`),
  reached over HTTP — that wraps it as tools. `teaching_agent.py` talks to
  it through `mcp/client.py`, never by importing `content_library`
  directly — the same way it would talk to *anyone's* MCP server later.
  It's a backing service, not something the web app spawns for you: if
  it's not running, lesson requests fail with a clear error instead of a
  hidden subprocess quietly appearing.
- **Every agent depends on an interface, not a vendor SDK.**
  `llm_client.py` defines `LLMClient`; `MockLLMClient` and `OpenAILLMClient`
  both implement it. Flip `llm.mode` in `config.yaml` to swap between them
  without touching agent code.
- **Schemas are load-bearing.** `core/schemas.py` mirrors the JSON
  contracts in `agents/prompts/ui_prompt.md`. Every agent response gets
  validated against these before Root Agent's critic check even looks at
  it.

## How does the HTML call Python?

`frontend/adaptive_learning_avatar_demo_v4.html` is now served *by* this
same FastAPI process (see the `StaticFiles`/`FileResponse` mount at the
bottom of `web/main.py`), so browser and server are the same origin —
`fetch("/api/session")` just works, no CORS headers to configure. The flow:

1. Page loads → `init()` calls `bootstrapSession()` → `POST /api/session`
   → backend creates a SQLite-backed session, returns a `session_id`.
2. Student picks a grade/theme/law → `renderLesson()` calls
   `fetchLessonRecord(ctx)` → `POST /api/session/{id}/lesson` with
   `{concept, gradeBand, theme}`.
3. `web/main.py`'s `lesson()` route calls `root_agent.get_lesson(...)`,
   which calls `teaching_agent.generate_lesson(...)`, which calls the MCP
   server *over HTTP* — a second, already-running process (see "Running
   it" below) — which reads `content_library.py`, which reads the JSON
   file. The whole chain runs in milliseconds because it's all local
   lookups — no LLM call happens unless nothing matched. If that second
   process isn't running, this step raises a clear error instead of hanging.
4. The `LessonScreen` JSON comes back through all those layers unchanged
   and the browser renders it exactly like it used to render the old
   embedded array — the rendering code (`sceneShell`, `playRollingObjectScene`,
   etc.) didn't need to change at all, only *where the data comes from* did.

## Project layout

```
pyproject.toml              deps + [project.scripts] entry points
config.yaml                  non-secret settings (model names, mock/live, host/port, mcp host/port)
.env.example                 secret settings only (the API key)
src/learning_avatar/
  config.py                  loads config.yaml + .env, computes all paths once
  llm_client.py               LLMClient interface + Mock/OpenAI impls
  core/
    schemas.py                 Pydantic models = the shared contract
    state_store.py              SQLite session persistence
    content_library.py          the old LESSON_LIBRARY, now the Teaching
                                 Agent's default input (loads the JSON files)
  mcp/
    server.py                   standalone MCP server wrapping content_library --
                                 its own process, started by hand (see below)
    client.py                   HTTP client used by teaching_agent.py to reach
                                 the already-running server.py process
  agents/
    root_agent.py                orchestration + critic check
    teaching_agent.py             MCP lookup -> LLM fallback -> validate
    assessment_agent.py           same pattern, thinner (extend as an exercise)
    prompts/                      the actual system prompts, loaded at runtime
  content/
    newtons_laws_lesson_library.json   12 pre-authored lessons
    concept_definitions.json            ground-truth physics per concept
  web/
    main.py                     FastAPI app + serves frontend/ same-origin
tests/
  conftest.py                  shared fixtures, incl. mock_llm
  test_teaching_agent.py        mocks the MCP client layer
  test_root_agent.py            mocks the teaching_agent layer (one level up)
frontend/
  adaptive_learning_avatar_demo_v4.html   now fetches lessons from the API —
                                            no embedded content anymore
```

## Running it

This is **two processes, started in order, in two terminals.** The content
server is a backing service — start it first and leave it running, the same
way you'd start a database before an app that reads from it. Nothing here
launches it for you.

With `uv` (recommended, matches this layout):
```bash
uv sync    # picks up the mcp>=1.9.0 bump this needed -- re-run even if you synced before
cp .env.example .env        # optional while llm.mode: mock — no key needed yet
```

Terminal 1 — start the content server first, leave it running:
```bash
uv run learning-avatar-mcp-server
# Content-retrieval MCP server listening on http://127.0.0.1:9000/mcp
```

Terminal 2 — start the web app:
```bash
uv run learning-avatar-serve
# Learning Avatar web app: open http://127.0.0.1:8000/
```
It prints the URL to open on startup — **always check that line, not this
README.** The port comes from `config.yaml`'s `server.port`, which you (or a
past debugging session) may have changed away from the 8000 default, e.g.
to dodge an "Address already in use" error. If the site "isn't coming up,"
this mismatch — browser pointed at 8000 while the app is actually on some
other port — is the single most common cause. `config.yaml` is always the
source of truth.

With plain `pip`, same two-terminal shape:
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt      # or: pip install -e .
cp .env.example .env

# Terminal 1:
python3 -m learning_avatar.mcp.server
# Terminal 2:
uvicorn learning_avatar.web.main:app --reload
```

Open whatever URL Terminal 2 printed — that's the actual app now, served
from the backend, not a file opened from disk. (In this project's current
`config.yaml` that's port 8100, not the 8000 default — see the note above.)

**If you forget to start the content server first:** the web app still
starts fine (it's a separate process), and the page loads fine — sessions
don't need it. But picking a lesson will show a "Content not ready" card
with the exact fix (`uv run learning-avatar-mcp-server`) instead of hanging
or crashing. `GET /health` also reports `mcp_reachable: true/false` if you
want to check from the command line: `curl localhost:<port>/health`
(substitute whatever port Terminal 2 printed).

Try the API directly (substitute your actual port for 8000 below):
```bash
curl -X POST localhost:8000/api/session
# -> {"session_id": "...", "state": {...}}

curl -X POST localhost:8000/api/session/<id>/lesson \
  -H "Content-Type: application/json" \
  -d '{"concept": "law_1_inertia", "gradeBand": "grade5", "theme": "soccer"}'
# -> a real LessonScreen, served from the MCP content library, $0 cost
# (needs the content server running in the other terminal, or you'll get a 503)
```

Run the tests (these mock the MCP client layer, so the content server
doesn't need to be running). `pytest` and friends are in the `dev` optional
dependency group, which plain `uv sync` does **not** install — you need:
```bash
uv sync --extra dev
uv run pytest -v      # or: pytest -v
```

Poke at the MCP server directly (useful for debugging tool schemas — this
starts its own throwaway instance, separate from the one in Terminal 1):
```bash
uv run mcp dev src/learning_avatar/mcp/server.py
```

## Turning on real generation

1. Get an OpenAI API key, put it in `.env` as `OPENAI_API_KEY` (see
   `.env.example` for the full file shape, including the
   `PROJECT_ROOT_DIR`/`PROJECT_PYTHON`/`PYTHONPATH` exports our other
   projects use).
2. Set `llm.mode: live` in `config.yaml` (or `LLM_MODE=live` env var, which
   overrides the yaml).
3. Call `/api/session/<id>/lesson` with a `concept` that isn't one of the
   12 pre-authored ones (or a `gradeBand`/`theme` combo outside `grade5`/
   `high` × `soccer`/`creative_play`) — you'll see `content_source:
   "generated"` and a real model call, guarded by the same schema
   validation the mock path exercises in tests.

## What's deliberately left unfinished

These are marked with `TODO`/`NotImplementedError` in the code — they're
the natural next exercises, not oversights:

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
  of.

## A note on what I could and couldn't verify

This sandbox has no network access, so I could not `pip install`/`uv sync`
and actually run the server or `pytest` end to end. What I did verify:
every `.py` file compiles (`python -m py_compile`), every cross-module
import resolves to a name that's actually defined where it's imported
from, the JSON content files parse, and the frontend's JavaScript parses
cleanly with the embedded library removed. Run `uv run pytest -v` yourself
before trusting this in front of anyone — that's the one thing I couldn't
close the loop on.
