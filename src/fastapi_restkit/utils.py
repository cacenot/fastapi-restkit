"""
Utility functions for pagination filters.

Helper functions for parsing and validating filter values.
"""

from datetime import date, datetime, time, timezone
from typing import Any

from fastapi_restkit.config import is_unaccent_available, set_unaccent_available

__all__ = [
    "is_unaccent_available",
    "parse_date_value",
    "parse_datetime_value",
    "parse_time_value",
    "set_unaccent_available",
]


def parse_date_value(v: Any) -> date | None:
    """
    Parse date from various formats.

    Supports:
    - None (returns None)
    - date instance (returns as-is)
    - ISO string (YYYY-MM-DD)

    Args:
        v: Value to parse (None, date, or string)

    Returns:
        Parsed date or None

    Raises:
        ValueError: If string format is invalid
        TypeError: If value type is not supported
    """
    if v is None:
        return None
    if isinstance(v, date) and not isinstance(v, datetime):
        return v
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, str):
        try:
            return datetime.fromisoformat(v).date()
        except ValueError as e:
            raise ValueError(f"Invalid date format: {v}. Expected: YYYY-MM-DD") from e
    raise TypeError(f"Expected date or string, got {type(v)}")


def parse_datetime_value(v: Any) -> datetime | None:
    """
    Parse datetime from various formats and normalize to UTC.

    Supports:
    - None (returns None)
    - datetime instance (converts to UTC if timezone-aware, assumes UTC if naive)
    - ISO 8601 string (with or without timezone)

    All datetimes are normalized to UTC to match database storage.
    Naive datetimes are assumed to be UTC.

    Args:
        v: Value to parse (None, datetime, or string)

    Returns:
        Parsed datetime in UTC timezone or None

    Raises:
        ValueError: If string format is invalid
        TypeError: If value type is not supported
    """
    if v is None:
        return v

    if isinstance(v, datetime):
        if v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v.astimezone(timezone.utc)

    if isinstance(v, str):
        try:
            normalized = v.replace("Z", "+00:00")
            dt = datetime.fromisoformat(normalized)
            if dt.tzinfo is None:
                return dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except ValueError as e:
            raise ValueError(
                f"Invalid datetime format: {v}. Expected: ISO 8601 "
                f"(YYYY-MM-DD, YYYY-MM-DDTHH:MM:SS, or with timezone)"
            ) from e

    raise TypeError(f"Expected datetime or string, got {type(v)}")


def parse_time_value(v: Any) -> time | None:
    """
    Parse time from various formats.

    Supports:
    - None (returns None)
    - time instance (returns as-is)
    - Time string (HH:MM:SS or HH:MM)

    Args:
        v: Value to parse (None, time, or string)

    Returns:
        Parsed time or None

    Raises:
        ValueError: If string format is invalid
        TypeError: If value type is not supported
    """
    if v is None or isinstance(v, time):
        return v
    if isinstance(v, str):
        try:
            return datetime.fromisoformat(f"2000-01-01T{v}").time()
        except ValueError as e:
            raise ValueError(
                f"Invalid time format: {v}. Expected: HH:MM:SS or HH:MM"
            ) from e
    raise TypeError(f"Expected time or string, got {type(v)}")
