"""
FilterSet - Base class for domain-specific filters.

Inspired by Django django-filter, provides automatic SQLAlchemy expression generation.
"""

import inspect
import logging
from collections.abc import Callable
from typing import (
    Any,
    Literal,
    Optional,
    TypeVar,
    Union,
    get_args,
    get_origin,
)

from fastapi import Query
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy.orm import Load, defer, joinedload, load_only, selectinload
from sqlalchemy.sql import ColumnElement
from sqlmodel import SQLModel, and_, or_

from fastapi_restkit.exceptions import InvalidFormatError
from fastapi_restkit.filters import (
    BaseFilter,
    BooleanFilter,
    DateFilter,
    DateFromToRangeFilter,
    DateRangeFilter,
    DateTimeFilter,
    DateTimeFromToRangeFilter,
    ListFilter,
    NumberFilter,
    NumericRangeFilter,
    TimeRangeFilter,
)

TFilterSet = TypeVar("TFilterSet", bound="FilterSet")

logger = logging.getLogger(__name__)


class FilterSet(BaseModel):
    """
    Base class for creating domain-specific filter sets.

    Automatically generates SQLAlchemy expressions from filter fields.

    Usage:
        ```python
        class PermissionFilterSet(FilterSet):
            # Auto-mapped (field name = column name)
            resource: Optional[SearchFilter] = Field(default_factory=SearchFilter)
            action: Optional[ListFilter] = Field(default_factory=ListFilter)
            is_system_permission: Optional[BooleanFilter] = Field(
                default_factory=BooleanFilter
            )

            # Multi-column search (requires field_columns)
            search: Optional[SearchFilter] = Field(default_factory=SearchFilter)

            class Config:
                # Only map fields that:
                # 1. Search across multiple columns (list of column names)
                # 2. Have different field/column names
                field_columns = {
                    "search": ["resource", "action", "description"],  # Multi-column OR
                    # No need to map "resource", "action", "is_system_permission" - auto-mapped!
                }


        # In controller
        filters = PermissionFilterSet(
            search="project",
            action=ListFilter(values=["create", "read"]),
            is_system_permission=BooleanFilter(value=False),
        )

        # Generate SQLAlchemy expressions
        conditions = filters.to_sqlalchemy(Permission)  # Default: AND between filters

        # Use in query (AND: resource='project' AND action IN (...) AND is_system_permission=false)
        query = select(Permission).where(and_(*conditions))

        # Or use OR between filters
        or_conditions = filters.to_sqlalchemy(Permission, use_or=True)
        query = select(Permission).where(*or_conditions)
        ```

    Expansion and omission of relationships and columns:
        FilterSet also supports expanding SQLModel relationships via query params
        and configuration on the FilterSet Config class.

        - expand: Relationship names to eager-load
        - omit: Relationship or column names to exclude

        Config options:
            expandable: Dict of {api_name: relationship_path}
                - api_name is the query parameter name
                - relationship_path is the attribute path on the SQLModel
                - if a value is omitted, api_name is used as the path

            default_expand: Set or list of api_names expanded by default
            default_joined: Set or list of api_names that use joinedload
            expand_all: If True, expands all expandable fields by default

            column_fields: Dict of {api_name: column_path}
                - api_name is the query parameter name
                - column_path is the attribute path on the SQLModel
                - if a value is omitted, api_name is used as the path

            column_omit_mode: Strategy for column omission
                - "defer" (default): defers omitted columns
                - "load_only": loads only non-omitted columns
    """

    expand: list[str] = Field(
        default_factory=list,
        description="Relationships to expand (eager load)",
    )
    only: list[str] = Field(
        default_factory=list,
        description="Only include these relationships or columns",
    )
    omit: list[str] = Field(
        default_factory=list,
        description="Relationships or columns to omit",
    )

    class Config:
        """Configuration for FilterSet."""

        # Optional: Map filter field names to SQLModel column names
        field_columns: dict[str, str | list[str]] = {}

        # Model class for type checking
        model_class: type[SQLModel] | None = None

        # Relationship expansion configuration
        # Map api_name -> relationship path on the model
        expandable: dict[str, str] = {}
        # Expand all expandable relationships by default
        expand_all: bool = False
        # Expand these relationships by default
        default_expand: set[str] | list[str] = set()
        # Use joinedload for these relationships (allowlist)
        default_joined: set[str] | list[str] = set()

        # Column omission configuration
        # Map api_name -> column path on the model
        column_fields: dict[str, str] = {}
        # Strategy for omitting columns: "defer" or "load_only"
        column_omit_mode: Literal["defer", "load_only"] = "defer"

    def model_post_init(self, __context: Any) -> None:
        """
        Validate field_columns configuration after initialization.

        Raises:
            ValueError: If field_columns references non-existent fields
        """
        if not hasattr(self, "Config") or not hasattr(self.Config, "field_columns"):
            return

        field_columns = getattr(self.Config, "field_columns", {})
        if not field_columns:
            return

        # Validate that all keys in field_columns exist as fields
        invalid_fields = [
            field_name
            for field_name in field_columns
            if field_name not in self.model_fields
        ]

        if invalid_fields:
            logger.error(
                "Invalid field_columns configuration",
                extra={
                    "filterset_class": self.__class__.__name__,
                    "invalid_fields": invalid_fields,
                    "available_fields": list(self.model_fields.keys()),
                },
            )

            raise ValueError(
                f"field_columns contains non-existent fields in {self.__class__.__name__}: "
                f"{', '.join(invalid_fields)}. "
                f"Available fields: {', '.join(self.model_fields.keys())}"
            )

    def get_active_filters(self) -> dict[str, Any]:
        """
        Get all active filters (with values).

        Returns:
            Dict of field_name -> filter_instance for active filters
        """
        active = {}
        for field_name, field_value in self.model_dump().items():
            if field_value is None:
                continue

            # Get the actual filter instance
            filter_instance = getattr(self, field_name)
            if filter_instance and hasattr(filter_instance, "is_active"):
                if filter_instance.is_active():
                    active[field_name] = filter_instance

        return active

    def get_expandable_fields(self) -> dict[str, str]:
        """
        Get the expandable relationship mapping from Config.

        Returns:
            Dict of api_name -> relationship_path
        """
        if not hasattr(self, "Config"):
            return {}
        expandable = getattr(self.Config, "expandable", {}) or {}
        normalized: dict[str, str] = {}

        for name, path in expandable.items():
            if path:
                normalized[name] = path
            else:
                normalized[name] = name
        return normalized

    def get_column_fields(self) -> dict[str, str]:
        """
        Get the omittable column mapping from Config.

        Returns:
            Dict of api_name -> column_path
        """
        if not hasattr(self, "Config"):
            return {}
        column_fields = getattr(self.Config, "column_fields", {}) or {}
        normalized: dict[str, str] = {}

        for name, path in column_fields.items():
            if path:
                normalized[name] = path
            else:
                normalized[name] = name
        return normalized

    def _get_default_expand(self) -> set[str]:
        if not hasattr(self, "Config"):
            return set()
        default_expand = getattr(self.Config, "default_expand", set()) or set()
        return set(default_expand)

    def _get_default_joined(self) -> set[str]:
        if not hasattr(self, "Config"):
            return set()
        default_joined = getattr(self.Config, "default_joined", set()) or set()
        return set(default_joined)

    def resolve_omit_fields(self) -> tuple[set[str], set[str]]:
        """
        Resolve omit fields into relationship and column sets.

        Returns:
            Tuple of (relationship_omits, column_omits)

        Raises:
            InvalidFormatError: If omit includes invalid fields
        """
        expandable = self.get_expandable_fields()
        column_fields = self.get_column_fields()
        omits = set(self.omit or [])

        invalid_omits = omits - set(expandable.keys()) - set(column_fields.keys())
        if invalid_omits:
            valid_fields = set(expandable.keys()) | set(column_fields.keys())
            raise InvalidFormatError(
                field="omit",
                details={
                    "invalid_fields": sorted(invalid_omits),
                    "valid_fields": sorted(valid_fields),
                },
            )

        relationship_omits = omits & set(expandable.keys())
        column_omits = omits & set(column_fields.keys())
        return relationship_omits, column_omits

    def resolve_only_fields(self) -> tuple[set[str], set[str]]:
        """
        Resolve only fields into relationship and column sets.

        Returns:
            Tuple of (relationship_only, column_only)

        Raises:
            InvalidFormatError: If only includes invalid fields
        """
        expandable = self.get_expandable_fields()
        column_fields = self.get_column_fields()
        only_fields = set(self.only or [])

        if not only_fields:
            return set(), set()

        if not expandable and not column_fields:
            raise InvalidFormatError(
                field="only",
                details={"reason": "No fields are configured for only"},
            )

        valid_fields = set(expandable.keys()) | set(column_fields.keys())
        invalid_only = only_fields - valid_fields
        if invalid_only:
            raise InvalidFormatError(
                field="only",
                details={
                    "invalid_fields": sorted(invalid_only),
                    "valid_fields": sorted(valid_fields),
                },
            )

        relationship_only = only_fields & set(expandable.keys())
        column_only = only_fields & set(column_fields.keys())
        return relationship_only, column_only

    def resolve_expands(self) -> set[str]:
        """
        Resolve expand fields based on Config and query params.

        Returns:
            Set of api_names to expand

        Raises:
            InvalidFormatError: If requested expand/omit includes invalid fields
        """
        expandable = self.get_expandable_fields()
        if not expandable and self.expand:
            raise InvalidFormatError(
                field="expand",
                details={"reason": "No expandable relationships are configured"},
            )

        only_relations, _ = self.resolve_only_fields()
        expand_all = bool(getattr(self.Config, "expand_all", False))
        default_expand = self._get_default_expand()

        if only_relations:
            base = set()
            requested = set(only_relations)
        else:
            base = set(expandable.keys()) if expand_all else set(default_expand)
            requested = set(self.expand or [])
        omits, _ = self.resolve_omit_fields()
        resolved = base | requested

        invalid_expands = resolved - set(expandable.keys())
        if invalid_expands:
            raise InvalidFormatError(
                field="expand",
                details={
                    "invalid_fields": sorted(invalid_expands),
                    "valid_fields": sorted(expandable.keys()),
                },
            )

        return resolved - omits

    def to_sqlalchemy_column_options(self, model_class: type[SQLModel]) -> list[Load]:
        """
        Build SQLAlchemy load options for omitting columns.

        Args:
            model_class: SQLModel class to load columns from

        Returns:
            List of SQLAlchemy Load options
        """
        column_fields = self.get_column_fields()
        if not column_fields:
            return []

        _, column_only = self.resolve_only_fields()
        omit_mode = getattr(self.Config, "column_omit_mode", "defer")
        options: list[Load] = []

        if column_only:
            columns = [
                self._get_column(model_class, column_fields[name])
                for name in sorted(column_only)
            ]
            options.append(load_only(*columns))
            return options

        _, column_omits = self.resolve_omit_fields()
        if not column_omits:
            return []

        if omit_mode == "load_only":
            include_names = set(column_fields.keys()) - column_omits
            if not include_names:
                return []
            columns = [
                self._get_column(model_class, column_fields[name])
                for name in sorted(include_names)
            ]
            options.append(load_only(*columns))
            return options

        if omit_mode == "defer":
            for name in sorted(column_omits):
                column = self._get_column(model_class, column_fields[name])
                options.append(defer(column))
            return options

        raise InvalidFormatError(
            field="omit",
            details={"invalid_mode": omit_mode, "expected": ["defer", "load_only"]},
        )

    def to_sqlalchemy_load_options(self, model_class: type[SQLModel]) -> list[Load]:
        """
        Build SQLAlchemy load options for expanded relationships.

        Args:
            model_class: SQLModel class to load relationships from

        Returns:
            List of SQLAlchemy Load options
        """
        expandable = self.get_expandable_fields()
        expands = self.resolve_expands()
        default_joined = self._get_default_joined()
        options: list[Load] = []

        for api_name in sorted(expands):
            path = expandable[api_name]
            use_joined = api_name in default_joined
            options.append(self._build_load_option(model_class, path, use_joined))

        return options

    def apply_expands_to_query(self, query, model_class: type[SQLModel]):
        """
        Apply relationship expansion and column omission options to a query.

        Args:
            query: SQLAlchemy select query
            model_class: SQLModel class to load relationships from

        Returns:
            Query with eager loading and column options applied
        """
        options = self.to_sqlalchemy_load_options(model_class)
        options.extend(self.to_sqlalchemy_column_options(model_class))
        if options:
            return query.options(*options)
        return query

    def _build_load_option(
        self, model_class: type[SQLModel], relationship_path: str, use_joined: bool
    ) -> Load:
        """
        Build a SQLAlchemy load option for a relationship path.

        Args:
            model_class: SQLModel class to load from
            relationship_path: Dot notation path (e.g. "author.company")
            use_joined: Use joinedload when True, else selectinload

        Returns:
            SQLAlchemy Load option

        Raises:
            InvalidFormatError: If relationship path is invalid
        """
        parts = relationship_path.split(".")
        if not parts:
            raise InvalidFormatError(
                field="expand",
                details={"invalid_path": relationship_path},
            )

        if not hasattr(model_class, parts[0]):
            raise InvalidFormatError(
                field="expand",
                details={"invalid_path": relationship_path},
            )

        current_attr = getattr(model_class, parts[0])
        option: Load
        option = joinedload(current_attr) if use_joined else selectinload(current_attr)

        current_model = model_class
        for part in parts[1:]:
            if not hasattr(current_attr, "property") or not hasattr(
                current_attr.property, "mapper"
            ):
                raise InvalidFormatError(
                    field="expand",
                    details={"invalid_path": relationship_path},
                )

            current_model = current_attr.property.mapper.class_
            if not hasattr(current_model, part):
                raise InvalidFormatError(
                    field="expand",
                    details={"invalid_path": relationship_path},
                )
            current_attr = getattr(current_model, part)
            if use_joined:
                option = option.joinedload(current_attr)
            else:
                option = option.selectinload(current_attr)

        return option

    def to_sqlalchemy(
        self, model_class: type[SQLModel], use_or: bool = False
    ) -> list[ColumnElement]:
        """
        Generate SQLAlchemy expressions from active filters.

        Args:
            model_class: SQLModel class to filter
            use_or: If True, combine conditions with OR instead of AND (default: AND)

        Returns:
            List of SQLAlchemy expressions

        Raises:
            ValueError: If column not found in model
        """
        # Get field_columns config or empty dict
        field_columns = (
            getattr(self.Config, "field_columns", {}) if hasattr(self, "Config") else {}
        )

        conditions = []

        for field_name, filter_instance in self.get_active_filters().items():
            # Get column mapping
            column_mapping = field_columns.get(field_name)

            # Auto-map if not explicitly configured
            if column_mapping is None:
                # Check if model has a column with the same name as the field
                if hasattr(model_class, field_name):
                    column_mapping = field_name
                else:
                    # Skip unmapped fields that don't exist in model
                    continue

            # Handle multiple columns (OR condition for search across fields)
            if isinstance(column_mapping, list):
                or_conditions = []
                for col_name in column_mapping:
                    column = self._get_column(model_class, col_name)
                    expr = filter_instance.to_sqlalchemy(column)
                    if expr is not None:
                        or_conditions.append(expr)

                if or_conditions:
                    # Use OR for multiple columns within same field
                    conditions.append(or_(*or_conditions))
            else:
                # Single column
                column = self._get_column(model_class, column_mapping)
                expr = filter_instance.to_sqlalchemy(column)
                if expr is not None:
                    conditions.append(expr)

        # If use_or=True, combine all conditions with OR
        if use_or and len(conditions) > 1:
            return [or_(*conditions)]

        return conditions

    def _get_column(self, model_class: type[SQLModel], column_name: str):
        """
        Get column from model class with detailed error logging.

        Supports relationship traversal using dot notation (e.g., 'index_type.code').

        Args:
            model_class: SQLModel class
            column_name: Name of the column to retrieve

        Returns:
            Column attribute from model or related model

        Raises:
            ValueError: If column not found in model
        """
        # Support relationship traversal with dot notation
        if "." in column_name:
            parts = column_name.split(".")
            current_model = model_class
            current_attr = None

            for part in parts:
                if not hasattr(current_model, part):
                    break
                current_attr = getattr(current_model, part)

                # If this is a relationship, get the related model
                if hasattr(current_attr, "mapper") and hasattr(
                    current_attr.mapper, "class_"
                ):
                    current_model = current_attr.mapper.class_
                else:
                    break
            else:
                current_attr = None

            if current_attr is not None:
                return current_attr

        # Fallback to simple attribute access
        if hasattr(model_class, column_name):
            return getattr(model_class, column_name)

        # Get available columns for helpful error message
        available_columns = [
            name
            for name in dir(model_class)
            if not name.startswith("_")
            and hasattr(getattr(model_class, name, None), "__class__")
        ]

        logger.error(
            "Invalid filter column mapping",
            extra={
                "model": model_class.__name__,
                "requested_column": column_name,
                "available_columns": available_columns[:10],
                "filter_set": self.__class__.__name__,
            },
        )

        raise ValueError(
            f"Column '{column_name}' not found in model {model_class.__name__}. "
            f"Available columns: {', '.join(available_columns[:5])}..."
        )

    def apply_to_query(self, query, model_class: type[SQLModel]):
        """
        Apply filters to a SQLModel query.

        Args:
            query: SQLAlchemy select query
            model_class: SQLModel class

        Returns:
            Query with filters applied
        """
        conditions = self.to_sqlalchemy(model_class)
        if conditions:
            return query.where(and_(*conditions))
        return query


