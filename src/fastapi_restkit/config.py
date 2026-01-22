"""
Configuration for fastapi-restkit defaults.

Users can override these settings by setting environment variables or
passing parameters directly to classes.
"""

import os


class RestKitSettings:
    """Default settings for fastapi-restkit."""

    # Pagination defaults
    DEFAULT_PAGE_SIZE: int = 10
    MAX_PAGE_SIZE: int = 100

    # PostgreSQL unaccent extension flag
    UNACCENT_AVAILABLE: bool = False

    # PyPI publishing (for development/CI)
    PYPI_TOKEN: str | None = None
    PYPI_TEST_TOKEN: str | None = None

    @classmethod
    def from_env(cls) -> "RestKitSettings":
        """Load settings from environment variables."""
        instance = cls()
        if page_size := os.getenv("RESTKIT_DEFAULT_PAGE_SIZE"):
            instance.DEFAULT_PAGE_SIZE = int(page_size)
        if max_page_size := os.getenv("RESTKIT_MAX_PAGE_SIZE"):
            instance.MAX_PAGE_SIZE = int(max_page_size)
        if pypi_token := os.getenv("PYPI_TOKEN"):
            instance.PYPI_TOKEN = pypi_token
        if pypi_test_token := os.getenv("PYPI_TEST_TOKEN"):
            instance.PYPI_TEST_TOKEN = pypi_test_token
        return instance


# Global settings instance
settings = RestKitSettings.from_env()


def set_unaccent_available(available: bool) -> None:
    """Set whether PostgreSQL unaccent extension is available."""
    settings.UNACCENT_AVAILABLE = available


def is_unaccent_available() -> bool:
    """Check if PostgreSQL unaccent extension is available."""
    return settings.UNACCENT_AVAILABLE
