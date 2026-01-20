"""Tests for pagination functionality."""

from datetime import date, datetime, timezone

import pytest

from fastapi_restkit import (
    BooleanFilter,
    DateRangeFilter,
    FilterSet,
    InvalidFormatError,
    NumberFilter,
    PaginatedResponse,
    PaginationParams,
    SearchFilter,
    SortingParams,
)


class TestPaginationParams:
    """Tests for PaginationParams."""

    def test_default_values(self) -> None:
        """Test default pagination values."""
        params = PaginationParams()
        assert params.page == 1
        assert params.page_size == 10

    def test_custom_values(self) -> None:
        """Test custom pagination values."""
        params = PaginationParams(page=3, page_size=25)
        assert params.page == 3
        assert params.page_size == 25

    def test_offset_calculation(self) -> None:
        """Test offset calculation."""
        params = PaginationParams(page=3, page_size=10)
        assert params.offset == 20

    def test_limit_property(self) -> None:
        """Test limit property."""
        params = PaginationParams(page_size=50)
        assert params.limit == 50


class TestPaginatedResponse:
    """Tests for PaginatedResponse."""

    def test_create_response(self) -> None:
        """Test creating paginated response."""
        items = ["a", "b", "c"]
        pagination = PaginationParams(page=1, page_size=10)
        response = PaginatedResponse.create(items, total=25, pagination=pagination)

        assert response.items == items
        assert response.total == 25
        assert response.page == 1
        assert response.page_size == 10
        assert response.total_pages == 3
        assert response.has_next is True
        assert response.has_previous is False

    def test_last_page(self) -> None:
        """Test last page detection."""
        items = ["x"]
        pagination = PaginationParams(page=3, page_size=10)
        response = PaginatedResponse.create(items, total=25, pagination=pagination)

        assert response.has_next is False
        assert response.has_previous is True


class TestSearchFilter:
    """Tests for SearchFilter."""

    def test_active_filter(self) -> None:
        """Test active search filter."""
        f = SearchFilter(value="test")
        assert f.is_active() is True

    def test_inactive_filter(self) -> None:
        """Test inactive search filter."""
        f = SearchFilter()
        assert f.is_active() is False

    def test_sanitizes_whitespace(self) -> None:
        """Test whitespace sanitization."""
        f = SearchFilter(value="  test  ")
        assert f.value == "test"

    def test_empty_string_becomes_none(self) -> None:
        """Test empty string becomes None."""
        f = SearchFilter(value="   ")
        assert f.value is None
        assert f.is_active() is False


class TestBooleanFilter:
    """Tests for BooleanFilter."""

    def test_true_filter(self) -> None:
        """Test true boolean filter."""
        f = BooleanFilter(value=True)
        assert f.is_active() is True
        assert f.value is True

    def test_false_filter(self) -> None:
        """Test false boolean filter."""
        f = BooleanFilter(value=False)
        assert f.is_active() is True
        assert f.value is False


class TestNumberFilter:
    """Tests for NumberFilter."""

    def test_number_filter(self) -> None:
        """Test number filter."""
        f = NumberFilter(value=42.5)
        assert f.is_active() is True
        assert f.value == 42.5


class TestDateRangeFilter:
    """Tests for DateRangeFilter."""

    def test_date_range(self) -> None:
        """Test valid date range."""
        f = DateRangeFilter(min=date(2024, 1, 1), max=date(2024, 12, 31))
        assert f.is_active() is True
        assert f.min == date(2024, 1, 1)
        assert f.max == date(2024, 12, 31)

    def test_parse_date_strings(self) -> None:
        """Test parsing date strings."""
        f = DateRangeFilter(min="2024-01-01", max="2024-12-31")
        assert f.min == date(2024, 1, 1)
        assert f.max == date(2024, 12, 31)

    def test_invalid_range_raises_error(self) -> None:
        """Test that invalid range raises error."""
        with pytest.raises(InvalidFormatError):
            DateRangeFilter(min=date(2024, 12, 31), max=date(2024, 1, 1))


class TestSortingParams:
    """Tests for SortingParams."""

    def test_empty_sorting(self) -> None:
        """Test empty sorting."""
        params = SortingParams()
        assert params.is_empty() is True

    def test_parse_sort_fields(self) -> None:
        """Test parsing sort fields."""
        params = SortingParams(sort_by=["name:asc", "created_at:desc"])
        fields = params.get_sort_fields()

        assert len(fields) == 2
        assert fields[0].field == "name"
        assert fields[0].order.value == "asc"
        assert fields[1].field == "created_at"
        assert fields[1].order.value == "desc"

    def test_default_order_is_asc(self) -> None:
        """Test default sort order is ascending."""
        params = SortingParams(sort_by=["name"])
        fields = params.get_sort_fields()

        assert fields[0].order.value == "asc"

    def test_invalid_format_raises_error(self) -> None:
        """Test that invalid format raises error."""
        params = SortingParams(sort_by=["name :desc"])  # space before colon
        with pytest.raises(InvalidFormatError):
            params.get_sort_fields()


class TestFilterSet:
    """Tests for FilterSet."""

    def test_get_active_filters(self) -> None:
        """Test getting active filters."""

        class MyFilterSet(FilterSet):
            search: SearchFilter | None = None
            is_active: BooleanFilter | None = None

        filters = MyFilterSet(
            search=SearchFilter(value="test"),
            is_active=None,
        )
        active = filters.get_active_filters()

        assert "search" in active
        assert "is_active" not in active
