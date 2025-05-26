import pytest
from unittest.mock import patch
import os

@pytest.fixture(autouse=True)
def no_test_env():
    """Fixture to ensure that TEST_MODE is not set in the environment."""
    with patch.dict(os.environ, {"TEST_MODE": "", "LLM_MODEL": ""}, clear=True):
        yield
