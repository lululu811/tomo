"""Tests for the easter egg detection system."""

from unittest.mock import MagicMock, patch

from tomo.easter_eggs import (
    _get_commit_diff_stats,
    _get_recent_commits,
    _pick_message,
    _scan_code_patterns,
    check_easter_eggs,
)


class TestGetRecentCommits:
    @patch("tomo.easter_eggs.subprocess.run")
    def test_no_git_repo(self, mock_run):
        mock_run.return_value = MagicMock(returncode=128, stdout="")
        commits = _get_recent_commits()
        assert commits == []

    @patch("tomo.easter_eggs.subprocess.run")
    def test_single_commit(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="abc123|fix bug in login|2024-01-15 10:30:00 +0800",
        )
        commits = _get_recent_commits()
        assert len(commits) == 1
        assert commits[0]["message"] == "fix bug in login"

    @patch("tomo.easter_eggs.subprocess.run")
    def test_multiple_commits(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=(
                "abc123|fix bug|2024-01-15 10:30:00 +0800\n"
                "def456|refactor auth|2024-01-15 09:00:00 +0800"
            ),
        )
        commits = _get_recent_commits()
        assert len(commits) == 2


class TestCommitDiffStats:
    @patch("tomo.easter_eggs.subprocess.run")
    def test_normal_stats(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=" file.py | 10 +++++ 5 -----\n 1 file changed, 10 insertions(+), 5 deletions(-)",
        )
        stats = _get_commit_diff_stats("abc123")
        assert stats["insertions"] == 10
        assert stats["deletions"] == 5

    @patch("tomo.easter_eggs.subprocess.run")
    def test_no_changes(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="")
        stats = _get_commit_diff_stats("abc123")
        assert stats["insertions"] == 0
        assert stats["deletions"] == 0


class TestScanCodePatterns:
    @patch("tomo.easter_eggs.subprocess.run")
    def test_todo_found(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="+// TODO: fix this later",
        )
        patterns = _scan_code_patterns()
        assert "TODO" in patterns

    @patch("tomo.easter_eggs.subprocess.run")
    def test_nothing_found(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="")
        patterns = _scan_code_patterns()
        assert patterns == []

    @patch("tomo.easter_eggs.subprocess.run")
    def test_git_not_available(self, mock_run):
        mock_run.return_value = MagicMock(returncode=128, stdout="")
        patterns = _scan_code_patterns()
        assert patterns == []


class TestCheckEasterEggs:
    @patch("tomo.easter_eggs._get_recent_commits")
    @patch("tomo.easter_eggs._get_commit_diff_stats")
    @patch("tomo.easter_eggs._scan_code_patterns")
    def test_commit_keyword_trigger(self, mock_patterns, mock_stats, mock_commits):
        mock_commits.return_value = [
            {"hash": "abc123", "message": "fix bug in parser", "date": "2024-01-15 14:00:00 +0800"},
        ]
        mock_stats.return_value = {"insertions": 2, "deletions": 1}
        mock_patterns.return_value = []

        triggers = check_easter_eggs("fox")
        assert len(triggers) >= 1
        assert triggers[0].trigger_type == "commit_keyword"
        assert "bug" in triggers[0].message.lower()

    @patch("tomo.easter_eggs._get_recent_commits")
    @patch("tomo.easter_eggs._get_commit_diff_stats")
    @patch("tomo.easter_eggs._scan_code_patterns")
    def test_late_night_trigger(self, mock_patterns, mock_stats, mock_commits):
        mock_commits.return_value = [
            {"hash": "abc123", "message": "wip feature", "date": "2024-01-15 02:00:00 +0800"},
        ]
        mock_stats.return_value = {"insertions": 2, "deletions": 1}
        mock_patterns.return_value = []

        triggers = check_easter_eggs("fox")
        trigger_types = [t.trigger_type for t in triggers]
        assert "late_night" in trigger_types

    @patch("tomo.easter_eggs._get_recent_commits")
    @patch("tomo.easter_eggs._get_commit_diff_stats")
    @patch("tomo.easter_eggs._scan_code_patterns")
    def test_mass_delete_trigger(self, mock_patterns, mock_stats, mock_commits):
        mock_commits.return_value = [
            {"hash": "abc123", "message": "cleanup", "date": "2024-01-15 14:00:00 +0800"},
        ]
        mock_stats.return_value = {"insertions": 5, "deletions": 200}
        mock_patterns.return_value = []

        triggers = check_easter_eggs("fox")
        trigger_types = [t.trigger_type for t in triggers]
        assert "mass_delete" in trigger_types

    @patch("tomo.easter_eggs._get_recent_commits")
    @patch("tomo.easter_eggs._get_commit_diff_stats")
    @patch("tomo.easter_eggs._scan_code_patterns")
    def test_code_pattern_trigger(self, mock_patterns, mock_stats, mock_commits):
        mock_commits.return_value = []
        mock_stats.return_value = {"insertions": 0, "deletions": 0}
        mock_patterns.return_value = ["TODO"]

        triggers = check_easter_eggs("fox")
        assert len(triggers) >= 1
        assert triggers[0].trigger_type == "code_pattern"

    @patch("tomo.easter_eggs._get_recent_commits")
    @patch("tomo.easter_eggs._get_commit_diff_stats")
    @patch("tomo.easter_eggs._scan_code_patterns")
    def test_no_triggers(self, mock_patterns, mock_stats, mock_commits):
        mock_commits.return_value = [
            {"hash": "abc123", "message": "update readme", "date": "2024-01-15 14:00:00 +0800"},
        ]
        mock_stats.return_value = {"insertions": 2, "deletions": 1}
        mock_patterns.return_value = []

        triggers = check_easter_eggs("fox")
        assert triggers == []

    @patch("tomo.easter_eggs._get_recent_commits")
    @patch("tomo.easter_eggs._get_commit_diff_stats")
    @patch("tomo.easter_eggs._scan_code_patterns")
    def test_multiple_triggers_per_commit(self, mock_patterns, mock_stats, mock_commits):
        # A commit can match both keyword and late night
        mock_commits.return_value = [
            {"hash": "abc123", "message": "fix bug", "date": "2024-01-15 02:00:00 +0800"},
        ]
        mock_stats.return_value = {"insertions": 2, "deletions": 1}
        mock_patterns.return_value = []

        triggers = check_easter_eggs("fox")
        # Both keyword and late night can trigger from same commit
        trigger_types = [t.trigger_type for t in triggers]
        assert "commit_keyword" in trigger_types
        assert "late_night" in trigger_types


class TestPickMessage:
    def test_returns_from_pool(self):
        from tomo.species_manager import get_species

        species = get_species("fox")
        msg = _pick_message(["msg1", "msg2"], species)
        assert msg in ["msg1", "msg2"]
