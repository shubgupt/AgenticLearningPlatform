"""
Teaching Agent -- generates (or retrieves) one LessonScreen.

This is a plain async function, not a class, not a framework "Agent" object.
The whole orchestration pattern is visible right here:

    1. Try the MCP content-retrieval server first (fast, free, pre-vetted).
    2. If nothing matches, fall back to an LLM call using
       teaching_agent_prompt.md as the system prompt.
    3. Either way, validate the result against the LessonScreen schema
       before returning it -- Root Agent's critic gate depends on this
       agent never handing back something malformed.

This mirrors teaching_agent_prompt.md section 3 exactly: check the library,
generate only if missing.
"""
from __future__ import annotations
import json
import os

from pydantic import ValidationError

from learning_avatar.config import settings
from learning_avatar.llm_client import LLMClient
from learning_avatar.mcp import client as content_retrieval
from learning_avatar.core.schemas import LessonResponse, LessonScreen, SubjectContext

_PROMPT_PATH = settings.prompts_dir / "teaching_agent_prompt.md"


def _load_system_prompt() -> str:
    with open(_PROMPT_PATH) as f:
        return f.read()


async def generate_lesson(ctx: SubjectContext, llm: LLMClient) -> LessonResponse:
    # Step 1: try the MCP server -- this is the real MCP call, not a stub.
    record_dict = await content_retrieval.fetch_lesson_record(
        subject=ctx.subject, topic=ctx.topic, concept=ctx.concept,
        grade_band=ctx.gradeBand, theme=ctx.theme,
    )
    if record_dict is not None:
        return LessonResponse(record=LessonScreen.model_validate(record_dict), content_source="library")

    # Step 2: nothing pre-authored -- generate fresh, grounded in the
    # concept's ground-truth definition (also fetched over MCP) so the model
    # is phrasing known-correct physics, not inventing it.
    concept_def = await content_retrieval.fetch_concept_definition(ctx.concept)

    system_prompt = _load_system_prompt()
    user_message = json.dumps({
        "call": "generate_lesson",
        "subjectContext": ctx.model_dump(),
        "conceptDefinition": concept_def,
    })

    raw = await llm.complete(system_prompt, user_message, model=settings.teaching_agent_model)

    # Step 3: validate before this ever reaches the Root Agent's critic gate.
    try:
        record_dict = json.loads(raw)
        record = LessonScreen.model_validate(record_dict)
    except (json.JSONDecodeError, ValidationError) as exc:
        raise TeachingAgentError(f"Teaching Agent returned malformed content: {exc}") from exc

    return LessonResponse(record=record, content_source="generated")


class TeachingAgentError(Exception):
    """Raised when the Teaching Agent's output fails schema validation.
    The Root Agent should catch this, retry once, then fall back to a
    'this lesson isn't ready yet' screen rather than show broken content."""
