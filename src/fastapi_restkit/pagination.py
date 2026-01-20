"""
Paginated response model and filtering base class.

Provides:
- PaginatedResponse: Generic response for paginated data
- FilterParams: Base class for filter parameters
"""

from typing import Generic, TypeVar

from pydantic import BaseModel, Field

from fastapi_restkit.models import PaginationParams

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    """
    Generic paginated response.

    Attributes:
        items: List of items in current page
        total: Total number of items across all pages
        page: Current page number
        page_size: Number of items per page
        total_pages: Total number of pages
        has_next: Whether there is a next page
        has_previous: Whether there is a previous page

    Example:
        ```python
        from fastapi_restkit import PaginatedResponse, PaginationParams


        @router.get("/items", response_model=PaginatedResponse[ItemSchema])
        async def list_items(
            pagination: PaginationParams = Depends(),
        ):
            items = await get_items(pagination.offset, pagination.limit)
            total = await count_items()
            return PaginatedResponse.create(items, total, pagination)
        ```
    """

    items: list[T]
    total: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_previous: bool

    @classmethod
    def create(
        cls, items: list[T], total: int, pagination: PaginationParams
    ) -> "PaginatedResponse[T]":
        """
        Create paginated response from items and pagination params.

        Args:
            items: List of items for current page
            total: Total count of all items
            pagination: Pagination parameters used

        Returns:
            PaginatedResponse with calculated metadata
        """
        page = pagination.page or 1
        page_size = pagination.page_size or 10
        total_pages = (total + page_size - 1) // page_size if page_size > 0 else 0

        return cls(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_previous=page > 1,
        )


class FilterParams(BaseModel):
    """
    Base class for filter parameters.

    Simple base class for creating domain-specific filter parameters.
    For more advanced filtering with typed filters and SQLAlchemy integration,
    use FilterSet instead.

    Example:
        ```python
        class ItemFilterParams(FilterParams):
            status: Optional[str] = None
            category: Optional[str] = None
        ```
    """

    search: str | None = Field(default=None, description="Search term")


__all__ = [
    "FilterParams",
    "PaginatedResponse",
]
