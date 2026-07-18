"""
The MCP *client* side: connects over HTTP to an already-running MCP server
(mcp/server.py, started separately with `uv run learning-avatar-mcp-server`)
rather than spawning it as a subprocess. This is a deliberate simplification:
the content server is started once, by hand, in its own terminal -- the same
way you'd start a database before starting an app that reads from it. If
it's not running, calls here fail with one clear, actionable error instead
of a hidden process quietly appearing per request.

Kept as a small set of standalone async functions rather than a class with
a mocked-out network layer, so it's obvious exactly which two calls the
Teaching Agent depends on.
"""
from __future__ import annotations
import json
from contextlib import asynccontextmanager

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

from learning_avatar.config import settings


class MCPServerUnavailableError(Exception):
    """Raised when the content-retrieval MCP server can't be reached. The
    fix is always the same: start it first, in its own terminal, with
    `uv run learning-avatar-mcp-server`, then start (or retry) the web app."""


@asynccontextmanager
async def _session():
    try:
        async with streamablehttp_client(settings.mcp_server_url) as (read, write, _get_session_id):
            async with ClientSession(read, write) as session:
                await session.initialize()
                yield session
    except MCPServerUnavailableError:
        raise
    except Exception as exc:
        raise MCPServerUnavailableError(
            f"Could not reach the content-retrieval MCP server at {settings.mcp_server_url}. "
            f"({exc}) Start it first with: uv run learning-avatar-mcp-server"
        ) from exc


async def fetch_lesson_record(subject: str, topic: str, concept: str, grade_band: str, theme: str) -> dict | None:
    """Returns the matching lesson record dict, or None if the content
    library has no pre-authored entry for this combination. Raises
    MCPServerUnavailableError if the MCP server itself isn't running --
    that's a different failure mode from "no record found" and callers
    should let it propagate rather than treat it as a cache miss."""
    async with _session() as session:
        result = await session.call_tool(
            "get_lesson_record",
            {"subject": subject, "topic": topic, "concept": concept, "grade_band": grade_band, "theme": theme},
        )
        payload = _first_json_payload(result)
        return payload["record"] if payload and payload.get("found") else None


async def fetch_concept_definition(concept_id: str) -> dict | None:
    async with _session() as session:
        result = await session.call_tool("get_concept_definition", {"concept_id": concept_id})
        payload = _first_json_payload(result)
        return payload["definition"] if payload and payload.get("found") else None


async def fetch_related_chunks(query_text: str, top_k: int = 5) -> list[dict]:
    """Search PDF ingestion store for chunks related to query_text.
    Returns [] when no embeddings exist yet — callers should treat this as
    a cache miss (fall through to LLM generation) rather than an error."""
    async with _session() as session:
        result = await session.call_tool(
            "find_related_chunks",
            {"query_text": query_text, "top_k": top_k},
        )
        payload = _first_json_payload(result)
        return payload["chunks"] if payload and payload.get("found") else []


def _first_json_payload(call_tool_result) -> dict | None:
    """MCP tool results come back as a list of content blocks; FastMCP
    returns structured tool output as JSON text in the first block."""
    for block in call_tool_result.content:
        if hasattr(block, "text"):
            return json.loads(block.text)
    return None
