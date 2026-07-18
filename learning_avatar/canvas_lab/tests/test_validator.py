import validator

ASSET_MANIFEST = {
    "bg.stadium": "/static/mock-assets/backgrounds/scene_stadium.png",
    "bg.warehouse": "/static/mock-assets/backgrounds/scene_force.png",
    "bg.launchpad": "/static/mock-assets/backgrounds/scene_launchpad.png",
}

VALID_SLIDESHOW_STEP = {
    "content_type": "slideshow",
    "scenario_text": "A quick recap before the challenge.",
    "slides": [{"image": "bg.stadium", "caption": "Sample caption."}],
    "evaluation": {
        "type": "multiple_choice",
        "question": "What is 1+1?",
        "hint": "Count on fingers.",
        "options": [
            {"id": "A", "text": "1"},
            {"id": "B", "text": "2", "is_correct": True},
        ],
    },
}

VALID_STORY_STEP = {
    "content_type": "story",
    "scenario_text": "Debrief time.",
    "panels": [{"speaker": "Coach", "text": "Nice work."}],
    "evaluation": {
        "type": "free_text",
        "question": "What is the net force when two equal forces oppose?",
        "hint": "They cancel.",
        "accepted_answers": ["0", "0 n", "zero"],
    },
}


def test_valid_slideshow_step_passes():
    is_valid, errors = validator.validate(VALID_SLIDESHOW_STEP, ASSET_MANIFEST)
    assert is_valid, errors


def test_valid_story_step_passes():
    is_valid, errors = validator.validate(VALID_STORY_STEP, ASSET_MANIFEST)
    assert is_valid, errors


def test_interactive_scene_content_type_rejected():
    step = {**VALID_SLIDESHOW_STEP, "content_type": "interactive_scene"}
    is_valid, errors = validator.validate(step, ASSET_MANIFEST)
    assert not is_valid
    assert any("content_type" in e for e in errors)


def test_free_text_missing_accepted_answers_rejected():
    step = {
        "content_type": "story",
        "panels": [{"speaker": "Coach", "text": "Hi"}],
        "evaluation": {"type": "free_text", "question": "How much?", "accepted_answers": []},
    }
    is_valid, errors = validator.validate(step, ASSET_MANIFEST)
    assert not is_valid
    assert any("accepted_answers" in e for e in errors)


def test_multiple_choice_without_correct_option_rejected():
    step = {
        **VALID_SLIDESHOW_STEP,
        "evaluation": {
            "type": "multiple_choice",
            "question": "x?",
            "options": [{"id": "A", "text": "1"}, {"id": "B", "text": "2"}],
        },
    }
    is_valid, errors = validator.validate(step, ASSET_MANIFEST)
    assert not is_valid
    assert any("is_correct" in e for e in errors)


def test_dropdown_correct_choice_not_in_choices_rejected():
    step = {
        **VALID_SLIDESHOW_STEP,
        "evaluation": {
            "type": "dropdown",
            "question": "x?",
            "choices": ["A", "B"],
            "correct_choice": "C",
        },
    }
    is_valid, errors = validator.validate(step, ASSET_MANIFEST)
    assert not is_valid
    assert any("correct_choice" in e for e in errors)


def test_unknown_asset_id_rejected():
    step = {**VALID_SLIDESHOW_STEP, "slides": [{"image": "bg.nonexistent", "caption": "x"}]}
    is_valid, errors = validator.validate(step, ASSET_MANIFEST)
    assert not is_valid
    assert any("unknown asset id" in e for e in errors)


def test_negative_constraint_token_present_rejected():
    step = {**VALID_SLIDESHOW_STEP, "scenario_text": "This mentions bananas explicitly."}
    is_valid, errors = validator.validate(step, ASSET_MANIFEST, negative_constraint_token="bananas")
    assert not is_valid
    assert any("forbidden" in e for e in errors)


def test_negative_constraint_token_absent_passes():
    is_valid, errors = validator.validate(VALID_SLIDESHOW_STEP, ASSET_MANIFEST, negative_constraint_token="bananas")
    assert is_valid, errors
