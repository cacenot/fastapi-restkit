"""
SortingSet - Base class for domain-specific sorting configurations.

Inspired by Django OrderingFilter, provides declarative sorting with automatic
SQLAlchemy expression generation.
"""

import re
from collections.abc import Callable
from typing import Any, TypeVar

from fastapi import Query
from pydantic import BaseModel, Field
from sqlalchemy.sql import ColumnElement
from sqlmodel import SQLModel

from fastapi_restkit.exceptions import InvalidFormatError


class SortableField(BaseModel):
    """
    Information about a sortable field.

    Attributes:
        name: Field name (auto-mapped from property name if not provided)
        description: Human-readable description for documentation
        column: Optional column name if different from field name

    Examples:
        ```python
        # Simple field with auto-mapping
        id: SortableField = SortableField(description="User ID")

        # Custom column mapping
        full_name: SortableField = SortableField(
            description="User full name",
            column="name",  # Maps to 'name' column
        )
        ```
    """

    name: str | None = Field(
        default=None,
        description="Field name (auto-mapped from property name if not provided)",
    )
    description: str | None = Field(
        default=None, description="Field description for API docs"
    )
    column: str | None = Field(
        default=None,
        description="Column name in database (if different from field name)",
    )

    def get_column_name(self) -> str:
        """Get the actual column name to use in queries."""
        if self.column:
            return self.column
        if self.name:
            return self.name
        raise ValueError("SortableField must have either name or column set")


TSortingSet = TypeVar("TSortingSet", bound="SortingSet")


class SortingSet(BaseModel):
    """
    Base class for domain-specific sorting configurations.

    Provides declarative sorting fields with automatic SQLAlchemy expression generation.

    Usage:
        ```python
        class PermissionSortingSet(SortingSet):
            id: SortableField = SortableField(description="Permission ID")
            slug: SortableField = SortableField(description="Permission slug")
            created_at: SortableField = SortableField(description="Creation date")

            full_name: SortableField = SortableField(
                description="User full name",
                column="name",  # Maps to 'name' column
            )

            class Config:
                default_sorting = ["created_at:desc"]


        @router.get("/permissions")
        async def list_permissions(sorting: PermissionSortingSet = Depends()):
            order_by = sorting.to_sqlalchemy(Permission)
            query = select(Permission).order_by(*order_by)
        ```
    """

    sort_by: list[str] = Field(
        default_factory=list,
        description="List of fields to sort by (format: field:asc or field:desc)",
    )

    class Config:
        """Configuration for SortingSet."""

        default_sorting: list[str] = []

    def model_post_init(self, __context: Any) -> None:
        """Apply default sorting and auto-map field names after initialization."""
        # Auto-map field names from property names
        for field_name in self.model_fields:
            if field_name == "sort_by":
                continue

            field_value = getattr(self, field_name, None)
            if isinstance(field_value, SortableField) and field_value.name is None:
                field_value.name = field_name

        # Apply default sorting if no sorting specified
        if not self.sort_by and hasattr(self.Config, "default_sorting"):
            self.sort_by = self.Config.default_sorting

    def get_sortable_fields(self) -> dict[str, SortableField]:
        """
        Get all sortable fields.

        Returns:
            Dict mapping field names to SortableField instances
        """
        sortable_fields = {}

        for field_name in self.model_fields:
            if field_name == "sort_by":
                continue

            field_value = getattr(self, field_name, None)
            if isinstance(field_value, SortableField):
                sortable_fields[field_name] = field_value

        return sortable_fields

    def to_sqlalchemy(self, model_class: type[SQLModel]) -> list[ColumnElement]:
        """
        Generate SQLAlchemy order_by expressions from sort_by parameters.

        Args:
            model_class: SQLModel class to sort

        Returns:
            List of SQLAlchemy order_by expressions

        Raises:
            InvalidFormatError: If sort_by format is invalid or field not found
            ValueError: If column not found in model
        """
        if not self.sort_by:
            return []

        order_by_clauses = []
        sortable_fields = self.get_sortable_fields()

        sort_pattern = re.compile(r"^([a-zA-Z_][a-zA-Z0-9_]*)(?::([a-z]+))?$")

        for sort_param in self.sort_by:
            match = sort_pattern.match(sort_param.strip())
            if not match:
                raise InvalidFormatError(
                    field="sort_by",
                    details={
                        "invalid_format": sort_param,
                        "expected_format": "field_name or field_name:asc or field_name:desc",
                    },
                )

            field_name = match.group(1)
            order_str = match.group(2) or "asc"

            if order_str not in ["asc", "desc"]:
                raise InvalidFormatError(
                    field="sort_by",
                    details={
                        "invalid_order": order_str,
                        "valid_orders": ["asc", "desc"],
                    },
                )

            if field_name not in sortable_fields:
                raise InvalidFormatError(
                    field="sort_by",
                    details={
                        "invalid_field": field_name,
                        "valid_fields": list(sortable_fields.keys()),
                    },
                )

            sortable_field = sortable_fields[field_name]
            column_name = sortable_field.get_column_name()

            if not hasattr(model_class, column_name):
                raise ValueError(
                    f"Column '{column_name}' not found in model {model_class.__name__}"
                )
            column = getattr(model_class, column_name)

            if order_str == "desc":
                order_by_clauses.append(column.desc())
            else:
                order_by_clauses.append(column.asc())

        return order_by_clauses

    def apply_to_query(self, query, model_class: type[SQLModel]):
        """
        Apply sorting to a SQLAlchemy query.

        Args:
            query: SQLAlchemy query to modify
            model_class: SQLModel class for column references

        Returns:
            Modified query with order_by applied
        """
        order_by = self.to_sqlalchemy(model_class)
        if order_by:
            return query.order_by(*order_by)
        return query


def sorting_as_query(sorting_cls: type[TSortingSet]) -> Callable[..., TSortingSet]:
    """Create a FastAPI dependency that documents SortingSet query params."""

    temp_instance = sorting_cls()
    sortable_fields = temp_instance.get_sortable_fields()

    field_lines = []
    for name, field in sortable_fields.items():
        description = field.description or name
        field_lines.append(f"- `{name}`: {description}")

    default_sorting = list(getattr(sorting_cls.Config, "default_sorting", []))
    example = default_sorting or (
        [f"{next(iter(sortable_fields))}:asc"] if sortable_fields else ["id:asc"]
    )

    description = "List of fields to sort by (format: field:asc or field:desc)."
    if field_lines:
        description += "\n\n**Available fields**\n" + "\n".join(field_lines)
    if default_sorting:
        description += f"\n\n**Default:** {', '.join(default_sorting)}"

    def dependency(
        sort_by_values: list[str] | None = Query(
            default=None,
            alias="sort_by",
            description=description,
            examples=example,
        ),
    ) -> TSortingSet:
        values = list(sort_by_values) if sort_by_values else []
        return sorting_cls(sort_by=values)

    dependency.__name__ = f"{sorting_cls.__name__}QueryDependency"
    return dependency


__all__ = ["SortableField", "SortingSet", "sorting_as_query"]
