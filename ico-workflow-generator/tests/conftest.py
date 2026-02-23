"""Shared pytest fixtures."""

import os
import sys
import tempfile
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app import create_app


@pytest.fixture()
def app():
    """Create Flask app instance for tests with isolated context storage."""
    with tempfile.TemporaryDirectory() as temp_dir:
        app = create_app(
            {
                "TESTING": True,
                "CONTEXT_STORE_PATH": os.path.join(temp_dir, "context_artifacts.json"),
                "LLM_SETTINGS_PATH": os.path.join(temp_dir, "llm_settings.json"),
            }
        )
        yield app


@pytest.fixture()
def client(app):
    """Flask test client."""
    return app.test_client()

