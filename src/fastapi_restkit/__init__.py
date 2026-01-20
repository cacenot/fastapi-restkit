"""
FastAPI RestKit - Pagination, filtering, and sorting utilities for FastAPI with SQLModel.

This library provides reusable utilities for:
- Pagination parameters (page, page_size)
- Sorting parameters with validation
- Filtering parameters with typed filters
- FilterSet for domain-specific filters with SQLAlchemy expressions
- Paginated responses (generic)

Example:
    ```python
    from typing import Annotated
    from fastapi import APIRouter, Depends
    from fastapi_restkit import (
        PaginationParams,
        PaginatedResponse,
        SortingParams,
        create_sorting_dependency,
        FilterSet,
        SearchFilter,
        BooleanFilter,
        filter_as_query,
    )


    class ItemFilterSet(FilterSet):
        search: Optional[SearchFilter] = None
        is_active: Optional[BooleanFilter] = None

        class Config:
            field_columns = {
                "search": ["name", "description"],
            }


    router = APIRouter()

    ItemSortingDep = Annotated[
        SortingParams, Depends(create_sorting_dependency(["id", "name", "created_at"]))
    ]


    @router.get("/items", response_model=PaginatedResponse[ItemSchema])
    async def list_items(
        pagination: PaginationParams = Depends(),
        sorting: ItemSortingDep = SortingParams(),
        filters: ItemFilterSet = Depends(filter_as_query(ItemFilterSet)),
    ):
        query = select(Item)
        query = filters.apply_to_query(query, Item)
        # ... apply sorting and pagination
        return PaginatedResponse.create(items, total, pagination)
    ```
"""

__version__ = "0.1.0"

# Configuration
from fastapi_restkit.config import (
    RestKitSettings,
    is_unaccent_available,
    set_unaccent_available,
    settings,
)

# Exceptions
from fastapi_restkit.exceptions import FastAPIRestKitError, InvalidFormatError

# Typed Filters
from fastapi_restkit.filters import (
    BaseFilter,
    BooleanFilter,
    DateFilter,
    DateFromToRangeFilter,
    DateRangeFilter,
    DateTimeFilter,
    DateTimeFromToRangeFilter,
    FilterLookup,
    IntListFilter,
    ListFilter,
    NumberFilter,
    NumericRangeFilter,
    SearchFilter,
    StringListFilter,
    TimeRangeFilter,
    UUIDListFilter,
)

# FilterSet
from fastapi_restkit.filterset import FilterSet, filter_as_query

# Models
from fastapi_restkit.models import PaginationParams

# Pagination / Response
from fastapi_restkit.pagination import FilterParams, PaginatedResponse

# Sorting
from fastapi_restkit.sorting import (
    SortableFieldInfo,
    SortableFieldsConfig,
    SortField,
    SortingParams,
    SortOrder,
    create_sorting_dependency,
)

# SortingSet
from fastapi_restkit.sortingset import SortableField, SortingSet, sorting_as_query

# Utils
from fastapi_restkit.utils import (
    parse_date_value,
    parse_datetime_value,
    parse_time_value,
)

__all__ = [
    "BaseFilter",
    "BooleanFilter",
    "DateFilter",
    "DateFromToRangeFilter",
    "DateRangeFilter",
    "DateTimeFilter",
    "DateTimeFromToRangeFilter",
    # Exceptions
    "FastAPIRestKitError",
    # Typed Filters
    "FilterLookup",
    "FilterParams",
    # FilterSet
    "FilterSet",
    "IntListFilter",
    "InvalidFormatError",
    "ListFilter",
    "NumberFilter",
    "NumericRangeFilter",
    # Response
    "PaginatedResponse",
    # Models
    "PaginationParams",
    # Configuration
    "RestKitSettings",
    "SearchFilter",
    "SortField",
    # Sorting
    "SortOrder",
    # SortingSet
    "SortableField",
    "SortableFieldInfo",
    "SortableFieldsConfig",
    "SortingParams",
    "SortingSet",
    "StringListFilter",
    "TimeRangeFilter",
    "UUIDListFilter",
    # Version
    "__version__",
    "create_sorting_dependency",
    "filter_as_query",
    "is_unaccent_available",
    # Utils
    "parse_date_value",
    "parse_datetime_value",
    "parse_time_value",
    "set_unaccent_available",
    "settings",
    "sorting_as_query",
]
