import pytest
import os

@pytest.fixture(autouse=True)
def env_setup():
    """Set up environment variables for testing"""
    os.environ['GEMINI_API_KEY'] = 'test-key'
    yield
    if 'GEMINI_API_KEY' in os.environ:
        del os.environ['GEMINI_API_KEY'] 