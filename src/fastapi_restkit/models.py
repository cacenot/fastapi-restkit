"""
Pagination models - page and page_size parameters.

Provides reusable pagination parameters for list endpoints.
"""

from pydantic import BaseModel, Field

from fastapi_restkit.config import settings


class PaginationParams(BaseModel):
    """
    Generic pagination parameters.

    Attributes:
        page: Page number (1-based, default: 1)
        page_size: Items per page (default from settings, max 100)

    Example:
        ```python
        from fastapi import Depends
        from fastapi_restkit import PaginationParams


        @router.get("/items")
        async def list_items(
            pagination: PaginationParams = Depends(),
        ):
            offset = pagination.offset
            limit = pagination.limit
            ...
        ```
    """

    page: int | None = Field(default=1, ge=1, description="Page number (1-based)")
    page_size: int | None = Field(
        default=None,
        ge=1,
        le=100,
        description="Items per page",
    )

    def model_post_init(self, __context) -> None:
        """Set default page_size from settings if not provided."""
        if self.page_size is None:
            object.__setattr__(self, "page_size", settings.DEFAULT_PAGE_SIZE)

    @property
    def offset(self) -> int:
        """Calculate offset for database query."""
        page = self.page or 1
        page_size = self.page_size or settings.DEFAULT_PAGE_SIZE
        return (page - 1) * page_size

    @property
    def limit(self) -> int:
        """Get limit for database query."""
        return self.page_size or settings.DEFAULT_PAGE_SIZE
