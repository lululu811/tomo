"""Tests for the prompt builder."""

from unittest.mock import MagicMock

from tomo.config import Config
from tomo.pet_engine import PetEngine
from tomo.prompt_builder import (
    MOOD_QUIPS,
    STAGE_INTROS,
    build_fallback_reply,
    build_system_prompt,
)


class TestPromptBuilder:
    def test_build_system_prompt_basic(self, temp_db):
        config = Config(
            {
                "pet": {
                    "name": "TestFox",
                    "avatar": "🦊",
                    "personality": {
                        "description": "Test companion",
                        "style": "encourager",
                        "speech": {"forbidden": ["no tests"]},
                    },
                }
            }
        )
        pet = PetEngine(exp=10, energy=80, satiation=80)
        prompt = build_system_prompt(config, pet, temp_db)

        assert "TestFox" in prompt
        assert "程序员鼓励师" in prompt
        assert "程序员" in prompt
        assert "lv." in prompt
        assert "今日Coding战绩" in prompt
        assert "回复约束" in prompt

    def test_build_system_prompt_roaster_style(self, temp_db):
        config = Config({"pet": {"name": "Fox", "avatar": "🦊", "personality": {}}})
        pet = PetEngine()
        prompt = build_system_prompt(config, pet, temp_db, style="roaster")

        assert "毒舌" in prompt
        assert "损友" in prompt

    def test_build_system_prompt_anime_style(self, temp_db):
        config = Config({"pet": {"name": "Fox", "avatar": "🦊", "personality": {}}})
        pet = PetEngine()
        prompt = build_system_prompt(config, pet, temp_db, style="anime")

        assert "二次元" in prompt
        assert "热血" in prompt

    def test_build_system_prompt_with_achievements(self, temp_db):
        temp_db.unlock_achievement("first_meeting")
        config = Config({"pet": {"name": "Fox", "avatar": "🦊", "personality": {}}})
        pet = PetEngine()
        prompt = build_system_prompt(config, pet, temp_db)

        assert "已解锁成就" in prompt

    def test_build_system_prompt_with_daily_stats(self, temp_db):
        temp_db.upsert_daily_stats("2025-01-01", session_count=3, total_calls=42)
        config = Config({"pet": {"name": "Fox", "avatar": "🦊", "personality": {}}})
        pet = PetEngine()
        prompt = build_system_prompt(config, pet, temp_db)

        assert "Session数" in prompt
        assert "总调用" in prompt

    def test_build_system_prompt_level_message(self, temp_db):
        config = Config({"pet": {"name": "Fox", "avatar": "🦊", "personality": {}}})
        pet = PetEngine(exp=200)  # Should be level 3+
        prompt = build_system_prompt(config, pet, temp_db)

        assert "等级寄语" in prompt


class TestFallbackReply:
    def test_fallback_encourager(self):
        pet = PetEngine(energy=80, satiation=80)
        reply = build_fallback_reply(pet, style="encourager")
        assert reply.startswith("🦊")

    def test_fallback_roaster(self):
        pet = PetEngine(energy=10, satiation=10)
        reply = build_fallback_reply(pet, style="roaster")
        assert reply.startswith("🦊")

    def test_fallback_anime(self):
        pet = PetEngine(energy=50, satiation=50)
        reply = build_fallback_reply(pet, style="anime")
        assert reply.startswith("🦊")

    def test_fallback_all_moods(self):
        for mood in MOOD_QUIPS:
            pet = MagicMock()
            pet.mood = mood
            reply = build_fallback_reply(pet)
            assert reply.startswith("🦊")

    def test_fallback_invalid_style_uses_default(self):
        pet = MagicMock()
        pet.mood = "happy"
        reply = build_fallback_reply(pet, style="nonexistent")
        assert reply.startswith("🦊")


class TestQuipPools:
    def test_mood_quips_all_moods_have_entries(self):
        for mood, quips in MOOD_QUIPS.items():
            assert len(quips) > 0
            for q in quips:
                assert isinstance(q, str)
                assert len(q) > 0

    def test_stage_intros_all_stages_have_entries(self):
        for stage, intros in STAGE_INTROS.items():
            assert len(intros) > 0
            for i in intros:
                assert isinstance(i, str)
                assert len(i) > 0
