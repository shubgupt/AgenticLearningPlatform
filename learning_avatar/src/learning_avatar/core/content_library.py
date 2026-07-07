"""
This module IS what used to be the `LESSON_LIBRARY` JavaScript array in
adaptive_learning_avatar_demo_v4.html -- moved server-side and reframed as
what it actually is architecturally: the Teaching Agent's default input.
Per teaching_agent_prompt.md section 3 ("Lesson Plan Override"), this is
the pre-authored content checked *before* falling back to live generation.

Nothing in the frontend has its own copy of this data anymore. The browser
only ever sees a lesson record after asking for one over the network -- see
mcp/server.py (which wraps these functions as MCP tools) and
mcp/client.py + agents/teaching_agent.py (which call those tools).

Deliberately a thin data-access module: load once at import time, expose
three lookup functions, no caching layer, no database. 12 records easily
fits in memory; revisit this if/when the library grows large enough that
loading it all eagerly stops being free.
"""
from __future__ import annotations
import json

from learning_avatar.config import settings

with open(settings.content_dir / "newtons_laws_lesson_library.json") as f:
    _LIBRARY: list[dict] = json.load(f)

with open(settings.content_dir / "concept_definitions.json") as f:
    _CONCEPT_DEFS: list[dict] = json.load(f)


def get_lesson_record(subject: str, topic: str, concept: str, grade_band: str, theme: str) -> dict | None:
    """Exact-match lookup. Returns None (not an exception) on a miss --
    a miss is an expected, normal outcome (it means 'generate this one'),
    not an error condition."""
    for record in _LIBRARY:
        if (
            record["subject"] == subject
            and record["topic"] == topic
            and record["concept"] == concept
            and record["gradeBand"] == grade_band
            and record["theme"] == theme
        ):
            return record
    return None


def list_available_combinations() -> list[dict]:
    return [
        {"concept": r["concept"], "gradeBand": r["gradeBand"], "theme": r["theme"]}
        for r in _LIBRARY
    ]


def get_concept_definition(concept_id: str) -> dict | None:
    for definition in _CONCEPT_DEFS:
        if definition["conceptId"] == concept_id:
            return definition
    return None
