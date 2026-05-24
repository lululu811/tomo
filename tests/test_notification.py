"""Tests for the notification system."""

from unittest.mock import patch

from tomo.notification import _fallback_notify, notify


class TestNotify:
    @patch("tomo.notification._PLYER_AVAILABLE", True)
    @patch("tomo.notification.notification.notify")
    def test_plyer_success(self, mock_notify):
        notify("Title", "Message")
        mock_notify.assert_called_once_with(title="Title", message="Message", timeout=5)

    @patch("tomo.notification._PLYER_AVAILABLE", True)
    @patch("tomo.notification.notification.notify")
    def test_plyer_failure_falls_back(self, mock_notify):
        mock_notify.side_effect = Exception("plyer error")
        # Should not raise, fallback is silent
        notify("Title", "Message")

    @patch("tomo.notification._PLYER_AVAILABLE", False)
    @patch("tomo.notification.shutil.which")
    def test_fallback_notify_send(self, mock_which):
        mock_which.side_effect = lambda x: x == "notify-send"
        with patch("subprocess.run") as mock_run:
            _fallback_notify("Title", "Message", 5)
            mock_run.assert_called_once()
            args = mock_run.call_args[0][0]
            assert args[0] == "notify-send"

    @patch("tomo.notification._PLYER_AVAILABLE", False)
    @patch("tomo.notification.shutil.which")
    def test_fallback_no_backend(self, mock_which):
        mock_which.return_value = None
        # Should not raise
        _fallback_notify("Title", "Message", 5)
