"""Logging configuration for Tomo."""

import logging
import sys
from pathlib import Path

DEFAULT_LOG_LEVEL = logging.INFO
LOG_FORMAT = "%(asctime)s | %(name)s | %(levelname)s | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logging(
    *,
    level: int | None = None,
    log_dir: Path | None = None,
    console: bool = True,
    file: bool = True,
) -> None:
    """Configure logging for Tomo.

    Args:
        level: Logging level (default: INFO).
        log_dir: Directory for log files (default: ~/.tomo/logs).
        console: Whether to log to stderr.
        file: Whether to log to a file.
    """
    if level is None:
        level = DEFAULT_LOG_LEVEL

    if log_dir is None:
        log_dir = Path.home() / ".tomo" / "logs"

    # Prevent duplicate handlers if called multiple times
    root_logger = logging.getLogger("tomo")
    if root_logger.handlers:
        return

    root_logger.setLevel(level)

    formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)

    if console:
        console_handler = logging.StreamHandler(sys.stderr)
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

    if file:
        try:
            log_dir.mkdir(parents=True, exist_ok=True)
            file_handler = logging.FileHandler(
                log_dir / "tomo.log",
                encoding="utf-8",
            )
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(formatter)
            root_logger.addHandler(file_handler)
        except OSError:
            # If we can't write to the log file, fall back to console only
            pass


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with the 'tomo' prefix."""
    return logging.getLogger(f"tomo.{name}")
