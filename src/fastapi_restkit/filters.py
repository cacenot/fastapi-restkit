"""
Generic filtering system inspired by Django Filter.

Provides typed filter classes that:
- Show up correctly in OpenAPI documentation
- Generate SQLAlchemy expressions automatically
- Support various filter types (Boolean, Date, Number, Range, etc.)
"""

import logging
from datetime import date, datetime, time
from enum import Enum
from typing import Any, Generic, TypeVar, cast
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator
from sqlalchemy.sql import ColumnElement
from sqlmodel import Column, and_, func

from fastapi_restkit.config import is_unaccent_available
from fastapi_restkit.exceptions import InvalidFormatError
from fastapi_restkit.utils import (
    parse_date_value,
    parse_datetime_value,
    parse_time_value,
)

T = TypeVar("T")

logger = logging.getLogger(__name__)


class FilterLookup(str, Enum):
    """Lookup types for filters - similar to Django ORM."""

    EXACT = "exact"  # Equal
    IEXACT = "iexact"  # Case-insensitive equal
    CONTAINS = "contains"  # LIKE %value%
    ICONTAINS = "icontains"  # Case-insensitive LIKE %value%
    IN = "in"  # IN (value1, value2, ...)
    GT = "gt"  # Greater than
    GTE = "gte"  # Greater than or equal
    LT = "lt"  # Less than
    LTE = "lte"  # Less than or equal
    STARTSWITH = "startswith"  # LIKE value%
    ISTARTSWITH = "istartswith"  # Case-insensitive LIKE value%
    ENDSWITH = "endswith"  # LIKE %value
    IENDSWITH = "iendswith"  # Case-insensitive LIKE %value
    RANGE = "range"  # BETWEEN min AND max
    ISNULL = "isnull"  # IS NULL or IS NOT NULL


class BaseFilter(BaseModel, Generic[T]):
    """Base class for all filters."""

    value: T | None = Field(default=None)
    lookup: FilterLookup = Field(default=FilterLookup.EXACT)

    def is_active(self) -> bool:
        """Check if filter has a value."""
        return self.value is not None

    def to_sqlalchemy(self, column: Column) -> ColumnElement | None:
        """
        Convert filter to SQLAlchemy expression.

        Args:
            column: SQLModel column to filter

        Returns:
            SQLAlchemy expression or None if filter is not active
        """
        if not self.is_active():
            return None

        return self._build_expression(column)

    def _build_expression(self, column: Column) -> ColumnElement:
        """Build SQLAlchemy expression based on lookup type."""
        value = self.value

        if self.lookup == FilterLookup.EXACT:
            return column == value
        elif self.lookup == FilterLookup.IEXACT:
            return column.ilike(str(value))
        elif self.lookup == FilterLookup.CONTAINS:
            return column.like(f"%{value}%")
        elif self.lookup == FilterLookup.ICONTAINS:
            return column.ilike(f"%{value}%")
        elif self.lookup == FilterLookup.GT:
            return column > value
        elif self.lookup == FilterLookup.GTE:
            return column >= value
        elif self.lookup == FilterLookup.LT:
            return column < value
        elif self.lookup == FilterLookup.LTE:
            return column <= value
        elif self.lookup == FilterLookup.STARTSWITH:
            return column.like(f"{value}%")
        elif self.lookup == FilterLookup.ISTARTSWITH:
            return column.ilike(f"{value}%")
        elif self.lookup == FilterLookup.ENDSWITH:
            return column.like(f"%{value}")
        elif self.lookup == FilterLookup.IENDSWITH:
            return column.ilike(f"%{value}")
        elif self.lookup == FilterLookup.ISNULL:
            return column.is_(None) if value else column.isnot(None)
        else:
            return column == value


