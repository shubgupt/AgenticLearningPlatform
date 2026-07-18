# Socratic Hybrid Canvas

A local visual prototype of an interactive educational app: a dual-layered
canvas (background scene + interactive overlay) on the left, a Socratic
Q&A panel on the right, gamified with XP/timer/attempts. The frontend
prefetches an entire lesson module once and renders every step from that
one JSON payload, client-side, with zero further network calls per
interaction. A second, optional backend pipeline generates new lessons on
the fly with an LLM generator + critic loop when no hand-authored lesson
exists for a given skill/modality.

## Requirements

- Python ≥ 3.11
- [`uv`](https://docs.astral.sh/uv/) — used for all dependency management and running the app

## Running it

```bash
uv sync
uv run uvicorn main:app --reload
```

Then open **http://127.0.0.1:8000**.

`uv sync` creates `.venv/` and installs everything from `uv.lock`.
`--reload` restarts the server on file changes — convenient while editing
`main.py` or any of the pipeline modules.

The frontend itself needs no build step: `static/index.html` pulls
Tailwind and Alpine.js from CDNs and loads `static/app.js` directly.

## Project structure

```
main.py                    FastAPI app: static file host, GET /, GET /api/lessons/load,
                            plus the LLM-lesson-generation routes (see below)
static/
  index.html                Single-page app shell — canvas + Socratic panel, all markup
  app.js                    Alpine.js component: prefetch, generic control/behavior
                             engine, evaluation panel, character picker, timer/XP
  mock-assets/
    backgrounds/             Background scene images, referenced via asset_manifest ids
                              and fetched on demand (only when a step using them mounts)

docs/
  llm-lesson-generation-spec.md   Design spec for the generation pipeline below

schema.sql                  SQLite schema: students, lesson_requests, generated_lessons,
                             llm_call_trace
db.py                       SQLite connection + schema init
llm_client.py                OpenAI-compatible LLM client + persisted/console call tracing
validator.py                 Deterministic validation of a generated lesson step
generator.py                  Lesson+evaluation generator (one LLM role)
critic.py                     Pedagogical critic — relevance + student-safety rubric (LLM role)
pipeline.py                    Orchestrates cache-check → generate → validate → critique →
                               retry (max 3) → store, plus the personalization overlay

tests/
  test_validator.py           Pure unit tests, no LLM/network needed
  test_pipeline.py             Pipeline tests against a fake LLM client (no real API calls)
```

## The static lesson (always available, no config needed)

`GET /` serves the SPA; `GET /api/lessons/load` returns the full
hand-authored curriculum in one shot — this is what the frontend actually
prefetches and renders. It needs no environment variables and works
immediately after `uv sync`.

## The LLM lesson-generation pipeline (optional, needs an LLM endpoint)

A second pipeline can generate new `slideshow`/`story`-type lessons on the
fly for a `(skill, modality)` combination that has no hand-authored step,
cache the result, and serve it — see `docs/llm-lesson-generation-spec.md`
for the full design. This part of the app is **not required** to run the
main prototype; it's reachable through its own API routes.

### Configuration

Set these environment variables to enable real generation:

```bash
export LLM_BASE_URL="..."   # any OpenAI-compatible endpoint
export LLM_API_KEY="..."
export LLM_MODEL="..."
```

Without them, `/`, `/api/lessons/load`, and cache-hit lesson requests all
still work fine — only a cache-miss generation attempt fails (with a clear
error recorded on the request, not a crash).

### API routes

```
POST /api/students              {name, age, grade, favorite_sport,
                                  favorite_character, friend_names} -> {id}

POST /api/lesson-requests       {student_id, skill, modality, mastery_pct,
                                  prereq_threshold, negative_constraint_token}
                                 -> {id, status: "pending"}
                                 (generation runs as a background task)

GET  /api/lesson-requests/{id}  -> current status (pending|generating|ready|failed),
                                    plus the assembled+personalized lesson once ready
```

Example walkthrough:

```bash
STUDENT_ID=$(curl -s -X POST localhost:8000/api/students \
  -H "Content-Type: application/json" \
  -d '{"name":"Alex","age":12,"grade":"Gr 7","favorite_sport":"soccer"}' \
  | python3 -c "import json,sys; print(json.load(sys.stdin)['id'])")

REQUEST_ID=$(curl -s -X POST localhost:8000/api/lesson-requests \
  -H "Content-Type: application/json" \
  -d "{\"student_id\":$STUDENT_ID,\"skill\":\"sci.physics.forces.net_force\",\"modality\":\"Story-Based\"}" \
  | python3 -c "import json,sys; print(json.load(sys.stdin)['id'])")

curl -s localhost:8000/api/lesson-requests/$REQUEST_ID | python3 -m json.tool
```

The generated lesson shows up in the `"lesson"` field of that last response
once `status` is `"ready"`. It's also viewable directly in
`generated_lessons.payload_json` (pre-personalization) and, for debugging a
rejected generation, `llm_call_trace.output` holds the model's raw
un-validated response.

### Live generation test

`tests/test_live_generation.py` calls the real configured LLM (unlike
`test_pipeline.py`, which only ever uses a fake client) — it's
auto-skipped unless `LLM_BASE_URL`/`LLM_API_KEY`/`LLM_MODEL` are set, so it
never affects the default `uv run pytest` run:

```bash
uv run pytest tests/test_live_generation.py -v -s
```

`-s` is required to actually see the generated lesson printed. Add
`--clear-cache` to force a fresh generation instead of reusing whatever's
already cached from a previous run of the same test:

```bash
uv run pytest tests/test_live_generation.py -v -s --clear-cache
```

### Data & tracing

Everything is stored in a local SQLite file, `lessons.db` (created on
first run, gitignored). Every LLM call — generator and critic — is
recorded in `llm_call_trace` (and printed to the server console) with
timing and an OTEL-span-shaped record, so it can later be swapped for a
real OpenTelemetry/Arize Phoenix exporter without a schema change.

Generated lessons are cached by `(skill, modality, negative_constraint_token)`
in `generated_lessons` — repeat requests for the same combination are
served instantly with zero further LLM calls; per-student personalization
(favorite sport, friend names) is applied as a text-substitution overlay
on top of the cached content, not baked into the generation prompt.

## Testing

```bash
uv run pytest
```

Runs both `tests/test_validator.py` (pure logic) and
`tests/test_pipeline.py` (pipeline behavior against a fake LLM client) —
no real API key or network access required for either.
