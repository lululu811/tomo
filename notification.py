"""Cross-platform desktop notifications for Tomo."""

from __future__ import annotations

import logging
import shutil
import subprocess

try:
    from plyer import notification

    _PLYER_AVAILABLE = True
except ImportError:
    _PLYER_AVAILABLE = False

logger = logging.getLogger(__name__)


def notify(title: str, message: str, timeout: int = 5) -> None:
    """Send a desktop notification.

    Tries plyer first, then falls back to platform-specific commands:
    - Linux: notify-send
    - macOS: osascript
    - Windows: msg (or PowerShell)
    """
    if _PLYER_AVAILABLE:
        try:
            notification.notify(title=title, message=message, timeout=timeout)
            return
        except Exception as exc:
            logger.debug("plyer notification failed: %s", exc)

    # Fallback to platform-specific commands
    _fallback_notify(title, message, timeout)


def _fallback_notify(title: str, message: str, timeout: int) -> None:
    """Platform-specific fallback notifications."""
    # Linux
    if shutil.which("notify-send"):
        try:
            subprocess.run(
                ["notify-send", title, message, "-t", str(timeout * 1000)],
                capture_output=True,
                check=False,
            )
            return
        except Exception as exc:
            logger.debug("notify-send failed: %s", exc)

    # macOS
    if shutil.which("osascript"):
        try:
            script = f'display notification "{message}" with title "{title}"'
            subprocess.run(
                ["osascript", "-e", script],
                capture_output=True,
                check=False,
            )
            return
        except Exception as exc:
            logger.debug("osascript notification failed: %s", exc)

    # Windows (PowerShell)
    if shutil.which("powershell.exe"):
        try:
            ps_script = (
                f"Add-Type -AssemblyName System.Windows.Forms; "
                f"[System.Windows.Forms.MessageBox]::Show("
                f"'{message}', '{title}'"
                f")"
            )
            subprocess.run(
                ["powershell.exe", "-Command", ps_script],
                capture_output=True,
                check=False,
            )
            return
        except Exception as exc:
            logger.debug("powershell notification failed: %s", exc)

    logger.debug("No notification backend available")
