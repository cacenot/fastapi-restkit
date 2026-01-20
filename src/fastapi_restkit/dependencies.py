"""
FastAPI dependencies for pagination, sorting, and filtering.

Re-exports dependency factories for convenient imports.
"""

from fastapi_restkit.filterset import filter_as_query
from fastapi_restkit.sorting import create_sorting_dependency
from fastapi_restkit.sortingset import sorting_as_query

__all__ = [
    "create_sorting_dependency",
    "filter_as_query",
    "sorting_as_query",
]
