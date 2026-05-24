"""Custom exceptions for Tomo."""

from typing import Any


class TomoError(Exception):
    """Base exception for all Tomo errors."""

    def __init__(self, message: str, *, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class ConfigError(TomoError):
    """Raised when configuration is invalid or cannot be loaded."""


class DatabaseError(TomoError):
    """Raised when a database operation fails."""


class DetectorError(TomoError):
    """Raised when stats detection fails."""


class ValidationError(TomoError):
    """Raised when input validation fails."""
