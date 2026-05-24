"""Tests for the background daemon."""

from unittest.mock import MagicMock, patch

from tomo.daemon import Daemon, is_running, stop_daemon


class TestDaemonLifecycle:
    def test_daemon_init(self):
        daemon = Daemon(interval=300)
        assert daemon.interval == 300
        assert daemon.running is False
        assert daemon.decay_counter == 0

    def test_setup_signal_handlers(self):
        daemon = Daemon()
        daemon._setup_signal_handlers()
        assert daemon.running is True

    @patch("tomo.daemon.os.getpid", return_value=1234)
    @patch("tomo.daemon.PID_FILE")
    def test_write_pid(self, mock_pid_file, mock_getpid):
        daemon = Daemon()
        mock_pid_file.write_text = MagicMock()
        daemon._write_pid()
        mock_pid_file.write_text.assert_called_once_with("1234")


class TestIsRunning:
    @patch("tomo.daemon.PID_FILE")
    def test_not_running_no_file(self, mock_pid_file):
        mock_pid_file.exists.return_value = False
        assert is_running() is False

    @patch("tomo.daemon.os.kill")
    @patch("tomo.daemon.PID_FILE")
    def test_running(self, mock_pid_file, mock_kill):
        mock_pid_file.exists.return_value = True
        mock_pid_file.read_text.return_value = "1234"
        assert is_running() is True

    @patch("tomo.daemon.os.kill", side_effect=OSError)
    @patch("tomo.daemon.PID_FILE")
    def test_not_running_stale_pid(self, mock_pid_file, mock_kill):
        mock_pid_file.exists.return_value = True
        mock_pid_file.read_text.return_value = "9999"
        assert is_running() is False


class TestStopDaemon:
    @patch("tomo.daemon.get_pid", return_value=None)
    def test_stop_not_running(self, mock_get_pid):
        assert stop_daemon() is False

    @patch("tomo.daemon.os.kill")
    @patch("tomo.daemon.time.sleep")
    @patch("tomo.daemon.PID_FILE")
    @patch("tomo.daemon.get_pid", return_value=1234)
    def test_stop_success(self, mock_get_pid, mock_pid_file, mock_sleep, mock_kill):
        mock_pid_file.exists.side_effect = [True, False]
        assert stop_daemon() is True


class TestDaemonSync:
    def test_sync_no_activity(self):
        daemon = Daemon()
        daemon.db = MagicMock()
        daemon.config = MagicMock()
        daemon.last_snapshot = MagicMock(total_calls=0, session_count=0)

        detector = MagicMock()
        detector.read_latest.return_value = MagicMock(total_calls=0, session_count=0)
        detector.get_delta.return_value = MagicMock(
            total_calls=0, session_count=0, tool_breakdown={}
        )
        daemon._sync(detector)
            # Should not crash

    def test_sync_with_activity(self):
        daemon = Daemon()
        daemon.db = MagicMock()
        daemon.db.get_daily_stats.return_value = None
        daemon.config = MagicMock(pet_name="Test")
        daemon.last_snapshot = MagicMock(total_calls=10, session_count=1)
        daemon.llm_calls = 0
        daemon.llm_failures = 0

        with patch("tomo.daemon.PetEngine") as mock_pet, \
             patch("tomo.daemon.AchievementChecker") as mock_checker:

            detector = MagicMock()
            detector.read_latest.return_value = MagicMock(total_calls=15, session_count=1)
            detector.get_delta.return_value = MagicMock(
                total_calls=5, session_count=0, skill_calls=1,
                tool_breakdown={"Bash": 3, "Read": 2}
            )

            pet = MagicMock()
            pet.level = 2
            pet.energy = 100
            pet.satiation = 100
            pet.add_exp_from_session.return_value = 0
            mock_pet.from_dict.return_value = pet

            checker = MagicMock()
            checker.check.return_value = []
            mock_checker.return_value = checker

            daemon._sync(detector)
            daemon.db.set_pet_state.assert_called()

    def test_natural_decay(self):
        daemon = Daemon()
        daemon.db = MagicMock()
        daemon.config = MagicMock(pet_name="Test")
        daemon.last_snapshot = MagicMock(total_calls=0, session_count=0)
        daemon.decay_counter = 5  # One away from trigger

        detector = MagicMock()
        detector.read_latest.return_value = MagicMock(total_calls=0, session_count=0)
        detector.get_delta.return_value = MagicMock(
            total_calls=0, session_count=0, tool_breakdown={}
        )

        with patch("tomo.daemon.PetEngine") as mock_pet:
            pet = MagicMock()
            pet.energy = 25
            pet.satiation = 25
            mock_pet.from_dict.return_value = pet

            daemon._sync(detector)
            assert daemon.decay_counter == 0
            assert pet.consume_energy.called


class TestDaemonProactiveFeedback:
    def test_single_tool_concentration(self):
        daemon = Daemon()
        daemon.config = MagicMock(llm_important_only=True, pet_name="Test")

        pet = MagicMock(mood="happy", level=2)

        with patch("tomo.llm.LLMClient") as mock_client:
            client = MagicMock()
            client.generate.return_value = "Take a break!"
            mock_client.return_value = client

            result = daemon._generate_proactive_suggestion("You are using Bash a lot", pet)
            assert result == "Take a break!"

    def test_infer_work_type_below_threshold(self):
        daemon = Daemon()
        delta = MagicMock(total_calls=3)
        assert daemon._infer_work_type(delta) is None

    def test_infer_work_type_already_inferred(self):
        daemon = Daemon()
        daemon.db = MagicMock()
        daemon.db.get_daily_stats.return_value = {"detected_type": "coding"}
        delta = MagicMock(total_calls=10)
        assert daemon._infer_work_type(delta) is None
