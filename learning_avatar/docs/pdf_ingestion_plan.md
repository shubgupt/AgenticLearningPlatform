# PDF Ingestion Agent — Phased Implementation Plan

## Context

The platform already has a working multi-agent backend (Root → Teaching → Assessment), an MCP content server, and a static lesson library (12 JSON records). This plan adds a **PDF Ingestion Agent** that converts uploaded PDFs into structured, retrieval-ready learning assets.

**Fixed technology choices (all local, no cloud APIs):**
- Parsing: `docling` (DocumentConverter)
- Chunking: `chonkie` (SemanticChunker)
- Embeddings + late chunking: `jinaai/jina-embeddings-v2-base-en` via PyTorch + transformers (local GPU/CPU)
- Vision fallback: `colpali-engine` for visually dense pages (local model)
- Card generation LLM: `ollama` with `llama3.2` via its OpenAI-compatible API (`http://localhost:11434/v1`); structured JSON output enforced by parsing with Pydantic
- Orchestrator: `src/chunker.py` → `process_document_pipeline(pdf_path: str)`
- Tooling: PEP 517/621 `pyproject.toml`, all deps in `[project.dependencies]`, `uv sync`

**Local model setup required before Phase 5:**
```bash
brew install ollama          # or: curl -fsSL https://ollama.com/install.sh | sh
ollama serve &
ollama pull llama3.2         # ~2GB, runs on CPU if no GPU
```

**Design principle:** Phase 1 wires the full e2e skeleton (stubs everywhere). Each subsequent phase replaces exactly one stub with a real implementation. Only storage tables that exist in the final product are ever created — no intermediate-only tables.

---

## Final storage schema (defined once in Phase 1, never changed)

```sql
-- tracks each PDF ingestion run
CREATE TABLE IF NOT EXISTS ingestions (
    ingestion_id TEXT PRIMARY KEY,
    filename     TEXT NOT NULL,
    page_count   INTEGER,
    status       TEXT NOT NULL,   -- pending | done | failed
    error        TEXT,
    created_at   TEXT NOT NULL
);

-- one row per semantic chunk; page provenance lives here, not in a separate table
CREATE TABLE IF NOT EXISTS chunks (
    chunk_id       TEXT PRIMARY KEY,
    ingestion_id   TEXT NOT NULL,
    text           TEXT NOT NULL,
    context_prefix TEXT NOT NULL,
    context_suffix TEXT NOT NULL,
    page_start     INTEGER NOT NULL,
    page_end       INTEGER NOT NULL,
    heading_path   TEXT NOT NULL   -- JSON array e.g. ["Ch 3", "Law 1"]
);

-- late-chunked Jina embeddings
CREATE TABLE IF NOT EXISTS embeddings (
    chunk_id    TEXT PRIMARY KEY,
    vector_json TEXT NOT NULL      -- JSON array of floats
);

-- all card types per chunk
CREATE TABLE IF NOT EXISTS learning_cards (
    card_id    TEXT PRIMARY KEY,
    chunk_id   TEXT NOT NULL,
    card_type  TEXT NOT NULL,      -- standard|simplified|analogy|hint|quiz|teacher_note|recap
    card_json  TEXT NOT NULL       -- full card content as JSON
);

-- chunk-to-chunk and chunk-to-video-artifact links
CREATE TABLE IF NOT EXISTS chunk_links (
    link_id          TEXT PRIMARY KEY,
    source_chunk_id  TEXT NOT NULL,
    target_id        TEXT NOT NULL,
    target_type      TEXT NOT NULL,  -- chunk | video_artifact
    relation         TEXT NOT NULL,  -- same_concept|prerequisite|supports|misconception_match|matches_video
    confidence       REAL NOT NULL,
    evidence         TEXT NOT NULL
);

-- conservative learner behavioral signals (never diagnoses)
CREATE TABLE IF NOT EXISTS learner_signals (
    signal_id   TEXT PRIMARY KEY,
    session_id  TEXT NOT NULL,
    signal_type TEXT NOT NULL,
    confidence  REAL NOT NULL,
    scope       TEXT NOT NULL,      -- session | concept | today
    evidence    TEXT NOT NULL,
    created_at  TEXT NOT NULL
);
```

---

## Phase 1 — Skeleton E2E (all stubs, everything wired)

