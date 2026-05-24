"""Tests for the achievement share card system."""

from datetime import datetime
from unittest.mock import MagicMock

from rich.table import Table

from tomo.share_card import (
    _format_unlock_time,
    _get_mood_emoji,
    build_ascii_card,
    build_html_card,
    build_share_card,
    render_card_to_string,
)


class TestFormatters:
    def test_format_unlock_time_none(self):
        assert _format_unlock_time(None) == "刚刚"

    def test_format_unlock_time_valid(self):
        dt = datetime(2024, 6, 15, 14, 30)
        assert _format_unlock_time(dt.isoformat()) == "2024-06-15 14:30"

    def test_format_unlock_time_invalid(self):
        assert _format_unlock_time("not-a-date") == "not-a-date"

    def test_get_mood_emoji_known(self):
        assert _get_mood_emoji("happy") == "😊"
        assert _get_mood_emoji("exhausted") == "💀"

    def test_get_mood_emoji_unknown(self):
        assert _get_mood_emoji("unknown") == "😐"


class TestBuildShareCard:
    def test_build_share_card_returns_table(self):
        ach = MagicMock()
        ach.icon = "🌟"
        ach.name = "初次见面"
        ach.description = "Tomo 第一次陪伴你工作"

        pet = MagicMock()
        pet.level = 1
        pet.mood = "happy"
        pet.stage = "egg"

        config = MagicMock()
        config.pet_avatar = "🦊"
        config.pet_name = "Tomo"

        card = build_share_card(ach, pet, config, None)
        assert isinstance(card, Table)

    def test_build_share_card_with_unlock_time(self):
        ach = MagicMock()
        ach.icon = "🌟"
        ach.name = "Test"
        ach.description = "Desc"

        pet = MagicMock()
        pet.level = 5
        pet.mood = "energetic"
        pet.stage = "adult"

        config = MagicMock()
        config.pet_avatar = "🐱"
        config.pet_name = "Momo"

        dt = datetime(2024, 6, 15, 10, 0)
        card = build_share_card(ach, pet, config, dt.isoformat())
        assert isinstance(card, Table)


class TestBuildAsciiCard:
    def test_build_ascii_card_contains_achievement_info(self):
        ach = MagicMock()
        ach.icon = "🌟"
        ach.name = "初次见面"
        ach.description = "Tomo 第一次陪伴你工作"

        pet = MagicMock()
        pet.level = 1
        pet.mood = "happy"
        pet.stage = "egg"

        config = MagicMock()
        config.pet_avatar = "🦊"
        config.pet_name = "Tomo"

        text = build_ascii_card(ach, pet, config, None)
        assert "初次见面" in text
        assert "Tomo" in text
        assert "lv.1" in text
        assert "刚刚" in text

    def test_build_ascii_card_has_border(self):
        ach = MagicMock()
        ach.icon = "🌟"
        ach.name = "Test"
        ach.description = "Desc"

        pet = MagicMock()
        pet.level = 1
        pet.mood = "neutral"
        pet.stage = "egg"

        config = MagicMock()
        config.pet_avatar = "🦊"
        config.pet_name = "Tomo"

        text = build_ascii_card(ach, pet, config)
        assert "╔" in text
        assert "╝" in text


class TestBuildHtmlCard:
    def test_build_html_card_structure(self):
        ach = MagicMock()
        ach.icon = "🌟"
        ach.name = "初次见面"
        ach.description = "Desc"

        pet = MagicMock()
        pet.level = 1
        pet.mood = "happy"
        pet.stage = "egg"

        config = MagicMock()
        config.pet_avatar = "🦊"
        config.pet_name = "Tomo"

        html = build_html_card(ach, pet, config)
        assert "<!DOCTYPE html>" in html
        assert "🌟" in html
        assert "初次见面" in html
        assert "Tomo" in html


class TestRenderCardToString:
    def test_render_card_to_string(self):
        ach = MagicMock()
        ach.icon = "🌟"
        ach.name = "Test"
        ach.description = "Desc"

        pet = MagicMock()
        pet.level = 1
        pet.mood = "neutral"
        pet.stage = "egg"

        config = MagicMock()
        config.pet_avatar = "🦊"
        config.pet_name = "Tomo"

        card = build_share_card(ach, pet, config)
        text = render_card_to_string(card)
        assert isinstance(text, str)
        assert "Test" in text
