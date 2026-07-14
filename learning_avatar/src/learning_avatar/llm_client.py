"""
One narrow interface for "ask a model to generate text," with two
implementations behind it. Every agent depends on the *interface*
(LLMClient), never on `openai` directly — that indirection is what lets
tests swap in MockLLMClient and exercise the full agent pipeline with zero
network calls and zero cost (this is the "mock objects / stubs" testing goal,
built in from day one rather than bolted on later).
"""
from __future__ import annotations
import abc
import json

from learning_avatar.config import settings


class LLMClient(abc.ABC):
    @abc.abstractmethod
    async def complete(self, system_prompt: str, user_message: str, model: str) -> str:
        """Return raw text completion for a single-turn system+user call."""
        raise NotImplementedError


class OpenAILLMClient(LLMClient):
    """Real calls to the OpenAI API. Only imports the SDK lazily so the
    rest of the app can run in mock mode with the package not even installed
    yet, if you're still setting things up."""

    def __init__(self):
        import openai  # local import on purpose, see docstring above
        self._client = openai.AsyncOpenAI(api_key=settings.openai_api_key)

    async def complete(self, system_prompt: str, user_message: str, model: str) -> str:
        response = await self._client.chat.completions.create(
            model=model,
            max_tokens=2000,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
        )
        return response.choices[0].message.content


class MockLLMClient(LLMClient):
    """
    Deterministic stand-in used by LLM_MODE=mock and by every test. Instead of
    calling a model, it returns a syntactically-valid but obviously-fake
    LessonScreen/QuizItem so you can exercise the Root -> Teaching -> Critic
    pipeline end to end without an API key or any cost.

    This is intentionally dumb. Its only job is "return something shaped
    right," not "return something good" -- quality is what the real model
    (and later, DSPy optimization) is responsible for.
    """

    async def complete(self, system_prompt: str, user_message: str, model: str) -> str:
        try:
            payload = json.loads(user_message)
        except (json.JSONDecodeError, AttributeError):
            payload = None

        if not isinstance(payload, dict) or "subjectContext" not in payload:
            # Not a lesson-generation call (teaching_agent always sends JSON
            # with a subjectContext key) -- this is some other, plain-text
            # use of the LLMClient interface, e.g. labmodel/worker.py's hint
            # generation. Return a short deterministic mock string instead
            # of trying to force it into the LessonScreen shape below.
            return ("[mock hint] Compare the two things being described directly -- "
                    "which one is bigger, and what does that tell you about the direction of motion?")

        concept = payload.get("subjectContext", {}).get("concept", "unknown_concept")
        grade_band = payload.get("subjectContext", {}).get("gradeBand", "grade5")
        theme = payload.get("subjectContext", {}).get("theme", "soccer")

        fake_record = {
            "id": f"{concept}_{grade_band}_{theme}_MOCK",
            "subject": "physics",
            "topic": "newtons_laws_of_motion",
            "concept": concept,
            "gradeBand": grade_band,
            "theme": theme,
            "hook": {"kicker": "Mock hook", "text": "[mock output] a themed real-world tie-in would go here.", "options": ["Continue"]},
            "sandbox": {"kicker": "Mock sandbox", "prompt": "[mock output]", "scene_ref": "rolling_object_scene", "token": "❔", "options": ["Try it"]},
            "concept_screen": {"kicker": "Mock concept", "text_by_grade": {grade_band: "[mock output] formal concept text."}},
            "diagnostic": {
                "kicker": "Mock diagnostic",
                "prompt_by_grade": {grade_band: "[mock output] one check question."},
                "options": [
                    {"label": "Correct answer", "correct": True, "value": "a"},
                    {"label": "Wrong answer", "correct": False, "value": "b", "misconception": "mock_misconception"},
                ],
            },
            "mistake_genome": {
                "mock_misconception": {"message": "[mock output] non-judgmental correction.", "recommended_support": ["show_picture"]}
            },
            "image_prompt": None,
            "image_alt": None,
        }
        return json.dumps(fake_record)


def get_llm_client() -> LLMClient:
    """FastAPI dependency. Swap LLM_MODE in .env to flip real vs mock without
    touching a single line of agent code."""
    if settings.llm_mode == "live":
        return OpenAILLMClient()
    return MockLLMClient()
