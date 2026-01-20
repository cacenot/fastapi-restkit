"""
Sorting models and utilities - sort_by parameters with validation.

Provides:
- SortOrder enum (asc, desc)
- SortField model
- SortingParams with format validation
- SortableFieldsConfig for whitelisting
- create_sorting_dependency factory function
"""

import re
from enum import Enum

from pydantic import BaseModel, Field

from fastapi_restkit.exceptions import InvalidFormatError


class SortOrder(str, Enum):
    """Sort order options"""

    ASC = "asc"
    DESC = "desc"


class SortField(BaseModel):
    """Individual sort specification"""

    field: str = Field(description="Field name to sort by")
    order: SortOrder = Field(default=SortOrder.ASC, description="Sort order")

    def __str__(self) -> str:
        """String representation for database queries"""
        return f"{self.field}:{self.order.value}"


class SortableFieldInfo(BaseModel):
    """Information about a sortable field"""

    name: str = Field(description="Field name")
    description: str | None = Field(default=None, description="Field description")


class SortableFieldsConfig(BaseModel):
    """Configuration for sortable fields in an endpoint"""

    fields: list[SortableFieldInfo] = Field(
        description="List of fields that can be sorted"
    )

    @classmethod
    def create(
        cls, field_names: list[str], descriptions: dict | None = None
    ) -> "SortableFieldsConfig":
        """
        Create sortable fields config from field names.

        Args:
            field_names: List of field names that can be sorted
            descriptions: Optional dict mapping field names to descriptions

        Example:
            SortableFieldsConfig.create(
                ["created_at", "name", "status"],
                {"created_at": "Creation date", "name": "Item name"}
            )
        """
        descriptions = descriptions or {}
        sortable_fields = [
            SortableFieldInfo(name=field_name, description=descriptions.get(field_name))
            for field_name in field_names
        ]
        return cls(fields=sortable_fields)

    def get_field_names(self) -> list[str]:
        """Get all sortable field names"""
        return [field.name for field in self.fields]

    def is_sortable(self, field_name: str) -> bool:
        """Check if a field is sortable"""
        return field_name in self.get_field_names()

    def validate_sort_fields(self, sort_fields: list[SortField]) -> list[SortField]:
        """
        Validate and filter sort fields.

        Only keeps sort fields that are in the sortable fields list.
        """
        return [
            sort_field
            for sort_field in sort_fields
            if self.is_sortable(sort_field.field)
        ]


class SortingParams(BaseModel):
    """Sorting parameters supporting multiple sort fields"""

    sort_by: list[str] = Field(
        default_factory=list,
        description="List of fields to sort by (format: field:asc or field:desc)",
    )

    def is_empty(self) -> bool:
        """Check if no sorting is specified"""
        return len(self.sort_by) == 0

    def get_sort_fields(self) -> list[SortField]:
        """
        Parse sort_by strings into SortField objects.

        Format validation: field_name:order (e.g., "created_at:desc")
        - Field name: alphanumeric + underscores, must start with letter or underscore
        - Order: optional, must be 'asc' or 'desc'

        Raises InvalidFormatError for invalid formats.
        """
        fields = []
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

            field = match.group(1)
            order_str = match.group(2) or "asc"

            try:
                sort_order = SortOrder(order_str)
                fields.append(SortField(field=field, order=sort_order))
            except ValueError:
                raise InvalidFormatError(
                    field="sort_by",
                    details={
                        "invalid_order": order_str,
                        "valid_orders": ["asc", "desc"],
                        "received": sort_param,
                    },
                )

        return fields

    def validate_against_config(self, config: SortableFieldsConfig) -> "SortingParams":
        """
        Validate sorting parameters against allowed sortable fields.

        Returns:
            Self for chaining.

        Raises:
            InvalidFormatError: If sort_by contains invalid fields.
        """
        valid_fields = config.get_field_names()
        invalid_sorts = [
            s.split(":")[0].strip()
            for s in self.sort_by
            if s.split(":")[0].strip() not in valid_fields
        ]

        if invalid_sorts:
            raise InvalidFormatError(
                field="sort_by",
                details={
                    "invalid_fields": invalid_sorts,
                    "valid_fields": valid_fields,
                },
            )

        return self


def create_sorting_dependency(
    field_names: list[str],
    descriptions: dict | None = None,
):
    """
    Create a reusable sorting dependency with validation.

    Factory function that creates a dependency for validating sortable fields.

    Args:
        field_names: List of allowed field names
        descriptions: Optional dict mapping field names to descriptions

    Returns:
        Dependency function that validates SortingParams

    Example:
        ```python
        from typing import Annotated
        from fastapi import Depends
        from fastapi_restkit import SortingParams, create_sorting_dependency

        PermissionSortingDep = Annotated[
            SortingParams,
            Depends(
                create_sorting_dependency(
                    field_names=["id", "slug", "resource", "action", "created_at"],
                    descriptions={
                        "id": "Permission ID",
                        "slug": "Permission slug",
                    },
                )
            ),
        ]


        @router.get("/")
        async def list_permissions(
            sorting: PermissionSortingDep = SortingParams(),
        ):
            sort_fields = sorting.get_sort_fields()
            ...
        ```
    """
    config = SortableFieldsConfig.create(field_names, descriptions)

    async def validate_sorting(
        sorting: SortingParams = SortingParams(),
    ) -> SortingParams:
        """Validate sorting parameters against allowed fields."""
        if not sorting.is_empty():
            sorting.validate_against_config(config)
        return sorting

    return validate_sorting


__all__ = [
    "SortField",
    "SortOrder",
    "SortableFieldInfo",
    "SortableFieldsConfig",
    "SortingParams",
    "create_sorting_dependency",
]