def _unwrap_optional(annotation: Any) -> Any:
    """Return the non-None type when annotation is Optional."""
    origin = get_origin(annotation)
    if origin is Union:
        args = [arg for arg in get_args(annotation) if arg is not type(None)]
        if len(args) == 1:
            return args[0]
    return annotation


def _is_filter_type(annotation: Any, filter_type: Any) -> bool:
    """Check whether annotation corresponds to a filter type."""
    try:
        return isinstance(annotation, type) and issubclass(annotation, filter_type)
    except TypeError:
        return False


# ===== FILTER BUILDER FUNCTIONS =====


def _build_base_filter_params(
    field_name: str,
    field_info: Any,
    field_type: type,
    params: list[inspect.Parameter],
    builders: list[Callable],
) -> bool:
    """Build params for BaseFilter derivatives (SearchFilter, BooleanFilter, etc.)."""
    if not _is_filter_type(field_type, BaseFilter):
        return False

    description = field_info.description or f"Filter by {field_name}"

    # Determine python type for value
    value_type: Any = str
    if _is_filter_type(field_type, BooleanFilter):
        value_type = bool
    elif _is_filter_type(field_type, NumberFilter):
        value_type = float
    elif _is_filter_type(field_type, DateFilter) or _is_filter_type(
        field_type, DateTimeFilter
    ):
        value_type = str

    value_param = f"{field_name}_value"
    params.append(
        inspect.Parameter(
            value_param,
            inspect.Parameter.KEYWORD_ONLY,
            default=Query(default=None, alias=field_name, description=description),
            annotation=Optional[value_type],
        )
    )

    lookup_param = f"{field_name}_lookup"
    params.append(
        inspect.Parameter(
            lookup_param,
            inspect.Parameter.KEYWORD_ONLY,
            default=Query(
                default=None,
                alias=f"{field_name}[lookup]",
                description=f"Lookup operator for {field_name} (e.g. exact, icontains)",
            ),
            annotation=Optional[str],
        )
    )

    def build_base(
        raw_kwargs: dict[str, Any],
        data: dict[str, Any],
        *,
        _field_name: str = field_name,
        _value_param: str = value_param,
        _lookup_param: str = lookup_param,
        _field_type: type = field_type,
    ) -> None:
        value = raw_kwargs.get(_value_param)
        lookup = raw_kwargs.get(_lookup_param)
        if value is None and lookup is None:
            return

        payload: dict[str, Any] = {}
        if value is not None:
            payload["value"] = value
        if lookup is not None:
            payload["lookup"] = lookup
        data[_field_name] = _field_type(**payload)

    builders.append(build_base)
    return True


