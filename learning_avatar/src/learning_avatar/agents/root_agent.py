"""
Root Agent -- orchestration only. Per root_agent_prompt.md, this module
never writes lesson or quiz content itself; it owns session state, decides
when to call which sub-agent, and runs a (deliberately small, for now)
critic check on whatever comes back before it's allowed to reach the
student.

Notice what's NOT here: no prompt-engineering for lesson content, no
physics. If you find yourself wanting to write concept text inside this
file, that's a sign it belongs in teaching_agent.py instead -- keeping that
boundary sharp is the actual architectural skill this project is meant to
practice.
"""
from __future__ import annotations

from learning_avatar.agents import teaching_agent
from learning_avatar.llm_client import LLMClient
from learning_avatar.core.schemas import LessonResponse, SessionState, SubjectContext


def run_critic_check(lesson: LessonResponse) -> list[str]:
    """A first, intentionally small pass at system_prompt.md's 12-point
    critic checklist. Returns a list of problems found (empty = pass).
    Extend this as you add more checks -- each one should be a single,
    named, testable reason a screen could be rejected."""
    problems: list[str] = []
    record = lesson.record

    if not record.diagnostic.get("options"):
        problems.append("diagnostic has no options")

    for opt in record.diagnostic.get("options", []):
        if not opt.get("correct") and not opt.get("misconception"):
            problems.append(f"incorrect option '{opt.get('label')}' has no misconception mapping")
        if not opt.get("correct") and opt.get("misconception") not in record.mistake_genome:
            problems.append(f"misconception '{opt.get('misconception')}' has no mistake_genome entry")

    if record.image_prompt and not record.image_alt:
        problems.append("image_prompt present without image_alt")

    return problems


async def get_lesson(session: SessionState, ctx: SubjectContext, llm: LLMClient) -> LessonResponse:
    """The one orchestration call this scaffold implements end to end:
    ask the Teaching Agent for a lesson, critic-check it, retry once on
    failure, and update session state either way."""
    session.subjectContext = ctx

    lesson = await teaching_agent.generate_lesson(ctx, llm)
    problems = run_critic_check(lesson)

    if problems:
        # One retry, per root_agent_prompt.md section 6. If it fails twice,
        # let the caller (main.py) decide how to degrade gracefully --
        # Root Agent's job is to try, not to paper over a real problem.
        lesson = await teaching_agent.generate_lesson(ctx, llm)
        problems = run_critic_check(lesson)
        if problems:
            raise CriticRejectedError(problems)

    session.xp += 150
    return lesson


def record_diagnostic_result(session: SessionState, concept: str, correct: bool, misconception: str | None) -> None:
    """Root Agent owns mistakeGenome -- Teaching/Assessment agents only ever
    hand back structured content, they never touch session state directly."""
    session.xp += 180 if correct else 40
    session.mistakeGenome.append({
        "checkpoint": concept,
        "result": "understood" if correct else "misconception_detected",
        "misconception": misconception,
    })


class CriticRejectedError(Exception):
    """Raised when a sub-agent's output fails the critic check twice in a
    row. main.py should catch this and return a graceful fallback screen,
    never a 500 with a stack trace a student could see."""
    def __init__(self, problems: list[str]):
        self.problems = problems
        super().__init__(f"Critic rejected content: {problems}")
