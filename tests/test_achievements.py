"""Tests for the achievement system."""

from datetime import datetime
from unittest.mock import MagicMock

import pytest

from tomo.achievements import ACHIEVEMENTS, Achievement, AchievementChecker
from tomo.detector import SessionSnapshot


class TestAchievementDefinitions:
    def test_all_achievements_have_keys(self):
        for key, ach in ACHIEVEMENTS.items():
            assert ach.key == key
            assert ach.name
            assert ach.description
            assert ach.icon

    def test_achievement_is_frozen(self):
        ach = Achievement("test", "Test", "Desc", "🎉")
        with pytest.raises(AttributeError):
            ach.name = "Changed"


class TestAchievementChecker:
    def test_first_meeting(self, temp_db, sample_snapshot):
        checker = AchievementChecker(temp_db)
        new = checker.check(sample_snapshot, level=1)
        assert any(a.key == "first_meeting" for a in new)

    def test_tool_master(self, temp_db):
        snapshot = SessionSnapshot(1, 50, 0, {"Bash": 50}, 0)
        checker = AchievementChecker(temp_db)
        new = checker.check(snapshot, level=1)
        assert any(a.key == "tool_master" for a in new)

    def test_skill_enthusiast(self, temp_db):
        snapshot = SessionSnapshot(1, 10, 5, {"Skill": 5}, 0)
        checker = AchievementChecker(temp_db)
        new = checker.check(snapshot, level=1)
        assert any(a.key == "skill_enthusiast" for a in new)

    def test_level_up_milestones(self, temp_db, empty_snapshot):
        checker = AchievementChecker(temp_db)
        new = checker.check(empty_snapshot, level=3)
        assert any(a.key == "level_up_3" for a in new)

        new = checker.check(empty_snapshot, level=5)
        assert any(a.key == "level_up_5" for a in new)

        new = checker.check(empty_snapshot, level=10)
        assert any(a.key == "level_up_10" for a in new)

    def test_no_duplicates(self, temp_db, sample_snapshot):
        checker = AchievementChecker(temp_db)
        # First check unlocks
        new1 = checker.check(sample_snapshot, level=1)
        checker.log_unlocked(new1)
        # Second check should return empty
        new2 = checker.check(sample_snapshot, level=1)
        assert new2 == []

    def test_log_unlocked(self, temp_db, empty_snapshot):
        checker = AchievementChecker(temp_db)
        new = checker.check(empty_snapshot, level=3)
        checker.log_unlocked(new)
        assert checker._already_unlocked("level_up_3")

    def test_get_unlocked_achievements(self, temp_db):
        temp_db.unlock_achievement("first_meeting")
        temp_db.unlock_achievement("tool_master")
        checker = AchievementChecker(temp_db)
        unlocked = checker.get_unlocked_achievements()
        assert len(unlocked) == 2
