"""Deterministic validation of a generated lesson step.

Runs before any LLM critic call — cheap, free, and catches structural bugs
(wrong content_type, missing evaluation fields, an invented asset id, a
banned word slipping through) without spending a model call on them.
"""

ALLOWED_GENERATED_CONTENT_TYPES = {"slideshow", "story"}
ALLOWED_EVALUATION_TYPES = {"multiple_choice", "free_text", "dropdown"}


def _collect_text(step: dict) -> list[str]:
    """Every human-readable string in the step, for the negative-token scan."""
    texts: list[str] = []
    if step.get("scenario_text"):
        texts.append(step["scenario_text"])

    for slide in step.get("slides", []) or []:
        if slide.get("caption"):
            texts.append(slide["caption"])

    for panel in step.get("panels", []) or []:
        if panel.get("text"):
            texts.append(panel["text"])

    evaluation = step.get("evaluation") or {}
    if evaluation.get("question"):
        texts.append(evaluation["question"])
    if evaluation.get("hint"):
        texts.append(evaluation["hint"])
    for opt in evaluation.get("options", []) or []:
        if opt.get("text"):
            texts.append(opt["text"])
    for choice in evaluation.get("choices", []) or []:
        texts.append(choice)
    for ans in evaluation.get("accepted_answers", []) or []:
        texts.append(ans)

    return texts


def _validate_evaluation(evaluation: dict, errors: list[str]) -> None:
    eval_type = evaluation.get("type")
    if eval_type not in ALLOWED_EVALUATION_TYPES:
        errors.append(f"evaluation.type must be one of {ALLOWED_EVALUATION_TYPES}, got {eval_type!r}")
        return

    if not evaluation.get("question"):
        errors.append("evaluation.question is required")

    if eval_type == "multiple_choice":
        options = evaluation.get("options") or []
        if len(options) < 2:
            errors.append("multiple_choice evaluation needs at least 2 options")
        elif not any(opt.get("is_correct") for opt in options):
            errors.append("multiple_choice evaluation needs exactly one option with is_correct=true")
        for opt in options:
            if not opt.get("id") or not opt.get("text"):
                errors.append(f"multiple_choice option missing id/text: {opt!r}")

    elif eval_type == "free_text":
        if not evaluation.get("accepted_answers"):
            errors.append("free_text evaluation needs a non-empty accepted_answers list")

    elif eval_type == "dropdown":
        choices = evaluation.get("choices") or []
        correct = evaluation.get("correct_choice")
        if not choices:
            errors.append("dropdown evaluation needs a non-empty choices list")
        if not correct:
            errors.append("dropdown evaluation needs correct_choice")
        elif correct not in choices:
            errors.append("dropdown evaluation's correct_choice must be one of choices")


def _validate_assets(step: dict, asset_manifest: dict, errors: list[str]) -> None:
    known_ids = set(asset_manifest.keys())
    for slide in step.get("slides", []) or []:
        image_id = slide.get("image")
        if image_id and image_id not in known_ids:
            errors.append(f"slide references unknown asset id {image_id!r}")


def validate(step: dict, asset_manifest: dict, negative_constraint_token: str | None = None) -> tuple[bool, list[str]]:
    """Returns (is_valid, errors). Never raises — callers feed errors back into the next generation attempt."""
    errors: list[str] = []

    content_type = step.get("content_type")
    if content_type not in ALLOWED_GENERATED_CONTENT_TYPES:
        errors.append(
            f"content_type must be one of {ALLOWED_GENERATED_CONTENT_TYPES} for generated lessons, got {content_type!r}"
        )

    if content_type == "slideshow" and not step.get("slides"):
        errors.append("slideshow content_type requires a non-empty slides list")
    if content_type == "story" and not step.get("panels"):
        errors.append("story content_type requires a non-empty panels list")

    evaluation = step.get("evaluation")
    if not evaluation:
        errors.append("step is missing an evaluation block")
    else:
        _validate_evaluation(evaluation, errors)

    _validate_assets(step, asset_manifest, errors)

    if negative_constraint_token:
        token = negative_constraint_token.strip().lower()
        if token:
            for text in _collect_text(step):
                if token in text.lower():
                    errors.append(f"generated text contains the forbidden negative_constraint_token {negative_constraint_token!r}")
                    break

    return (len(errors) == 0, errors)
