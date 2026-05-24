"""Shared pytest fixtures for Tomo."""

import tempfile
from pathlib import Path

import pytest

from tomo.config import Config
from tomo.db import Database
from tomo.detector import SessionSnapshot
from tomo.pet_engine import PetEngine


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)
    db = Database(db_path)
    yield db
    db_path.unlink(missing_ok=True)


@pytest.fixture
def default_config():
    """Return a default configuration for testing."""
    return Config(
        {
            "pet": {
                "name": "TestTomo",
                "avatar": "🐱",
                "personality": {
                    "description": "A test companion.",
                    "traits": {"curiosity": 0.5},
                    "speech": {
                        "style": "casual",
                        "tone": "friendly",
                        "forbidden": [],
                    },
                },
                "llm": {
                    "provider": "ollama",
                    "model": "qwen2.5:7b",
                    "api_key": None,
                    "call_budget": {"daily_limit": 0, "important_only": True},
                },
            }
        }
    )


@pytest.fixture
def fresh_pet():
    """Return a fresh pet engine for testing."""
    return PetEngine()


@pytest.fixture
def empty_snapshot():
    """Return an empty session snapshot."""
    return SessionSnapshot(0, 0, 0, {}, 0)


@pytest.fixture
def sample_snapshot():
    """Return a sample session snapshot with data."""
    return SessionSnapshot(
        session_count=3,
        total_calls=42,
        skill_calls=5,
        tool_breakdown={"Bash": 15, "Read": 12, "Edit": 10, "Skill": 5},
        latest_update=1234567890,
    )