def _build_list_filter_params(
    field_name: str,
    field_info: Any,
    field_type: type,
    params: list[inspect.Parameter],
    builders: list[Callable],
) -> bool:
    """Build params for ListFilter."""
    if not _is_filter_type(field_type, ListFilter):
        return False

    description = field_info.description or f"Filter by {field_name}"
    values_param = f"{field_name}_values"

    params.append(
        inspect.Parameter(
            values_param,
            inspect.Parameter.KEYWORD_ONLY,
            default=Query(default=None, alias=field_name, description=description),
            annotation=Optional[list[str]],
        )
    )

    def build_list(
        raw_kwargs: dict[str, Any],
        data: dict[str, Any],
        *,
        _field_name: str = field_name,
        _values_param: str = values_param,
        _field_type: type = field_type,
        _field_info: Any = field_info,
    ) -> None:
        values = raw_kwargs.get(_values_param)
        if not values:
            return

        import typing

        original_type = (
            _field_info.annotation
            if hasattr(_field_info, "annotation")
            else _field_type
        )

        if hasattr(typing, "get_origin") and typing.get_origin(original_type) is Union:
            args = typing.get_args(original_type)
            original_type = next(
                (arg for arg in args if arg is not type(None)), _field_type
            )

        data[_field_name] = original_type(values=list(values))

    builders.append(build_list)
    return True


