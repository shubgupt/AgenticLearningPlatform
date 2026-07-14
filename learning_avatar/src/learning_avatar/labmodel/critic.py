"""
LabModel-Critic (plan doc section 2.1.3) -- the "Reviewer" role. For this
slice, a narrow and honest version of what the plan describes: curriculum
alignment, retrieval grounding, hallucination risk, and age-appropriateness
scoring are real evaluation work and NOT implemented here. This only checks
that the Worker's hint is non-empty and reasonably short. Anything that
fails is rejected, and the caller falls back to the static, hand-written
hint -- same "fail loudly, don't paper over it" pattern as
agents/root_agent.py's run_critic_check.
"""
from __future__ import annotations

MAX_HINT_CHARS = 400


def review_hint(hint_text: str) -> list[str]:
    """Returns a list of problems found (empty = pass)."""
    problems: list[str] = []
    if not hint_text or not hint_text.strip():
        problems.append("empty hint")
    if len(hint_text) > MAX_HINT_CHARS:
        problems.append(f"hint too long ({len(hint_text)} chars, max {MAX_HINT_CHARS})")
    return problems