class SearchFilter(BaseFilter[str]):
    """
    Text search filter with case-insensitive contains by default.

    Uses PostgreSQL unaccent extension when available for accent-insensitive search.

    Examples:
        - search="project" -> unaccent(column) ILIKE unaccent('%project%')
        - search="Project" (lookup=exact) -> = 'Project'
    """

    lookup: FilterLookup = Field(
        default=FilterLookup.ICONTAINS,
        description="Lookup type (default: icontains)",
    )

    @field_validator("value", mode="before")
    @classmethod
    def sanitize_value(cls, v: Any) -> str | None:
        """
        Sanitize search value.

        Note:
            SQLAlchemy parameterization handles SQL injection automatically,
            but we validate string length to prevent DOS attacks.
        """
        if v is None:
            return None

        value = str(v).strip()

        if not value:
            return None

        if len(value) > 1000:
            raise InvalidFormatError(
                field="search",
                details={"reason": "Search term cannot exceed 1000 characters"},
            )

        return value

    def _build_expression(self, column: Column) -> ColumnElement:
        """Build SQLAlchemy expression with unaccent support."""
        value = self.value

        # For exact match, use default behavior
        if self.lookup == FilterLookup.EXACT:
            return column == value

        # For search operations, use unaccent if available
        if self.lookup in (FilterLookup.ICONTAINS, FilterLookup.CONTAINS):
            if is_unaccent_available():
                # Use unaccent for accent-insensitive search
                if self.lookup == FilterLookup.ICONTAINS:
                    return func.unaccent(column).ilike(func.unaccent(f"%{value}%"))
                else:
                    return func.unaccent(column).like(func.unaccent(f"%{value}%"))
            # Fallback to regular LIKE/ILIKE
            elif self.lookup == FilterLookup.ICONTAINS:
                return column.ilike(f"%{value}%")
            else:
                return column.like(f"%{value}%")

        # For other lookups, use default behavior from BaseFilter
        return super()._build_expression(column)


class BooleanFilter(BaseFilter[bool]):
    """
    Boolean filter.

    Examples:
        - is_active=true -> column = true
        - is_deleted=false -> column = false
    """

    value: bool | None = Field(default=None, description="Boolean value")


class NumberFilter(BaseFilter[float]):
    """
    Numeric filter with comparison support.

    Examples:
        - quantity=10 -> column = 10
        - quantity=10 (lookup=gte) -> column >= 10
        - price=99.99 (lookup=lt) -> column < 99.99
    """

    value: float | None = Field(default=None, description="Numeric value")


class NumericRangeFilter(BaseModel):
    """
    Numeric range filter with validation.

    Examples:
        - min=10, max=100 -> column BETWEEN 10 AND 100
        - min=10 -> column >= 10
        - max=100 -> column <= 100
    """

    min: float | None = Field(default=None, description="Minimum value (inclusive)")
    max: float | None = Field(default=None, description="Maximum value (inclusive)")

    @model_validator(mode="after")
    def validate_range(self) -> "NumericRangeFilter":
        """Validate that min <= max."""
        if self.min is not None and self.max is not None:
            if self.min > self.max:
                raise InvalidFormatError(
                    field="range",
                    details={
                        "min": self.min,
                        "max": self.max,
                        "reason": f"Minimum value ({self.min}) cannot be greater than maximum value ({self.max})",
                    },
                )
        return self

    def is_active(self) -> bool:
        """Check if filter has any value."""
        return self.min is not None or self.max is not None

    def to_sqlalchemy(self, column: Column) -> ColumnElement | None:
        """Convert to SQLAlchemy BETWEEN or comparison."""
        if not self.is_active():
            return None

        conditions = []
        if self.min is not None:
            conditions.append(column >= self.min)
        if self.max is not None:
            conditions.append(column <= self.max)

        return and_(*conditions) if len(conditions) > 1 else conditions[0]


class DateFilter(BaseFilter[date]):
    """
    Date filter with comparison support.

    Examples:
        - created_at=2024-01-15 -> column = '2024-01-15'
        - created_at=2024-01-15 (lookup=gte) -> column >= '2024-01-15'
    """

    value: date | None = Field(
        default=None, description="Date in ISO format (YYYY-MM-DD)"
    )

    @field_validator("value", mode="before")
    @classmethod
    def parse_date(cls, v: Any) -> date | None:
        """Parse date from string."""
        return parse_date_value(v)