def _build_range_filter_params(
    field_name: str,
    field_info: Any,
    field_type: type,
    params: list[inspect.Parameter],
    builders: list[Callable],
) -> bool:
    """Build params for range filters (DateRangeFilter, NumericRangeFilter, TimeRangeFilter)."""
    if not _is_filter_type(
        field_type, (DateRangeFilter, NumericRangeFilter, TimeRangeFilter)
    ):
        return False

    min_param = f"{field_name}_min"
    max_param = f"{field_name}_max"

    params.append(
        inspect.Parameter(
            min_param,
            inspect.Parameter.KEYWORD_ONLY,
            default=Query(
                default=None,
                alias=f"{field_name}[min]",
                description=f"Minimum value for {field_name}",
            ),
            annotation=Optional[str],
        )
    )
    params.append(
        inspect.Parameter(
            max_param,
            inspect.Parameter.KEYWORD_ONLY,
            default=Query(
                default=None,
                alias=f"{field_name}[max]",
                description=f"Maximum value for {field_name}",
            ),
            annotation=Optional[str],
        )
    )

    def build_range(
        raw_kwargs: dict[str, Any],
        data: dict[str, Any],
        *,
        _field_name: str = field_name,
        _min_param: str = min_param,
        _max_param: str = max_param,
        _field_type: type = field_type,
    ) -> None:
        min_value = raw_kwargs.get(_min_param)
        max_value = raw_kwargs.get(_max_param)
        if min_value is None and max_value is None:
            return
        payload: dict[str, Any] = {}
        if min_value is not None:
            payload["min"] = min_value
        if max_value is not None:
            payload["max"] = max_value
        data[_field_name] = _field_type(**payload)

    builders.append(build_range)
    return True


