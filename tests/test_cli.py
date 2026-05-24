"""Tests for the CLI."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from tomo.cli import main


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def mock_init():
    """Mock initialization state."""
    with patch("tomo.cli._db_path") as mock_db, \
         patch("tomo.cli._config_path") as mock_config, \
         patch("tomo.cli.Database") as mock_db_cls, \
         patch("tomo.cli.load_config") as mock_load_cfg:

        db_path = MagicMock()
        db_path.exists.return_value = True
        mock_db.return_value = db_path
        mock_config.return_value = Path.home() / ".tomo" / "config.yaml"
        mock_db_cls.return_value = MagicMock()
        mock_load_cfg.return_value = MagicMock(
            pet_name="TestTomo",
            pet_avatar="🐱",
            personality={
                "description": "Test",
                "speech": {"style": "casual", "tone": "friendly", "forbidden": []},
            },
        )
        yield


class TestInit:
    def test_init_creates_files(self, runner, tmp_path):
        cfg = tmp_path / ".tomo" / "config.yaml"
        with patch("tomo.cli._tomo_dir", return_value=tmp_path / ".tomo"), \
             patch("tomo.cli.ensure_default_config", return_value=cfg):
            result = runner.invoke(main, ["init"])
            assert result.exit_code == 0
            assert "TestTomo" in result.output or "Welcome" in result.output


class TestStatus:
    def test_status_not_initialized(self, runner):
        with patch("tomo.cli._db_path") as mock_db:
            mock_db.return_value = Path("/nonexistent/tomo.db")
            result = runner.invoke(main, ["status"])
            assert result.exit_code != 0
            assert "not initialized" in result.output.lower()


class TestFeed:
    def test_feed(self, runner, mock_init):
        with patch("tomo.cli.PetEngine") as mock_pet:
            pet = MagicMock()
            pet.satiation = 100
            pet.feed.return_value = None
            mock_pet.from_dict.return_value = pet
            result = runner.invoke(main, ["feed"])
            assert result.exit_code == 0


class TestRest:
    def test_rest(self, runner, mock_init):
        with patch("tomo.cli.PetEngine") as mock_pet:
            pet = MagicMock()
            pet.energy = 100
            pet.rest.return_value = None
            mock_pet.from_dict.return_value = pet
            result = runner.invoke(main, ["rest"])
            assert result.exit_code == 0


class TestPlay:
    def test_play(self, runner, mock_init):
        with patch("tomo.cli.PetEngine") as mock_pet:
            pet = MagicMock()
            pet.energy = 50
            pet.satiation = 100
            mock_pet.from_dict.return_value = pet
            result = runner.invoke(main, ["play"])
            assert result.exit_code == 0

    def test_play_too_tired(self, runner, mock_init):
        with patch("tomo.cli.PetEngine") as mock_pet:
            pet = MagicMock()
            pet.energy = 5
            mock_pet.from_dict.return_value = pet
            result = runner.invoke(main, ["play"])
            assert result.exit_code == 0
            assert "too tired" in result.output.lower() or "tired" in result.output


class TestPrompt:
    def test_prompt_not_initialized(self, runner):
        with patch("tomo.cli._db_path") as mock_db:
            mock_db.return_value = Path("/nonexistent/tomo.db")
            result = runner.invoke(main, ["prompt"])
            assert result.exit_code == 0


class TestInstall:
    def test_install_zsh(self, runner):
        result = runner.invoke(main, ["install", "--shell=zsh"])
        assert result.exit_code == 0
        assert "zsh" in result.output.lower()

    def test_install_bash(self, runner):
        result = runner.invoke(main, ["install", "--shell=bash"])
        assert result.exit_code == 0
        assert "bash" in result.output.lower()


class TestDaemonCommands:
    def test_daemon_status_not_running(self, runner):
        with patch("tomo.daemon.is_running", return_value=False):
            result = runner.invoke(main, ["daemon", "status"])
            assert result.exit_code == 0
            assert "not running" in result.output.lower()

    def test_daemon_stop_not_running(self, runner):
        with patch("tomo.daemon.is_running", return_value=False):
            result = runner.invoke(main, ["daemon", "stop"])
            assert result.exit_code == 0
            assert "not running" in result.output.lower()


class TestLogs:
    def test_logs_empty(self, runner, mock_init):
        mock_db = MagicMock()
        mock_db.get_growth_logs.return_value = []
        with patch("tomo.cli.Database", return_value=mock_db):
            result = runner.invoke(main, ["logs"])
            assert result.exit_code == 0


class TestGrowth:
    def test_growth(self, runner, mock_init):
        with patch("tomo.cli.PetEngine") as mock_pet:
            pet = MagicMock()
            pet.level = 3
            pet.exp = 200
            pet.exp_to_next_level = 50
            pet.level_progress = 0.5
            mock_pet.from_dict.return_value = pet
            # Need to mock Database.get_exp_history to avoid MagicMock issues
            mock_db = MagicMock()
            mock_db.get_exp_history.return_value = []
            with patch("tomo.cli.Database", return_value=mock_db):
                result = runner.invoke(main, ["growth"])
                assert result.exit_code == 0