class DateRangeFilter(BaseModel):
    """
    Date range filter with validation.

    Examples:
        - min=2024-01-01, max=2024-12-31 -> BETWEEN
        - min=2024-01-01 -> >= 2024-01-01
    """

    min: date | None = Field(
        default=None, description="Start date (inclusive) in ISO format (YYYY-MM-DD)"
    )
    max: date | None = Field(
        default=None, description="End date (inclusive) in ISO format (YYYY-MM-DD)"
    )

    @field_validator("min", "max", mode="before")
    @classmethod
    def parse_date(cls, v: Any) -> date | None:
        """Parse date from string."""
        return parse_date_value(v)

    @model_validator(mode="after")
    def validate_range(self) -> "DateRangeFilter":
        """Validate that min <= max."""
        if self.min is not None and self.max is not None:
            if self.min > self.max:
                raise InvalidFormatError(
                    field="date_range",
                    details={
                        "min": str(self.min),
                        "max": str(self.max),
                        "reason": f"Start date ({self.min}) cannot be after end date ({self.max})",
                    },
                )
        return self

    def is_active(self) -> bool:
        """Check if filter has any value."""
        return self.min is not None or self.max is not None

    def to_sqlalchemy(self, column: Column) -> ColumnElement | None:
        """Convert to SQLAlchemy BETWEEN or comparison."""
        if not self.is_active():
            return None

        conditions = []
        if self.min is not None:
            conditions.append(column >= self.min)
        if self.max is not None:
            conditions.append(column <= self.max)

        return and_(*conditions) if len(conditions) > 1 else conditions[0]


class DateFromToRangeFilter(BaseModel):
    """
    Date range filter with 'from' and 'to' naming (more intuitive).

    Examples:
        - from_date=2024-01-01, to_date=2024-12-31
    """

    from_date: date | None = Field(
        default=None,
        alias="from",
        description="Start date (inclusive) in ISO format (YYYY-MM-DD)",
    )
    to_date: date | None = Field(
        default=None,
        alias="to",
        description="End date (inclusive) in ISO format (YYYY-MM-DD)",
    )

    @field_validator("from_date", "to_date", mode="before")
    @classmethod
    def parse_date(cls, v: Any) -> date | None:
        """Parse date from string."""
        return parse_date_value(v)

    @model_validator(mode="after")
    def validate_range(self) -> "DateFromToRangeFilter":
        """Validate that from_date <= to_date."""
        if self.from_date is not None and self.to_date is not None:
            if self.from_date > self.to_date:
                raise InvalidFormatError(
                    field="date_range",
                    details={
                        "from": str(self.from_date),
                        "to": str(self.to_date),
                        "reason": f"Start date ({self.from_date}) cannot be after end date ({self.to_date})",
                    },
                )
        return self

    def is_active(self) -> bool:
        """Check if filter has any value."""
        return self.from_date is not None or self.to_date is not None

    def to_sqlalchemy(self, column: Column) -> ColumnElement | None:
        """Convert to SQLAlchemy BETWEEN or comparison."""
        if not self.is_active():
            return None

        conditions = []
        if self.from_date is not None:
            conditions.append(column >= self.from_date)
        if self.to_date is not None:
            conditions.append(column <= self.to_date)

        return and_(*conditions) if len(conditions) > 1 else conditions[0]


class DateTimeFilter(BaseFilter[datetime]):
    """
    DateTime filter with ISO 8601 format support.

    **Timezone Behavior:**
    - Input datetimes are converted to UTC automatically (see `parse_datetime_value`)
    - Naive datetimes (without timezone) are treated as UTC
    - Comparison is always done in UTC

    Examples:
        - created_at=2024-01-15T10:30:00 -> exact match (UTC)
        - created_at=2024-01-15T10:30:00Z -> exact match (UTC explicit)
        - created_at=2024-01-15T10:30:00-03:00 -> converted to UTC (13:30:00)
    """

    value: datetime | None = Field(
        default=None,
        description="DateTime in ISO 8601 format (YYYY-MM-DDTHH:MM:SS[Z|±HH:MM])",
    )

    @field_validator("value", mode="before")
    @classmethod
    def parse_datetime(cls, v: Any) -> datetime | None:
        """Parse datetime from string."""
        return parse_datetime_value(v)