def _build_from_to_filter_params(
    field_name: str,
    field_info: Any,
    field_type: type,
    params: list[inspect.Parameter],
    builders: list[Callable],
) -> bool:
    """Build params for DateFromToRangeFilter."""
    if not _is_filter_type(field_type, DateFromToRangeFilter):
        return False

    from_param = f"{field_name}_from"
    to_param = f"{field_name}_to"

    params.append(
        inspect.Parameter(
            from_param,
            inspect.Parameter.KEYWORD_ONLY,
            default=Query(
                default=None,
                alias=f"{field_name}[from]",
                description=f"Start value for {field_name}",
            ),
            annotation=Optional[str],
        )
    )
    params.append(
        inspect.Parameter(
            to_param,
            inspect.Parameter.KEYWORD_ONLY,
            default=Query(
                default=None,
                alias=f"{field_name}[to]",
                description=f"End value for {field_name}",
            ),
            annotation=Optional[str],
        )
    )

    def build_from_to(
        raw_kwargs: dict[str, Any],
        data: dict[str, Any],
        *,
        _field_name: str = field_name,
        _from_param: str = from_param,
        _to_param: str = to_param,
        _field_type: type = field_type,
    ) -> None:
        start_value = raw_kwargs.get(_from_param)
        end_value = raw_kwargs.get(_to_param)
        if start_value is None and end_value is None:
            return
        payload: dict[str, Any] = {}
        if start_value is not None:
            payload["from_date"] = start_value
        if end_value is not None:
            payload["to_date"] = end_value
        data[_field_name] = _field_type(**payload)

    builders.append(build_from_to)
    return True


