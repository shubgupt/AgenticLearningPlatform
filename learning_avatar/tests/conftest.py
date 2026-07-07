"""
Shared fixtures. The key one is `mock_llm` -- every agent test gets a fake
model that costs nothing and returns deterministic output, so the test
suite runs in CI with no API key and no flakiness from real model variance.
"""
import pytest

from learning_avatar.llm_client import MockLLMClient
from learning_avatar.core.schemas import SessionState, SubjectContext


@pytest.fixture
def mock_llm():
    return MockLLMClient()


@pytest.fixture
def session():
    return SessionState(session_id="test-session")


@pytest.fixture
def ctx_grade5_soccer_law1():
    return SubjectContext(concept="law_1_inertia", gradeBand="grade5", theme="soccer")


@pytest.fixture
def ctx_uncovered_combo():
    """A concept guaranteed NOT to be in the pre-authored library (all 12
    real combinations only cover law_1/2/3), to exercise the "fall through
    to generation" path deliberately."""
    return SubjectContext(concept="law_4_not_a_real_law", gradeBand="high", theme="creative_play")
