"""
A real, standalone MCP server -- its own long-running process, separate
from the FastAPI app and started by hand, before the web app. It knows
nothing about FastAPI, sessions, or HTTP; its only job is exposing
core.content_library (the Teaching Agent's default input) as MCP tools,
reachable over the network the same way a database or any other backing
service would be.

Start it (in its own terminal, and leave it running):
    uv run learning-avatar-mcp-server

Then, separately, start the web app (uv run learning-avatar-serve). If this
process isn't running when the web app tries to fetch a lesson, the request
fails with a clear "start the MCP server" error instead of anything silently
spawning a hidden subprocess.

Poke at it directly with the MCP Inspector:
    uv run mcp dev src/learning_avatar/mcp/server.py

The Teaching Agent talks to this over mcp/client.py -- it does NOT import
core.content_library directly. That protocol boundary is the point: the
retrieval logic lives behind MCP the same way it would if this were swapped
for a real database, a vector store, or someone else's server later.
"""
from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from learning_avatar.config import settings
from learning_avatar.core import content_library

mcp = FastMCP("content-retrieval", host=settings.mcp_host, port=settings.mcp_port)


@mcp.tool()
def get_lesson_record(subject: str, topic: str, concept: str, grade_band: str, theme: str) -> dict:
    """Look up a single pre-authored lesson record by exact match on
    subject, topic, concept, grade_band, and theme. Returns {"found": false}
    if nothing matches -- callers should fall back to generation, not treat
    this as an error."""
    record = content_library.get_lesson_record(subject, topic, concept, grade_band, theme)
    return {"found": record is not None, "record": record}


@mcp.tool()
def list_available_combinations() -> list[dict]:
    """List every (concept, gradeBand, theme) combination that has
    pre-authored content, so a caller can know what's covered without
    guessing or making a failed lookup first."""
    return content_library.list_available_combinations()


@mcp.tool()
def get_concept_definition(concept_id: str) -> dict:
    """Fetch the ground-truth ConceptDefinition (formal statement + known
    misconceptions) for a concept, so a generation step never has to
    invent physics -- it only has to phrase it for the right grade band."""
    definition = content_library.get_concept_definition(concept_id)
    return {"found": definition is not None, "definition": definition}


@mcp.tool()
def find_related_chunks(query_text: str, top_k: int = 5) -> dict:
    """Search the PDF ingestion store for chunks semantically related to
    query_text. Returns the top_k most similar chunks by cosine distance
    over Jina embeddings. Returns {"found": false, "chunks": []} when the
    store is empty or embeddings haven't been generated yet."""
    try:
        from learning_avatar.config import settings
        from pdf_ingestion import store as pdf_store, embedder

        pdf_store.configure(settings.pdf_db_path)

        # Embed query text (reuse same Jina model)
        class _Q:
            text = query_text
            context_prefix = ""
            context_suffix = ""

        q_vec = embedder.embed(_Q())
        similar = pdf_store.find_top_k_similar(q_vec, top_k=top_k)

        # Build chunk_id → Chunk lookup from embedded chunks
        all_embedded = pdf_store.get_all_chunks_with_embeddings()
        chunk_map = {c.chunk_id: c for c, _ in all_embedded}

        _SUPPORTS = 0.70
        results = []
        for chunk_id, score in similar:
            if score < _SUPPORTS or chunk_id not in chunk_map:
                continue
            c = chunk_map[chunk_id]
            results.append({
                "chunk_id": c.chunk_id,
                "text": c.text,
                "heading_path": c.heading_path,
                "page_start": c.page_start,
                "confidence": round(score, 4),
            })

        return {"found": len(results) > 0, "chunks": results}
    except Exception as exc:
        return {"found": False, "chunks": [], "error": str(exc)}


def main():
    """Entry point for `uv run learning-avatar-mcp-server` (see
    pyproject.toml [project.scripts]). Runs as a persistent process over
    Streamable HTTP -- start this FIRST, in its own terminal, and leave it
    running. The web app connects to it as a client; it does not start it
    for you."""
    print(f"Content-retrieval MCP server listening on {settings.mcp_server_url}")
    print("Leave this running. Start the web app separately with: uv run learning-avatar-serve")
    mcp.run(transport="streamable-http")


if __name__ == "__main__":
    main()