**Goal:** Full pipeline exists and runs end-to-end. Every step is a stub returning valid-schema data. The API endpoint accepts a real PDF upload and returns a well-formed (stub) response. All final storage tables are created. `pyproject.toml` declares all deps.

### New files
```
src/
  chunker.py                        # orchestrator — process_document_pipeline()
  pdf_ingestion/
    __init__.py
    schemas.py                      # all Pydantic models
    store.py                        # SQLite: all 6 tables, CRUD functions
    parser.py                       # STUB: returns 1 fake chunk worth of text
    chunker.py                      # STUB: returns 1 Chunk from the parser output
    embedder.py                     # STUB: returns [0.0] * 768
    card_generator.py               # STUB: returns 7 placeholder LearningCard objects
    linker.py                       # STUB: returns []
    signal_detector.py              # STUB: returns []
src/learning_avatar/web/
  ingest_routes.py                  # FastAPI router: POST /api/ingest, GET /api/ingest/{id}
```

### `pyproject.toml` (PEP 517/621 — all deps declared upfront)
```toml
[project]
name = "learning-avatar"
version = "0.1.0"
requires-python = ">=3.10"

[project.dependencies]
fastapi = ">=0.115"
uvicorn = ">=0.30"
pydantic = ">=2.9"
openai = ">=1.40"
mcp = ">=1.9"
python-dotenv = "*"
pyyaml = "*"
docling = ">=2.0"
chonkie = ">=0.4"
torch = ">=2.3"
transformers = ">=4.40"
colpali-engine = ">=0.3"
tiktoken = ">=0.7"
# openai SDK reused to talk to ollama's OpenAI-compatible endpoint (already in deps)

[project.scripts]
learning-avatar-serve = "learning_avatar.web.main:run"
learning-avatar-mcp-server = "learning_avatar.mcp.server:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

### `schemas.py`
```python
class IngestionRecord(BaseModel):
    ingestion_id: str; filename: str; page_count: int
    status: Literal["pending", "done", "failed"]; error: str | None = None; created_at: str

class Chunk(BaseModel):
    chunk_id: str; ingestion_id: str; text: str
    context_prefix: str; context_suffix: str
    page_start: int; page_end: int; heading_path: list[str]

class CardType(str, Enum):
    standard="standard"; simplified="simplified"; analogy="analogy"
    hint="hint"; quiz="quiz"; teacher_note="teacher_note"; recap="recap"

class LearningCard(BaseModel):
    card_id: str; chunk_id: str; card_type: CardType
    title: str; body: str; quiz: dict | None = None

class ChunkLink(BaseModel):
    link_id: str; source_chunk_id: str; target_id: str
    target_type: Literal["chunk","video_artifact"]
    relation: Literal["same_concept","prerequisite","supports","misconception_match","matches_video"]
    confidence: float; evidence: str

class LearnerSignal(BaseModel):
    signal_id: str; session_id: str
    signal_type: Literal["reading_tolerance_may_be_low","visual_examples_help",
                          "shorter_chunks_help","needs_more_time_today","break_requested"]
    confidence: float; scope: Literal["session","concept","today"]
    evidence: str; created_at: str

class PipelineResult(BaseModel):
    ingestion_id: str; chunk_count: int; card_count: int; link_count: int
```

### `src/chunker.py` — orchestrator (Phase 1: full call chain, all stubs)
```python
def process_document_pipeline(pdf_path: str) -> PipelineResult:
    ingestion_id = str(uuid.uuid4())
    store.create_ingestion(ingestion_id, Path(pdf_path).name)

    raw_text = parser.extract(pdf_path)                    # STUB → fake string
    chunks   = chunker.chunk(raw_text, ingestion_id)       # STUB → [1 Chunk]
    store.save_chunks(chunks)

    vectors = [embedder.embed(c) for c in chunks]          # STUB → [[0.0]*768]
    store.save_embeddings(chunks, vectors)

    cards = card_generator.generate(chunks)                # STUB → 7 placeholder cards
    store.save_cards(cards)

    links = linker.link(chunks)                            # STUB → []
    store.save_links(links)

    store.mark_done(ingestion_id, len(chunks))
    return PipelineResult(ingestion_id=ingestion_id,
                          chunk_count=len(chunks), card_count=len(cards), link_count=len(links))
