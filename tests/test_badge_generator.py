"""Tests for the GitHub badge SVG generator."""

from unittest.mock import MagicMock

from tomo.badge_generator import (
    _bar_svg,
    _mood_emoji,
    _stage_label,
    generate_badge,
    generate_workflow_yaml,
)


class TestHelpers:
    def test_mood_emoji_known(self):
        assert _mood_emoji("happy") == "😊"
        assert _mood_emoji("exhausted") == "💀"

    def test_mood_emoji_unknown(self):
        assert _mood_emoji("unknown") == "😐"

    def test_stage_label(self):
        assert _stage_label("egg") == "蛋"
        assert _stage_label("adult") == "成年"
        assert _stage_label("unknown") == "unknown"

    def test_bar_svg(self):
        svg = _bar_svg(50, x=10, y=20, width=100, height=8)
        assert '<rect' in svg
        assert 'x="10"' in svg
        assert 'y="20"' in svg
        assert 'var(--tomo-track)' in svg
        assert 'var(--tomo-energy)' in svg


class TestGenerateBadge:
    def test_generate_badge_basic(self):
        pet = MagicMock()
        pet.level = 3
        pet.mood = "happy"
        pet.stage = "child"
        pet.energy = 80
        pet.satiation = 90
        pet.affinity = 10

        config = MagicMock()
        config.pet_avatar = "🦊"
        config.pet_name = "Tomo"

        svg = generate_badge(pet, config)
        assert svg.startswith("<svg")
        assert "</svg>" in svg
        assert "Tomo" in svg
        assert "lv.3" in svg

    def test_generate_badge_with_stats(self):
        pet = MagicMock()
        pet.level = 5
        pet.mood = "energetic"
        pet.stage = "teen"
        pet.energy = 100
        pet.satiation = 100
        pet.affinity = 50

        config = MagicMock()
        config.pet_avatar = "🐱"
        config.pet_name = "Momo"

        today_stats = {
            "session_count": 5,
            "total_calls": 200,
            "detected_type": "dev",
        }
        svg = generate_badge(pet, config, today_stats)
        assert "Sessions: 5" in svg
        assert "Calls: 200" in svg
        assert "Type: dev" in svg

    def test_generate_badge_dark_light_theme(self):
        pet = MagicMock()
        pet.level = 1
        pet.mood = "neutral"
        pet.stage = "egg"
        pet.energy = 50
        pet.satiation = 50
        pet.affinity = 0

        config = MagicMock()
        config.pet_avatar = "🦊"
        config.pet_name = "Tomo"

        svg = generate_badge(pet, config)
        assert "prefers-color-scheme: light" in svg
        assert "prefers-color-scheme: dark" in svg


class TestGenerateWorkflow:
    def test_generate_workflow_yaml(self):
        yaml = generate_workflow_yaml()
        assert "name: Update Tomo Badge" in yaml
        assert "actions/checkout@v4" in yaml
        assert "tomo badge --output tomo-badge.svg" in yaml
