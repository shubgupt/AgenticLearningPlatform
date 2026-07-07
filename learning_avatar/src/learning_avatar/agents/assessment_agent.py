"""
Assessment Agent -- generates a standalone checkpoint quiz.

Same shape as the Teaching Agent deliberately: try cheap/free retrieval
first (here, reusing the diagnostic questions already embedded in
pre-authored lesson records as a "review quiz"), fall back to the LLM using
assessment_agent_prompt.md when asked for something the library can't
answer (e.g. a brand-new set of harder questions).

This one is intentionally left thinner than teaching_agent.py -- extend the
`_generate_via_llm` path following assessment_agent_prompt.md section 2
(input/output contract) as your next exercise once the Teaching Agent path
is working end to end.
"""
from __future__ import annotations
import json
import os
import uuid

from learning_avatar.config import settings
from learning_avatar.llm_client import LLMClient
from learning_avatar.mcp import client as content_retrieval
from learning_avatar.core.schemas import AssessmentResponse, MistakeGenomeEntry, QuizItem, QuizOption, SubjectContext

_PROMPT_PATH = settings.prompts_dir / "assessment_agent_prompt.md"


def _load_system_prompt() -> str:
    with open(_PROMPT_PATH) as f:
        return f.read()


async def generate_review_quiz(ctx: SubjectContext, concepts: list[str], llm: LLMClient) -> AssessmentResponse:
    """Builds a short recap quiz out of already-covered concepts, reusing
    each concept's pre-authored diagnostic question via the same MCP server
    the Teaching Agent uses -- no new content is generated for the common
    case, which is the whole point of checking the library first."""
    items: list[QuizItem] = []
    mistake_map: dict[str, MistakeGenomeEntry] = {}

    for concept in concepts:
        record = await content_retrieval.fetch_lesson_record(
            subject=ctx.subject, topic=ctx.topic, concept=concept,
            grade_band=ctx.gradeBand, theme=ctx.theme,
        )
        if record is None:
            continue
        prompt = record["diagnostic"]["prompt_by_grade"].get(ctx.gradeBand) \
            or next(iter(record["diagnostic"]["prompt_by_grade"].values()))
        options = [QuizOption(**opt) for opt in record["diagnostic"]["options"]]
        items.append(QuizItem(id=f"recap_{concept}", prompt=prompt, gradeBand=ctx.gradeBand, options=options))
        for key, entry in record["mistake_genome"].items():
            mistake_map[key] = MistakeGenomeEntry(**entry)

    return AssessmentResponse(
        assessment_id=f"assess_{uuid.uuid4().hex[:8]}",
        items=items,
        mistake_genome_map=mistake_map,
    )


async def _generate_via_llm(ctx: SubjectContext, llm: LLMClient) -> AssessmentResponse:
    """Stub for the "no library match" path -- see assessment_agent_prompt.md
    section 2 for the exact input/output contract to implement here."""
    system_prompt = _load_system_prompt()
    user_message = json.dumps({
        "subjectContext": ctx.model_dump(),
        "numQuestions": 3,
        "difficultyHint": "steady",
        "assessmentType": "standalone_checkpoint",
    })
    raw = await llm.complete(system_prompt, user_message, model=settings.assessment_agent_model)
    # NOTE: unlike teaching_agent.py, this path is not yet parsed/validated --
    # left as a deliberate TODO so you have a second, smaller place to
    # practice the "generate -> validate -> retry" pattern yourself.
    raise NotImplementedError("Parse `raw` into AssessmentResponse and validate, mirroring teaching_agent.py")
