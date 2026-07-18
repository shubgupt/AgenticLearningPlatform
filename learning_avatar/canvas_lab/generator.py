"""Lesson+evaluation generator — one combined LLM role (see spec section 4:
'Roles: 3, not 4' — the question naturally follows from the scenario, so
plan and evaluation are generated together rather than as two round-trips).
"""

import json
import re

from llm_client import LLMClient, record_llm_call

SYSTEM_PROMPT = """You are a lesson-content generator for a middle-school science
platform. You output exactly one JSON object describing a single lesson step —
no prose, no markdown code fences, just the JSON object.

Hard rules:
- "content_type" MUST be either "slideshow" or "story". Never "interactive_scene".
- For "slideshow": include a "slides" array of {"image": <asset id>, "caption": <string>}.
  Each "image" MUST be one of the allowed asset ids given below — never invent a URL or id.
- For "story": include a "panels" array of {"speaker": <string>, "text": <string>}.
- Always include a top-level "scenario_text" (1-2 sentences) and an "evaluation" block.
- "evaluation.type" MUST be exactly one of: "multiple_choice", "free_text", "dropdown".
  - multiple_choice: "options" is a list of {"id": "A"/"B"/"C"/..., "text": ...},
    with exactly one option carrying "is_correct": true.
  - free_text: "accepted_answers" is a non-empty list of acceptable answer strings.
  - dropdown: "choices" is a non-empty list of strings, and "correct_choice" is
    exactly one of those strings.
  - Always include "evaluation.question" and a short "evaluation.hint".
- Where it reads naturally in slide captions or story panel text, you may use the
  personalization placeholders {{favorite_sport}} and {{friend_name}} verbatim
  (they are substituted per-student after generation — do not resolve them yourself).
- Never include the forbidden token given below anywhere in your output, in any form.
"""


class GenerationParseError(Exception):
    pass


def _build_user_prompt(
    *,
    skill: str,
    modality: str,
    mastery_pct: float | None,
    prereq_threshold: float | None,
    negative_constraint_token: str | None,
    asset_manifest: dict,
    prior_feedback: list[str] | None,
) -> str:
    lines = [
        f"Target skill: {skill}",
        f"Modality: {modality}",
        f"Student mastery so far: {mastery_pct if mastery_pct is not None else 'unknown'}%",
        f"Prerequisite mastery threshold: {prereq_threshold if prereq_threshold is not None else 'unknown'}%",
        f"Allowed asset ids for slide images: {sorted(asset_manifest.keys())}",
    ]
    if negative_constraint_token:
        lines.append(f"Forbidden token (must not appear anywhere): {negative_constraint_token!r}")
    if prior_feedback:
        lines.append(
            "Your previous attempt was rejected for these reasons — fix all of them: "
            + "; ".join(prior_feedback)
        )
    lines.append("Return the JSON object now.")
    return "\n".join(lines)


def _parse_json_response(raw: str) -> dict:
    text = raw.strip()
    fence_match = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.DOTALL)
    if fence_match:
        text = fence_match.group(1)
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise GenerationParseError(f"model did not return valid JSON: {exc}") from exc


def generate(
    client: LLMClient,
    *,
    request_id: int | None,
    trace_id: str,
    skill: str,
    modality: str,
    mastery_pct: float | None,
    prereq_threshold: float | None,
    negative_constraint_token: str | None,
    asset_manifest: dict,
    prior_feedback: list[str] | None = None,
) -> dict:
    user_prompt = _build_user_prompt(
        skill=skill,
        modality=modality,
        mastery_pct=mastery_pct,
        prereq_threshold=prereq_threshold,
        negative_constraint_token=negative_constraint_token,
        asset_manifest=asset_manifest,
        prior_feedback=prior_feedback,
    )
    raw_output = record_llm_call(
        client,
        role="lesson_generator",
        request_id=request_id,
        system=SYSTEM_PROMPT,
        user=user_prompt,
        trace_id=trace_id,
    )
    return _parse_json_response(raw_output)
