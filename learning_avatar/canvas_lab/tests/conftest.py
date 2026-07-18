def pytest_addoption(parser):
    parser.addoption(
        "--clear-cache",
        action="store_true",
        default=False,
        help="For live generation tests: delete any cached generated_lessons "
        "row for the test's (skill, modality) first, forcing a fresh LLM call "
        "instead of serving the cached result.",
    )
