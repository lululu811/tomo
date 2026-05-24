"""Tests for the Claude Code stats detector."""

import json
from pathlib import Path

import pytest

from tomo.detector import SessionSnapshot, StatsDetector


class TestSessionSnapshot:
    def test_immutable(self):
        snapshot = SessionSnapshot(1, 10, 2, {"Bash": 5}, 123)
        with pytest.raises(AttributeError):
            snapshot.total_calls = 20


class TestStatsDetector:
    def test_read_missing_file(self):
        detector = StatsDetector("/nonexistent/path/stats.json")
        snapshot = detector.read_latest()
        assert snapshot == SessionSnapshot(0, 0, 0, {}, 0)

    def test_read_valid_file(self, tmp_path):
        stats_file = tmp_path / "stats.json"
        data = {
            "sessions": {
                "session1": {
                    "total_calls": 10,
                    "updated_at": 1000,
                    "tool_counts": {"Bash": 5, "Read": 3, "Skill": 2},
                },
                "session2": {
                    "total_calls": 5,
                    "updated_at": 2000,
                    "tool_counts": {"Edit": 5},
                },
            }
        }
        stats_file.write_text(json.dumps(data))

        detector = StatsDetector(str(stats_file))
        snapshot = detector.read_latest()

        assert snapshot.session_count == 2
        assert snapshot.total_calls == 15
        assert snapshot.skill_calls == 2
        assert snapshot.tool_breakdown == {"Bash": 5, "Read": 3, "Skill": 2, "Edit": 5}
        assert snapshot.latest_update == 2000

    def test_read_corrupted_file(self, tmp_path):
        stats_file = tmp_path / "stats.json"
        stats_file.write_text("not valid json{")

        detector = StatsDetector(str(stats_file))
        snapshot = detector.read_latest()
        assert snapshot == SessionSnapshot(0, 0, 0, {}, 0)

    def test_read_empty_sessions(self, tmp_path):
        stats_file = tmp_path / "stats.json"
        stats_file.write_text(json.dumps({"sessions": {}}))

        detector = StatsDetector(str(stats_file))
        snapshot = detector.read_latest()
        assert snapshot == SessionSnapshot(0, 0, 0, {}, 0)

    def test_get_delta(self):
        detector = StatsDetector()
        previous = SessionSnapshot(1, 10, 2, {"Bash": 5}, 1000)
        current = SessionSnapshot(3, 25, 4, {"Bash": 12, "Read": 8}, 2000)

        delta = detector.get_delta(previous)
        # We can't easily mock read_latest here, but we can test with a real file

    def test_get_delta_none_previous(self, tmp_path):
        stats_file = tmp_path / "stats.json"
        data = {
            "sessions": {
                "s1": {"total_calls": 5, "updated_at": 100, "tool_counts": {"Bash": 5}},
            }
        }
        stats_file.write_text(json.dumps(data))

        detector = StatsDetector(str(stats_file))
        delta = detector.get_delta(None)

        assert delta.session_count == 1
        assert delta.total_calls == 5
        assert delta.tool_breakdown == {"Bash": 5}

    def test_get_delta_delta_calculation(self, tmp_path):
        stats_file = tmp_path / "stats.json"
        data = {
            "sessions": {
                "s1": {"total_calls": 15, "updated_at": 200, "tool_counts": {"Bash": 10, "Read": 5}},
            }
        }
        stats_file.write_text(json.dumps(data))

        detector = StatsDetector(str(stats_file))
        previous = SessionSnapshot(0, 5, 0, {"Bash": 3}, 100)
        delta = detector.get_delta(previous)

        assert delta.total_calls == 10
        assert delta.tool_breakdown == {"Bash": 7, "Read": 5}