def _build_datetime_from_to_filter_params(
    field_name: str,
    field_info: Any,
    field_type: type,
    params: list[inspect.Parameter],
    builders: list[Callable],
) -> bool:
    """Build params for DateTimeFromToRangeFilter."""
    if not _is_filter_type(field_type, DateTimeFromToRangeFilter):
        return False

    from_param = f"{field_name}_from"
    to_param = f"{field_name}_to"

    params.append(
        inspect.Parameter(
            from_param,
            inspect.Parameter.KEYWORD_ONLY,
            default=Query(
                default=None,
                alias=f"{field_name}[from]",
                description=f"Start datetime for {field_name}",
            ),
            annotation=Optional[str],
        )
    )
    params.append(
        inspect.Parameter(
            to_param,
            inspect.Parameter.KEYWORD_ONLY,
            default=Query(
                default=None,
                alias=f"{field_name}[to]",
                description=f"End datetime for {field_name}",
            ),
            annotation=Optional[str],
        )
    )

    def build_datetime_from_to(
        raw_kwargs: dict[str, Any],
        data: dict[str, Any],
        *,
        _field_name: str = field_name,
        _from_param: str = from_param,
        _to_param: str = to_param,
        _field_type: type = field_type,
    ) -> None:
        start_value = raw_kwargs.get(_from_param)
        end_value = raw_kwargs.get(_to_param)
        if start_value is None and end_value is None:
            return
        payload: dict[str, Any] = {}
        if start_value is not None:
            payload["from_datetime"] = start_value
        if end_value is not None:
            payload["to_datetime"] = end_value
        data[_field_name] = _field_type(**payload)

    builders.append(build_datetime_from_to)
    return True


