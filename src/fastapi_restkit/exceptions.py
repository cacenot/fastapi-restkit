"""
Custom exceptions for fastapi-restkit.

These exceptions provide structured error handling for filter and sorting validation.
"""

from typing import Any


class FastAPIRestKitError(Exception):
    """Base exception for fastapi-restkit."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        self.message = message
        self.details = details or {}
        super().__init__(message)


class InvalidFormatError(FastAPIRestKitError):
    """
    Exception raised when input format is invalid.

    Used for validation errors in filters, sorting parameters, etc.

    Attributes:
        field: The field that has the invalid format
        details: Additional details about the error
    """

    def __init__(self, field: str, details: dict[str, Any] | None = None) -> None:
        self.field = field
        message = f"Invalid format for field '{field}'"
        if details:
            message += f": {details}"
        super().__init__(message, details)
