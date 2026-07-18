"""
Phase 5: Generate 7 learning card types per chunk using a local ollama model.

The ollama server (http://localhost:11434) speaks the OpenAI protocol, so we
reuse the openai SDK that is already a dependency. Cards are validated with
Pydantic before being returned so callers always receive well-formed data.

Run before use:
    ollama serve &
    ollama pull llama3.2
"""
from __future__ import annotations

import json
import logging
import uuid

from .schemas import CardType, LearningCard, QuizContent

logger = logging.getLogger(__name__)

_CARD_TYPES = [ct.value for ct in CardType]

_SYSTEM_PROMPT = """\
You are a learning card generator for an educational platform.

Given a text chunk from a learning document, generate EXACTLY 7 learning cards — one of each type listed below.

Return ONLY a valid JSON object — no markdown fences, no explanation, nothing else.

Required JSON structure:
{
  "cards": [
    {"card_type": "standard",     "title": "<concise title>", "body": "<2-3 sentence explanation for average learner>"},
    {"card_type": "simplified",   "title": "<simple title>",  "body": "<2 sentence explanation for beginners, plain language>"},
    {"card_type": "analogy",      "title": "<analogy title>", "body": "<explain using a real-world comparison>"},
    {"card_type": "hint",         "title": "<hint title>",    "body": "<1-2 sentence memory aid or tip>"},
    {"card_type": "quiz",         "title": "<quiz title>",    "body": "<brief intro to the question>",
     "quiz": {"question": "<clear question>", "options": ["<correct answer>", "<wrong1>", "<wrong2>", "<wrong3>"], "correct_index": 0, "hint": "<hint if stuck>"}},
    {"card_type": "teacher_note", "title": "<teacher note title>", "body": "<professional note about common misconceptions or pedagogy>"},
    {"card_type": "recap",        "title": "<recap title>",   "body": "<1-2 sentence summary of the key takeaway>"}
  ]
}

IMPORTANT:
- Output EXACTLY 7 cards, one per type: standard, simplified, analogy, hint, quiz, teacher_note, recap
- All 7 card_type values are required — do not skip any
- body: 2-3 sentences max (except teacher_note: can be 3-4)
- quiz.options: exactly 4 strings, correct answer MUST be at index 0
- Return ONLY the JSON, starting with { and ending with }
"""


def generate(chunks: list) -> list[LearningCard]:
    """Generate 7 cards per chunk. Returns all cards flat in insertion order."""
    try:
        from openai import OpenAI
    except ImportError:
        raise RuntimeError("openai package required — run: uv sync")

    from learning_avatar.config import settings

    client = OpenAI(base_url=settings.ollama_base_url, api_key="ollama")

    all_cards: list[LearningCard] = []
    for chunk in chunks:
        cards = _generate_for_chunk(client, settings.ollama_model, chunk)
        all_cards.extend(cards)

    return all_cards


def _generate_for_chunk(client, model: str, chunk) -> list[LearningCard]:
    user_text = chunk.text[:4000]  # guard against oversized chunks

    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_text},
            ],
            response_format={"type": "json_object"},
            temperature=0.3,
        )
        raw = resp.choices[0].message.content or "{}"
    except Exception as exc:
        logger.error("ollama call failed for chunk %s: %s", chunk.chunk_id, exc)
        return _stub_cards(chunk.chunk_id)

    return _parse_cards(raw, chunk.chunk_id)


def _parse_cards(raw_json: str, chunk_id: str) -> list[LearningCard]:
    try:
        data = json.loads(raw_json)
        cards_data = data.get("cards", [])
    except json.JSONDecodeError:
        logger.warning("Invalid JSON from ollama for chunk %s; using stubs", chunk_id)
        return _stub_cards(chunk_id)

    cards: list[LearningCard] = []
    seen_types: set[str] = set()

    for item in cards_data:
        try:
            ct = CardType(item.get("card_type", ""))
        except ValueError:
            continue

        if ct.value in seen_types:
            continue
        seen_types.add(ct.value)

        quiz_content: QuizContent | None = None
        if ct == CardType.quiz and "quiz" in item:
            q = item["quiz"]
            try:
                quiz_content = QuizContent(
                    question=q.get("question", ""),
                    options=q.get("options", [])[:4],
                    correct_index=int(q.get("correct_index", 0)),
                    hint=q.get("hint", ""),
                )
            except Exception:
                pass

        cards.append(LearningCard(
            card_id=str(uuid.uuid4()),
            chunk_id=chunk_id,
            card_type=ct,
            title=str(item.get("title", ct.value.replace("_", " ").title())),
            body=str(item.get("body", "")),
            quiz=quiz_content,
        ))

    # Fill in any missing card types with stubs so callers always get 7 cards
    for ct in CardType:
        if ct.value not in seen_types:
            logger.warning("Missing card type %s from ollama; using stub", ct.value)
            cards.append(_stub_card(chunk_id, ct))

    return cards


def _stub_cards(chunk_id: str) -> list[LearningCard]:
    return [_stub_card(chunk_id, ct) for ct in CardType]


def _stub_card(chunk_id: str, ct: CardType) -> LearningCard:
    quiz = None
    if ct == CardType.quiz:
        quiz = QuizContent(
            question="What is the main idea?",
            options=["Option A", "Option B", "Option C", "Option D"],
            correct_index=0,
            hint="Think about the core concept.",
        )
    return LearningCard(
        card_id=str(uuid.uuid4()),
        chunk_id=chunk_id,
        card_type=ct,
        title=ct.value.replace("_", " ").title(),
        body="[Card content will be generated when ollama is running]",
        quiz=quiz,
    )