```

### `ingest_routes.py` — FastAPI router
```
POST /api/ingest               UploadFile → saves to temp file → process_document_pipeline()
GET  /api/ingest/{id}          → IngestionRecord
GET  /api/ingest/{id}/chunks   → list[Chunk]
GET  /api/ingest/{id}/cards    → list[LearningCard] (optional ?type= filter)
GET  /api/ingest/{id}/links    → list[ChunkLink]
```
Mount in `web/main.py`: `app.include_router(ingest_router)`

### Verification — Phase 1
```bash
uv sync
uv run learning-avatar-serve
curl -X POST http://127.0.0.1:8100/api/ingest -F "file=@any.pdf"
# → { "ingestion_id": "...", "chunk_count": 1, "card_count": 7, "link_count": 0 }
curl http://127.0.0.1:8100/api/ingest/{id}/cards
# → 7 placeholder LearningCard objects with valid schema
```

---

## Phase 2 — Real Parsing (docling)

**Only file changed:** `src/pdf_ingestion/parser.py`

Replace stub with docling DocumentConverter. Output: plain text per page with page numbers, heading detection, noise removal (repeated headers/footers). The `extract()` function returns a structured result the chunker can use.

```python
from docling.document_converter import DocumentConverter

def extract(pdf_path: str) -> list[dict]:
    # Returns [{"page": int, "text": str, "is_heading": bool}] per block
    # Noise filter: skip blocks appearing on > 70% of pages (headers/footers)
    # ColPali placeholder: if page has no extractable text → log warning, skip page for now
    result = DocumentConverter().convert(pdf_path)
    ...
```

`process_document_pipeline()` unchanged — it already calls `parser.extract()`.

### Verification
Upload a real 5-page PDF → GET /chunks → `text` field contains real extracted content, not stub text.

---

## Phase 3 — Real Chunking (chonkie SemanticChunker)

**Only file changed:** `src/pdf_ingestion/chunker.py`

Replace stub with chonkie. Input: structured block list from parser. Output: `list[Chunk]` with real semantic boundaries, heading_path, and context windows.

```python
from chonkie import SemanticChunker

def chunk(blocks: list[dict], ingestion_id: str) -> list[Chunk]:
    chunker = SemanticChunker(
        embedding_model="jinaai/jina-embeddings-v2-base-en",
        chunk_size=300, threshold=0.5
    )
    joined = "\n".join(b["text"] for b in blocks)
    raw_chunks = chunker.chunk(joined)
    # Reconstruct page_start/page_end by matching raw_chunk text back to blocks
    # Build heading_path from is_heading=True blocks that precede each chunk
    # Attach context_prefix/suffix: ±200 tokens from neighboring chunks
    return [Chunk(...) for rc in raw_chunks]
```

### Verification
Same PDF → GET /chunks → chunks respect topic boundaries, `heading_path` is non-empty, no chunk exceeds 400 tokens.

---

## Phase 4 — Real Embeddings (Jina + late chunking)

**Only file changed:** `src/pdf_ingestion/embedder.py`

Replace stub with Jina local model. Late chunking: embed `context_prefix + text + context_suffix` as one string.

```python
from transformers import AutoTokenizer, AutoModel
import torch

_TOKENIZER, _MODEL = None, None   # lazy-loaded on first call

def embed(chunk: Chunk) -> list[float]:
    # Input: context_prefix + " " + chunk.text + " " + context_suffix  (late chunking)
    # Forward pass through jinaai/jina-embeddings-v2-base-en
    # Mean-pool last hidden state → L2-normalize → return as list[float] (768-dim)
```

### Verification
Embed two chunks from the same physics topic → cosine similarity > 0.82. Embed two unrelated chunks → < 0.5.

---

## Phase 5 — Real Card Generation (Gemini + Pydantic Structured Outputs)

**Only file changed:** `src/pdf_ingestion/card_generator.py`

Replace stub with ollama via the OpenAI-compatible API. All 7 cards generated in a single call per chunk. Response parsed with Pydantic.

```python
from openai import OpenAI   # reuse existing dep — ollama speaks OpenAI protocol

_client = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")

