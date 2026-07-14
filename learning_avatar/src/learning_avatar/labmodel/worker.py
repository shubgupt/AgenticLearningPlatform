"""
LabModel-Worker (plan doc section 2.1.3) -- the "Actor" role: generates a
draft that LabModel-Critic (critic.py) then reviews before it's allowed to
reach the student. This wraps the existing LLMClient interface
(learning_avatar/llm_client.py) rather than replacing it -- MockLLMClient
still works here with zero cost/setup, same as everywhere else in this repo.

Scoped to exactly one job right now: generating a single task hint. The
plan doc's Worker also owns lesson/diagnostic/remediation generation, but
those already exist and work as teaching_agent.py / assessment_agent.py --
this module isn't a replacement for either, just the new piece for the
orchestrator-driven hint slice.

NOT implemented (plan doc 4.2, "Softmax Temperature Scaling"): actual
decoding-temperature control per grade band. LLMClient.complete() doesn't
expose a temperature parameter yet, so this only *describes* the intended
tone/register to the model via the prompt. Extending LLMClient's interface
to accept temperature would touch code other tests already depend on, so
it's left as a deliberate next step, not done here.
"""
from __future__ import annotations

from learning_avatar.llm_client import LLMClient

HINT_WORKER_SYSTEM_PROMPT = """You are the LabModel-Worker for an adaptive physics tutoring platform.
Generate ONE short hint (1-2 sentences, no more) for the student's current task.
Rules:
- Never give away the final answer outright -- nudge toward the reasoning, don't state it.
- Match the vocabulary and complexity of the stated grade band.
- If attention or motivation is low, keep the hint shorter and more concrete.
- Return plain text only, no markdown, no JSON.
"""


async def generate_hint(
    llm: LLMClient,
    model: str,
    task_question: str,
    grade_band: str,
    attention_score: int,
    motivation_score: int,
    static_hint_fallback: str,
) -> str:
    user_message = (
        f"Grade band: {grade_band}\n"
        f"Task question: {task_question}\n"
        f"Student attention (0-10): {attention_score}\n"
        f"Student motivation (0-10): {motivation_score}\n"
        f"A previously hand-written hint for reference (do not just copy it verbatim): "
        f"{static_hint_fallback}\n"
        f"Write one new short hint."
    )
    return await llm.complete(HINT_WORKER_SYSTEM_PROMPT, user_message, model=model)
