"""Utilities for timezone-aware timestamps."""

from datetime import UTC, datetime


def utcnow() -> datetime:
    """Return a timezone-aware UTC timestamp."""
    return datetime.now(UTC)
