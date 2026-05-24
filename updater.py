"""Self-update functionality for Tomo."""

from __future__ import annotations

import json
import logging
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import NamedTuple
from urllib.request import Request, urlopen

logger = logging.getLogger(__name__)

GITHUB_REPO = "lululu811/tomo"
GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/git/refs/heads/main"


class UpdateInfo(NamedTuple):
    """Information about available update."""

    current_version: str
    current_commit: str
    latest_commit: str
    needs_update: bool


def _get_current_commit() -> str | None:
    """Get current installed commit hash if installed from git."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
            cwd=Path(__file__).parent.parent,
        )
        return result.stdout.strip()[:7]
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def _get_install_type() -> str:
    """Detect how tomo was installed."""
    try:
        result = subprocess.run(
            ["pip", "show", "tomo"],
            capture_output=True,
            text=True,
            check=True,
        )
        for line in result.stdout.splitlines():
            if line.startswith("Location:"):
                location = line.split(":", 1)[1].strip()
                # Check if there's a .git directory near the install location
                loc_path = Path(location)
                if (loc_path.parent / ".git").exists():
                    return "editable"
                return "pip"
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass
    return "unknown"


def check_update(current_version: str) -> UpdateInfo:
    """Check if a newer version is available on GitHub."""
    current_commit = _get_current_commit()

    try:
        req = Request(
            GITHUB_API_URL,
            headers={"Accept": "application/vnd.github.v3+json"},
        )
        with urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode("utf-8"))
            latest_commit = data["object"]["sha"][:7]
    except Exception as exc:
        logger.warning("Failed to check for updates: %s", exc)
        return UpdateInfo(
            current_version=current_version,
            current_commit=current_commit or "unknown",
            latest_commit="unknown",
            needs_update=False,
        )

    needs_update = current_commit != latest_commit if current_commit else True

    return UpdateInfo(
        current_version=current_version,
        current_commit=current_commit or "unknown",
        latest_commit=latest_commit,
        needs_update=needs_update,
    )


def backup_database(tomo_dir: Path) -> Path | None:
    """Backup the database before update. Keep last 5 backups."""
    db_path = tomo_dir / "tomo.db"
    if not db_path.exists():
        return None

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = tomo_dir / f"tomo.db.backup.{timestamp}"

    try:
        shutil.copy2(db_path, backup_path)
        logger.info("Database backed up to %s", backup_path)

        # Clean up old backups (keep last 5)
        backups = sorted(
            tomo_dir.glob("tomo.db.backup.*"),
            key=lambda p: p.stat().st_mtime,
        )
        for old_backup in backups[:-5]:
            old_backup.unlink()
            logger.debug("Removed old backup: %s", old_backup)

        return backup_path
    except OSError as exc:
        logger.error("Failed to backup database: %s", exc)
        return None


def perform_update() -> tuple[bool, str]:
    """Perform the update. Returns (success, message)."""
    install_type = _get_install_type()

    if install_type == "editable":
        # Editable install: git pull + pip install -e .
        try:
            repo_dir = Path(__file__).parent.parent
            subprocess.run(
                ["git", "pull", "origin", "main"],
                cwd=repo_dir,
                check=True,
                capture_output=True,
                text=True,
            )
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "-e", "."],
                cwd=repo_dir,
                check=True,
                capture_output=True,
                text=True,
            )
            return True, "Updated successfully via git pull"
        except subprocess.CalledProcessError as exc:
            logger.error("Update failed: %s", exc)
            return False, f"Update failed: {exc.stderr or exc.stdout}"

    elif install_type == "pip":
        # Regular pip install: pip install --upgrade
        try:
            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "pip",
                    "install",
                    "--upgrade",
                    f"git+https://github.com/{GITHUB_REPO}.git@main",
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            return True, "Updated successfully via pip"
        except subprocess.CalledProcessError as exc:
            logger.error("Update failed: %s", exc)
            return False, f"Update failed: {exc.stderr or exc.stdout}"

    return False, "Could not detect installation type. Please update manually."


import sys  # noqa: E402
