"""Tests for the SQLite database layer."""

import pytest

from tomo.db import Database


class TestDatabaseInit:
    def test_creates_tables(self, temp_db):
        tables = temp_db.list_tables()
        expected = [
            "schema_version",
            "pet_state",
            "dir_type_map",
            "growth_log",
            "daily_stats",
            "chat_history",
        ]
        for table in expected:
            assert table in tables

    def test_default_pet_state(self, temp_db):
        assert temp_db.get_pet_state("energy") == "100"
        assert temp_db.get_pet_state("exp") == "0"
        assert temp_db.get_pet_state("level") == "1"
        assert temp_db.get_pet_state("stage") == "egg"


class TestPetState:
    def test_set_and_get(self, temp_db):
        temp_db.set_pet_state("energy", "80")
        assert temp_db.get_pet_state("energy") == "80"

    def test_get_all(self, temp_db):
        state = temp_db.get_all_pet_state()
        assert "energy" in state
        assert "exp" in state

    def test_get_missing_key(self, temp_db):
        assert temp_db.get_pet_state("nonexistent") is None


class TestDirTypeMap:
    def test_upsert_and_get(self, temp_db):
        temp_db.upsert_dir_type("/projects/", "软件开发", 0.8)
        mappings = temp_db.get_dir_type_mappings()
        assert len(mappings) == 1
        assert mappings[0]["pattern"] == "/projects/"
        assert mappings[0]["type_name"] == "软件开发"

    def test_detect_type_from_cwd(self, temp_db):
        temp_db.upsert_dir_type("myproject", "数据分析", 0.9)
        work_type, confidence = temp_db.detect_type_from_cwd("/home/user/myproject/src")
        assert work_type == "数据分析"
        assert confidence == 0.9

    def test_detect_type_no_match(self, temp_db):
        work_type, confidence = temp_db.detect_type_from_cwd("/home/user/other")
        assert work_type is None
        assert confidence == 0.0


class TestGrowthLog:
    def test_log_and_get(self, temp_db):
        temp_db.log_growth_event("sync", "Test event")
        logs = temp_db.get_growth_logs(limit=10)
        assert len(logs) == 1
        assert logs[0]["event_type"] == "sync"
        assert "Test event" in logs[0]["description"]

    def test_empty_logs(self, temp_db):
        logs = temp_db.get_growth_logs()
        assert logs == []


class TestDailyStats:
    def test_upsert_and_get(self, temp_db):
        temp_db.upsert_daily_stats(
            date="2025-01-01",
            session_count=5,
            total_calls=100,
            detected_type="软件开发",
        )
        stats = temp_db.get_daily_stats("2025-01-01")
        assert stats is not None
        assert stats["session_count"] == 5
        assert stats["total_calls"] == 100
        assert stats["detected_type"] == "软件开发"

    def test_get_missing_date(self, temp_db):
        assert temp_db.get_daily_stats("1999-01-01") is None

    def test_update_existing(self, temp_db):
        temp_db.upsert_daily_stats("2025-01-01", session_count=5)
        temp_db.upsert_daily_stats("2025-01-01", session_count=10)
        stats = temp_db.get_daily_stats("2025-01-01")
        assert stats["session_count"] == 10


class TestChatHistory:
    def test_add_and_get(self, temp_db):
        temp_db.add_chat_entry("user", "Hello")
        temp_db.add_chat_entry("assistant", "Hi there!")
        history = temp_db.get_chat_history(limit=10)
        assert len(history) == 2
        assert history[0]["role"] == "user"
        assert history[1]["role"] == "assistant"

    def test_clear_history(self, temp_db):
        temp_db.add_chat_entry("user", "Test")
        temp_db.clear_chat_history()
        assert temp_db.get_chat_history() == []


class TestAchievements:
    def test_unlock_achievement(self, temp_db):
        temp_db.unlock_achievement("first_meeting")
        keys = temp_db.get_unlocked_achievement_keys()
        assert "first_meeting" in keys

    def test_unlock_duplicate_ignored(self, temp_db):
        temp_db.unlock_achievement("first_meeting")
        temp_db.unlock_achievement("first_meeting")
        keys = temp_db.get_unlocked_achievement_keys()
        assert len(keys) == 1

    def test_achievement_times(self, temp_db):
        temp_db.unlock_achievement("first_meeting")
        times = temp_db.get_achievement_times()
        assert "first_meeting" in times
        assert len(times["first_meeting"]) > 0
