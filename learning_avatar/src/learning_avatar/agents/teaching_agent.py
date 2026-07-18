"""
Teaching Agent -- generates (or retrieves) one LessonScreen.

This is a plain async function, not a class, not a framework "Agent" object.
The whole orchestration pattern is visible right here:

    1. Try the MCP content-retrieval server first (fast, free, pre-vetted).
    2. Try the PDF ingestion store (chunks embedded from uploaded PDFs).
    3. If nothing matches, fall back to an LLM call using
       teaching_agent_prompt.md as the system prompt.
    4. Either way, validate the result against the LessonScreen schema
       before returning it -- Root Agent's critic gate depends on this
       agent never handing back something malformed.

This mirrors teaching_agent_prompt.md section 3 exactly: check the library,
generate only if missing.
"""
from __future__ import annotations
import json
import logging

from pydantic import ValidationError

from learning_avatar.config import settings
from learning_avatar.llm_client import LLMClient
from learning_avatar.mcp import client as content_retrieval
from learning_avatar.core.schemas import LessonResponse, LessonScreen, SubjectContext

_PROMPT_PATH = settings.prompts_dir / "teaching_agent_prompt.md"
logger = logging.getLogger(__name__)


def _load_system_prompt() -> str:
    with open(_PROMPT_PATH) as f:
        return f.read()


async def generate_lesson(ctx: SubjectContext, llm: LLMClient) -> LessonResponse:
    # Step 1: try the pre-authored library via MCP — free and instant.
    record_dict = await content_retrieval.fetch_lesson_record(
        subject=ctx.subject, topic=ctx.topic, concept=ctx.concept,
        grade_band=ctx.gradeBand, theme=ctx.theme,
    )
    if record_dict is not None:
        return LessonResponse(record=LessonScreen.model_validate(record_dict), content_source="library")

    # Step 2: search PDF ingestion store for related chunks.
    # If relevant PDF content has been ingested, use it to ground generation.
    query = f"{ctx.subject} {ctx.topic} {ctx.concept} {ctx.gradeBand} {ctx.theme}"
    pdf_chunks: list[dict] = []
    try:
        pdf_chunks = await content_retrieval.fetch_related_chunks(query, top_k=3)
    except Exception as exc:
        logger.warning("PDF chunk search failed (non-fatal): %s", exc)

    # Step 3: fetch concept definition to ground generation regardless of source.
    concept_def = await content_retrieval.fetch_concept_definition(ctx.concept)

    system_prompt = _load_system_prompt()
    user_message = json.dumps({
        "call": "generate_lesson",
        "subjectContext": ctx.model_dump(),
        "conceptDefinition": concept_def,
        "pdfChunks": pdf_chunks,  # empty list when no PDF content exists
    })

    raw = await llm.complete(system_prompt, user_message, model=settings.teaching_agent_model)

    try:
        record_dict = json.loads(raw)
        record = LessonScreen.model_validate(record_dict)
    except (json.JSONDecodeError, ValidationError) as exc:
        raise TeachingAgentError(f"Teaching Agent returned malformed content: {exc}") from exc

    # Report content_source="pdf" when generation was grounded in PDF chunks.
    source = "pdf" if pdf_chunks else "generated"
    return LessonResponse(record=record, content_source=source)


class TeachingAgentError(Exception):
    """Raised when the Teaching Agent's output fails schema validation.
    The Root Agent should catch this, retry once, then fall back to a
    'this lesson isn't ready yet' screen rather than show broken content."""