class DateTimeFromToRangeFilter(BaseModel):
    """
    DateTime range filter with ISO 8601 format and validation.

    **Timezone Behavior:**
    - All datetimes are converted to UTC
    - Naive datetimes are treated as UTC
    - Range comparison is done in UTC

    Examples:
        - from=2024-01-15T00:00:00, to=2024-01-15T23:59:59
        - from=2024-01-15T00:00:00-03:00, to=2024-01-15T23:59:59-03:00
    """

    from_datetime: datetime | None = Field(
        default=None,
        alias="from",
        description="Start datetime (inclusive) in ISO 8601 format",
    )
    to_datetime: datetime | None = Field(
        default=None,
        alias="to",
        description="End datetime (inclusive) in ISO 8601 format",
    )

    @field_validator("from_datetime", "to_datetime", mode="before")
    @classmethod
    def parse_datetime(cls, v: Any) -> datetime | None:
        """Parse datetime from string."""
        return parse_datetime_value(v)

    @model_validator(mode="after")
    def validate_range(self) -> "DateTimeFromToRangeFilter":
        """Validate that from_datetime <= to_datetime."""
        if self.from_datetime is not None and self.to_datetime is not None:
            if self.from_datetime > self.to_datetime:
                raise InvalidFormatError(
                    field="datetime_range",
                    details={
                        "from": str(self.from_datetime),
                        "to": str(self.to_datetime),
                        "reason": f"Start datetime ({self.from_datetime}) cannot be after end datetime ({self.to_datetime})",
                    },
                )
        return self

    def is_active(self) -> bool:
        """Check if filter has any value."""
        return self.from_datetime is not None or self.to_datetime is not None

    def to_sqlalchemy(self, column: Column) -> ColumnElement | None:
        """Convert to SQLAlchemy BETWEEN or comparison."""
        if not self.is_active():
            return None

        conditions = []
        if self.from_datetime is not None:
            conditions.append(column >= self.from_datetime)
        if self.to_datetime is not None:
            conditions.append(column <= self.to_datetime)

        return and_(*conditions) if len(conditions) > 1 else conditions[0]


class TimeRangeFilter(BaseModel):
    """
    Time range filter (time of day) with validation.

    Examples:
        - min=08:00:00, max=17:00:00 -> business hours
        - min=09:00 -> >= 09:00:00
    """

    min: time | None = Field(
        default=None, description="Start time (inclusive) in format HH:MM:SS"
    )
    max: time | None = Field(
        default=None, description="End time (inclusive) in format HH:MM:SS"
    )

    @field_validator("min", "max", mode="before")
    @classmethod
    def parse_time(cls, v: Any) -> time | None:
        """Parse time from string."""
        return parse_time_value(v)

    @model_validator(mode="after")
    def validate_range(self) -> "TimeRangeFilter":
        """Validate that min <= max."""
        if self.min is not None and self.max is not None:
            if self.min > self.max:
                raise InvalidFormatError(
                    field="time_range",
                    details={
                        "min": str(self.min),
                        "max": str(self.max),
                        "reason": f"Start time ({self.min}) cannot be after end time ({self.max})",
                    },
                )
        return self

    def is_active(self) -> bool:
        """Check if filter has any value."""
        return self.min is not None or self.max is not None

    def to_sqlalchemy(self, column: Column) -> ColumnElement | None:
        """Convert to SQLAlchemy time comparison."""
        if not self.is_active():
            return None

        conditions = []
        if self.min is not None:
            conditions.append(column >= self.min)
        if self.max is not None:
            conditions.append(column <= self.max)

        return and_(*conditions) if len(conditions) > 1 else conditions[0]