def generate(chunks: list[Chunk]) -> list[LearningCard]:
    all_cards = []
    for chunk in chunks:
        resp = _client.chat.completions.create(
            model="llama3.2",
            messages=[
                {"role": "system", "content": CARD_SYSTEM_PROMPT},
                {"role": "user", "content": chunk.text},
            ],
            response_format={"type": "json_object"},
        )
        batch = CardBatch.model_validate_json(resp.choices[0].message.content)
        all_cards.extend(batch.cards)
    return all_cards
```

`CARD_SYSTEM_PROMPT` instructs the model to return exactly `{"cards": [...7 items...]}` with all card types.

Add to `config.yaml`:
```yaml
ollama:
  base_url: http://localhost:11434/v1
  model: llama3.2
```

### Verification
POST /ingest with real PDF → GET /cards?type=quiz → each quiz card has `question`, `options`, `correct_index`, `hint`.

---

## Phase 6 — ColPali Vision Fallback

**Only file changed:** `src/pdf_ingestion/parser.py`

Wire ColPali for pages where docling extraction confidence is low or returns no text.

```python
from colpali_engine.models import ColPali, ColPaliProcessor

def _extract_with_colpali(page_image_bytes: bytes) -> str:
    # Render page as image → pass to ColPali → return extracted text
    ...

def extract(pdf_path: str) -> list[dict]:
    ...
    for page in result.document.pages:
        if _needs_vlm_fallback(page):           # low confidence or empty text
            text = _extract_with_colpali(render_page(page))
        else:
            text = page.text
    ...
```

### Verification
Ingest a scanned PDF → blocks are populated (not empty), content is coherent.

---

## Phase 7 — Concept Linking + Learner Signals

**Files changed:** `src/pdf_ingestion/linker.py`, `src/pdf_ingestion/signal_detector.py`

Replace stubs with real implementations.

**Linker** — cosine similarity over embeddings table:
- > 0.82 → `same_concept`
- 0.70–0.82 → `supports`
- Chunk text matches a misconception string from `concept_definitions.json` → `misconception_match`
- Also add new MCP tool to `mcp/server.py`: `find_related_chunks(chunk_id, top_k)`

**Signal detector** — conservative rules only:
- 3+ wrong answers on one concept → `shorter_chunks_help` (confidence 0.5)
- Explicit break button event → `break_requested` (confidence 0.95)
- Correct on analogy card after wrong on standard → `visual_examples_help` (confidence 0.6)
- Never diagnose. Never reference protected traits.

Signal storage: each call to `detect_signals(session, events)` appends to `learner_signals` table (not to `session.mistakeGenome`).

### Verification
Unit tests: feed synthetic event sequences → assert correct `signal_type` and confidence range.

---

## Phase 8 — UI + Teaching Agent Integration

**Files changed:** `frontend/adaptive_learning_avatar_demo_v4.html`, `src/learning_avatar/agents/teaching_agent.py`

**Teacher dashboard (new section in existing HTML):**
- File upload → `POST /api/ingest` → poll `GET /api/ingest/{id}` until `status: "done"`
- Card browser (filter by type, hide `teacher_note` from student view)
- Signal table per session (teacher-only)

**Teaching Agent fallthrough** (`teaching_agent.py: generate_lesson()`):
1. MCP library lookup (existing) → hit → return `content_source: "library"`
2. Miss → cosine search over embedded PDF chunks → hit → assemble `LessonScreen` from `standard` card content → return `content_source: "pdf"`
3. Miss → LLM generation (existing) → return `content_source: "generated"`

### Verification
Upload a physics PDF → from student view, select a concept not in the 12-record library → lesson renders with `content_source: "pdf"` in the API response.

---

## Summary table

| Phase | Stub replaced | Files changed |
|---|---|---|
| 1 | — (skeleton) | All new files created, all stubs in place |
| 2 | `parser.extract()` | `parser.py` |
| 3 | `chunker.chunk()` | `pdf_ingestion/chunker.py` |
| 4 | `embedder.embed()` | `embedder.py` |
| 5 | `card_generator.generate()` | `card_generator.py`, `config.yaml` (ollama settings) |
| 6 | ColPali fallback in `parser.py` | `parser.py` |
| 7 | `linker.link()`, `signal_detector.detect_signals()` | `linker.py`, `signal_detector.py`, `mcp/server.py` |
| 8 | UI + Teaching Agent fallthrough | `adaptive_learning_avatar_demo_v4.html`, `teaching_agent.py` |
