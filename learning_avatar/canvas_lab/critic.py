"""LLM lesson critic — content relevance + student-profile safety rubric.

Unlike the LearningAvatar reference's critic (a hardcoded-score banned-word
filter dressed up as pedagogical review), this critic makes a real LLM call
and returns a structured, per-dimension verdict rather than a single score.
The negative-constraint-token check itself stays deterministic (see
validator.py) and runs before this is ever invoked — this critic's job is
the nuanced judgment layer on top: is this actually good, relevant, and
age-appropriate content.
"""

import json
import re

from llm_client import LLMClient, record_llm_call

SYSTEM_PROMPT = """You are a pedagogical content critic reviewing a draft lesson
step for a middle-school science platform. You output exactly one JSON object —
no prose, no markdown fences.

Score the draft on two dimensions, each 0-100:
- "relevance_score": does the content and evaluation faithfully address the
  target skill and modality, without being off-topic or testing something else?
- "safety_score": is this age-appropriate and safe for a student of the given
  age/grade — no unsafe, frightening, or inappropriate content or examples?

Then decide:
- "decision": "APPROVED" if both scores are 70 or higher, otherwise "REJECTED".
- "feedback": a short, specific explanation covering both dimensions, written
  so the generator can act on it directly if this is rejected.

Return: {"relevance_score": <int>, "safety_score": <int>, "decision": "APPROVED"|"REJECTED", "feedback": <string>}
"""


class CriticParseError(Exception):
    pass


def _parse_json_response(raw: str) -> dict:
    text = raw.strip()
    fence_match = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.DOTALL)
    if fence_match:
        text = fence_match.group(1)
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise CriticParseError(f"critic did not return valid JSON: {exc}") from exc


def _build_user_prompt(
    *,
    skill: str,
    modality: str,
    draft_step: dict,
    student_age: int | None,
    student_grade: str | None,
    negative_constraint_token: str | None,
) -> str:
    lines = [
        f"Target skill: {skill}",
        f"Modality: {modality}",
        # Coarse, grade-band-level profile only — this generation is cached and
        # reused across students (see spec section 5), so the safety judgment
        # needs to generalize across a grade band, not bind to one student's
        # full personal profile (favorite sport/friends are irrelevant here).
        f"Requesting student's age/grade (for the safety_score judgment only): age={student_age}, grade={student_grade}",
    ]
    if negative_constraint_token:
        lines.append(f"Forbidden token (must not appear anywhere in the draft): {negative_constraint_token!r}")
    lines.append("Draft step JSON to review:")
    lines.append(json.dumps(draft_step, ensure_ascii=False))
    lines.append("Return your verdict JSON now.")
    return "\n".join(lines)


def review(
    client: LLMClient,
    *,
    request_id: int | None,
    trace_id: str,
    skill: str,
    modality: str,
    draft_step: dict,
    student_age: int | None,
    student_grade: str | None,
    negative_constraint_token: str | None = None,
) -> dict:
    user_prompt = _build_user_prompt(
        skill=skill,
        modality=modality,
        draft_step=draft_step,
        student_age=student_age,
        student_grade=student_grade,
        negative_constraint_token=negative_constraint_token,
    )
    raw_output = record_llm_call(
        client,
        role="lesson_critic",
        request_id=request_id,
        system=SYSTEM_PROMPT,
        user=user_prompt,
        trace_id=trace_id,
    )
    return _parse_json_response(raw_output)