class ListFilter(BaseModel, Generic[T]):
    """
    List filter (IN clause) with automatic type validation.

    Automatically validates list values based on the generic type parameter.
    Supports: str, int, float, bool, UUID, and Enum types.

    Examples:
        - ListFilter[str]: Validates strings
        - ListFilter[int]: Validates and converts to integers
        - ListFilter[ProjectStatus]: Validates enum values
        - status=["active","pending"] -> status IN ('active', 'pending')
        - ids=[uuid1,uuid2] -> id IN (uuid1, uuid2)
    """

    values: list[T] | None = Field(
        default=None, description="List of values for IN clause"
    )

    @field_validator("values", mode="before")
    @classmethod
    def validate_values(cls, v: Any) -> list[Any] | None:
        """
        Validate list values based on generic type T.

        Supports:
        - Native types: str, int, float, bool, UUID
        - Enum types: Validates against enum values and converts strings to enum instances
        """
        if v is None:
            return None

        # Get the generic type from __pydantic_generic_metadata__
        generic_args = getattr(cls, "__pydantic_generic_metadata__", {}).get("args", ())
        if not generic_args:
            # Fallback: try to get from model fields (Pydantic v2)
            field_info = cls.model_fields.get("values")
            if field_info and hasattr(field_info, "annotation"):
                import typing

                if hasattr(typing, "get_args"):
                    inner_args = typing.get_args(field_info.annotation)
                    if inner_args:
                        # Extract T from Optional[List[T]]
                        if typing.get_origin(inner_args[0]) is list:
                            generic_args = typing.get_args(inner_args[0])

        if not generic_args:
            # No type info available, return as-is
            return v

        value_type = generic_args[0]

        # Handle List[T] - extract T
        if hasattr(value_type, "__origin__"):
            import typing

            if typing.get_origin(value_type) is list:
                value_type = typing.get_args(value_type)[0]

        validated_values = []
        invalid_values = []

        for item in v:
            # If already correct type, keep it
            if isinstance(item, value_type):
                validated_values.append(item)
                continue

            # Try to convert/validate
            try:
                # Enum validation
                if isinstance(value_type, type) and issubclass(value_type, Enum):
                    converted = value_type(item)
                    validated_values.append(converted)
                # UUID validation
                elif value_type is UUID:
                    if isinstance(item, str):
                        converted = UUID(item)
                        validated_values.append(converted)
                    else:
                        invalid_values.append(item)
                # Native types (str, int, float, bool)
                elif value_type in (str, int, float, bool):
                    converted = value_type(item)
                    validated_values.append(converted)
                else:
                    # Unknown type, try direct construction
                    converted = value_type(item)
                    validated_values.append(converted)
            except (ValueError, TypeError, KeyError):
                invalid_values.append(item)

        # Raise error if any invalid values
        if invalid_values:
            # Build error message based on type
            if isinstance(value_type, type) and issubclass(value_type, Enum):
                valid_values = [e.value for e in value_type]
                raise InvalidFormatError(
                    field="values",
                    details={
                        "invalid_values": invalid_values,
                        "valid_values": valid_values,
                        "type": value_type.__name__,
                        "reason": f"Invalid values for {value_type.__name__}. Must be one of: {', '.join(map(str, valid_values))}",
                    },
                )
            else:
                raise InvalidFormatError(
                    field="values",
                    details={
                        "invalid_values": invalid_values,
                        "expected_type": value_type.__name__,
                        "reason": f"Invalid values. Expected type: {value_type.__name__}",
                    },
                )

        return validated_values if validated_values else None

    def is_active(self) -> bool:
        """Check if filter has values."""
        return self.values is not None and len(self.values) > 0

    def to_sqlalchemy(self, column: Column) -> ColumnElement | None:
        """Convert to SQLAlchemy IN clause."""
        if not self.is_active():
            return None

        return column.in_(cast("list[T]", self.values))


# ===== TYPED ALIASES FOR COMMON USE CASES =====

StringListFilter = ListFilter[str]
"""List filter for string values (status, tags, etc.)"""

UUIDListFilter = ListFilter[UUID]
"""List filter for UUID values (IDs, foreign keys, etc.)"""

IntListFilter = ListFilter[int]
"""List filter for integer values (counts, quantities, etc.)"""


# ===== DEBUG HELPERS =====


def _debug_filter_sql(filter_instance: BaseModel, column: Column) -> str:
    """
    Debug helper to show SQL generated by a filter (for development/testing).

    Args:
        filter_instance: Any filter instance (SearchFilter, DateRangeFilter, etc.)
        column: SQLModel column

    Returns:
        String representation of SQL expression
    """
    if not hasattr(filter_instance, "to_sqlalchemy"):
        return "N/A (no to_sqlalchemy method)"

    expr = filter_instance.to_sqlalchemy(column)
    if expr is None:
        return "N/A (filter not active)"

    try:
        from sqlalchemy.dialects import postgresql

        compiled = expr.compile(
            dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}
        )
        return str(compiled)
    except Exception as e:
        return f"Error compiling SQL: {e!s}"


__all__ = [
    "BaseFilter",
    "BooleanFilter",
    "DateFilter",
    "DateFromToRangeFilter",
    "DateRangeFilter",
    "DateTimeFilter",
    "DateTimeFromToRangeFilter",
    "FilterLookup",
    "IntListFilter",
    "ListFilter",
    "NumberFilter",
    "NumericRangeFilter",
    "SearchFilter",
    "StringListFilter",
    "TimeRangeFilter",
    "UUIDListFilter",
]