def _build_fallback_filter_params(
    field_name: str,
    field_info: Any,
    field_type: type,
    params: list[inspect.Parameter],
    builders: list[Callable],
) -> bool:
    """Fallback builder - accept raw value as string."""
    description = field_info.description or f"Filter by {field_name}"
    fallback_param = f"{field_name}_raw"

    params.append(
        inspect.Parameter(
            fallback_param,
            inspect.Parameter.KEYWORD_ONLY,
            default=Query(default=None, alias=field_name, description=description),
            annotation=Optional[str],
        )
    )

    def build_fallback(
        raw_kwargs: dict[str, Any],
        data: dict[str, Any],
        *,
        _field_name: str = field_name,
        _param: str = fallback_param,
    ) -> None:
        value = raw_kwargs.get(_param)
        if value is None:
            return
        data[_field_name] = value

    builders.append(build_fallback)
    return True


def _normalize_list_values(values: list[str] | None) -> list[str]:
    """Normalize list values from query params, supporting CSV and repeated args."""
    if not values:
        return []

    normalized: list[str] = []
    for value in values:
        if value is None:
            continue
        for part in str(value).split(","):
            item = part.strip()
            if item:
                normalized.append(item)
    return normalized


def filter_as_query(filter_cls: type[TFilterSet]) -> Callable[..., TFilterSet]:
    """
    Create a FastAPI dependency that documents FilterSet query params.

    Args:
        filter_cls: FilterSet class to generate dependency for

    Returns:
        FastAPI dependency function with proper signature

    Raises:
        InvalidFormatError: If filter validation fails
    """
    params: list[inspect.Parameter] = []
    builders: list[Callable[[dict[str, Any], dict[str, Any]], None]] = []

    # Chain of responsibility pattern for filter builders
    filter_builders = [
        _build_base_filter_params,
        _build_list_filter_params,
        _build_range_filter_params,
        _build_from_to_filter_params,
        _build_datetime_from_to_filter_params,
        _build_fallback_filter_params,
    ]

    expandable = (
        getattr(filter_cls.Config, "expandable", {})
        if hasattr(filter_cls, "Config")
        else {}
    )
    expand_fields = list(expandable.keys()) if expandable else []
    expand_description = "Relationships to expand (eager load)."
    if expand_fields:
        expand_description += "\n\n**Available relationships**\n" + "\n".join(
            [f"- `{name}`" for name in expand_fields]
        )

    params.append(
        inspect.Parameter(
            "expand_values",
            inspect.Parameter.KEYWORD_ONLY,
            default=Query(
                default=None,
                alias="expand",
                description=expand_description,
            ),
            annotation=Optional[list[str]],
        )
    )
    params.append(
        inspect.Parameter(
            "only_values",
            inspect.Parameter.KEYWORD_ONLY,
            default=Query(
                default=None,
                alias="only",
                description="Only include these relationships or columns.",
            ),
            annotation=Optional[list[str]],
        )
    )
    params.append(
        inspect.Parameter(
            "omit_values",
            inspect.Parameter.KEYWORD_ONLY,
            default=Query(
                default=None,
                alias="omit",
                description="Relationships or columns to omit.",
            ),
            annotation=Optional[list[str]],
        )
    )

    def build_expand_omit(raw_kwargs: dict[str, Any], data: dict[str, Any]) -> None:
        expand_values = raw_kwargs.get("expand_values")
        only_values = raw_kwargs.get("only_values")
        omit_values = raw_kwargs.get("omit_values")
        data["expand"] = _normalize_list_values(expand_values)
        data["only"] = _normalize_list_values(only_values)
        data["omit"] = _normalize_list_values(omit_values)

    builders.append(build_expand_omit)

    for field_name, field_info in filter_cls.model_fields.items():
        if field_name in {"expand", "only", "omit"}:
            continue
        field_type = _unwrap_optional(field_info.annotation)

        if field_type is None:
            continue

        # Try each builder until one handles it
        for builder_func in filter_builders:
            if builder_func(field_name, field_info, field_type, params, builders):
                break

    def dependency(**kwargs: Any) -> TFilterSet:
        """Dependency that builds FilterSet from query params."""
        payload: dict[str, Any] = {}

        try:
            # Apply all builders
            for builder in builders:
                try:
                    builder(kwargs, payload)
                except InvalidFormatError:
                    raise
                except Exception as e:
                    logger.warning(
                        "Filter builder failed - skipping field",
                        extra={
                            "filter_class": filter_cls.__name__,
                            "error": str(e),
                        },
                    )
                    continue

            # Build FilterSet instance
            return filter_cls(**payload)

        except ValidationError as e:
            error_details = {
                "filter_class": filter_cls.__name__,
                "validation_errors": [
                    {
                        "field": str(err["loc"][0]) if err["loc"] else "unknown",
                        "message": err["msg"],
                    }
                    for err in e.errors()
                ],
            }

            logger.error(
                "FilterSet validation failed",
                extra=error_details,
                exc_info=True,
            )

            raise InvalidFormatError(field="filters", details=error_details)

        except InvalidFormatError:
            raise

        except Exception as e:
            logger.error(
                "Unexpected error building FilterSet",
                extra={"filter_class": filter_cls.__name__, "error": str(e)},
                exc_info=True,
            )
            raise

    sig = inspect.Signature(parameters=params, return_annotation=filter_cls)
    dependency.__signature__ = sig  # type: ignore[attr-defined]
    dependency.__name__ = f"{filter_cls.__name__}QueryDependency"
    return dependency


__all__ = [
    "FilterSet",
    "filter_as_query",
]
