# FastAPI RestKit

[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![PyPI](https://img.shields.io/pypi/v/fastapi-restkit.svg)](https://pypi.org/project/fastapi-restkit/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

A complete REST toolkit for FastAPI with SQLModel ORM - featuring pagination, filtering, and sorting.

## Features

- 🚀 **Easy pagination** with customizable page sizes
- 🔍 **Powerful filtering** with Django-style filter lookups
- 📊 **Flexible sorting** with multi-field support
- 📦 **Generic response models** with full type hints
- ⚡ **FastAPI dependencies** ready to use
- 🔄 **Async support** out of the box
- 📝 **Auto-generated OpenAPI docs** for all parameters

## Installation

```bash
pip install fastapi-restkit
```

Or with uv:

```bash
uv add fastapi-restkit
```

## Table of Contents

- [Quick Start](#quick-start)
- [Pagination](#pagination)
- [Filtering](#filtering)
  - [Available Filter Types](#available-filter-types)
  - [Lookup Operators](#lookup-operators)
  - [Creating a FilterSet](#creating-a-filterset)
  - [URL Examples](#filter-url-examples)
- [Sorting](#sorting)
  - [Creating a SortingSet](#creating-a-sortingset)
  - [URL Examples](#sorting-url-examples)
- [Complete Example](#complete-example)
- [Development](#development)

---

## Quick Start

```python
from fastapi import FastAPI, Depends
from sqlmodel import Session, select
from fastapi_restkit import PaginationParams, paginate, PaginatedResponse

app = FastAPI()

@app.get("/items", response_model=PaginatedResponse[Item])
async def list_items(
    session: Session = Depends(get_session),
    pagination: PaginationParams = Depends(),
):
    return await paginate(session, select(Item), pagination)
```

---

## Pagination

Simple pagination with configurable page size:

```python
from fastapi_restkit import PaginationParams, paginate, PaginatedResponse

@app.get("/products", response_model=PaginatedResponse[Product])
async def list_products(
    session: Session = Depends(get_session),
    pagination: PaginationParams = Depends(),
):
    query = select(Product)
    return await paginate(session, query, pagination)
```

**URL Examples:**
```bash
GET /products?page=1&page_size=20
GET /products?page=2&page_size=50
```

---

## Filtering

### Available Filter Types

| Filter | Description | Value Type | URL Example |
|--------|-------------|------------|-------------|
| `SearchFilter` | Text search (case-insensitive) | `str` | `?name=laptop` |
| `BooleanFilter` | Boolean filter | `bool` | `?is_active=true` |
| `NumberFilter` | Numeric with comparisons | `float` | `?price=99.99` |
| `ListFilter[T]` | List of values (IN clause) | `list` | `?status=active&status=pending` |
| `DateFilter` | Date filter | `date` | `?created_at=2024-01-15` |
| `DateRangeFilter` | Date range (min/max) | `date` | `?created_at[min]=2024-01-01` |
| `DateTimeFilter` | DateTime filter | `datetime` | `?updated_at=2024-01-15T10:30:00Z` |
| `NumericRangeFilter` | Numeric range | `float` | `?price[min]=10&price[max]=100` |
| `TimeRangeFilter` | Time range | `time` | `?hours[min]=08:00&hours[max]=17:00` |

### Lookup Operators

Filters support Django-style lookup operators:

| Lookup | Description | SQL Example |
|--------|-------------|-------------|
| `exact` | Exact match (default) | `column = 'value'` |
| `iexact` | Case-insensitive equal | `column ILIKE 'value'` |
| `contains` | Contains | `column LIKE '%value%'` |
| `icontains` | Case-insensitive contains | `column ILIKE '%value%'` |
| `startswith` | Starts with | `column LIKE 'value%'` |
| `endswith` | Ends with | `column LIKE '%value'` |
| `gt` | Greater than | `column > value` |
| `gte` | Greater or equal | `column >= value` |
| `lt` | Less than | `column < value` |
| `lte` | Less or equal | `column <= value` |
| `isnull` | Is null check | `column IS NULL` |

### Creating a FilterSet

```python
from typing import Optional
from pydantic import Field
from fastapi_restkit.filterset import FilterSet, filter_as_query
from fastapi_restkit.filters import (
    SearchFilter,
    BooleanFilter,
    ListFilter,
    NumericRangeFilter,
    DateRangeFilter,
)


class ProductFilterSet(FilterSet):
    """Filters for products."""
    
    # Text search (auto-mapped to 'name' column)
    name: Optional[SearchFilter] = Field(
        default_factory=SearchFilter,
        description="Search by product name"
    )
    
    # Boolean filter
    is_active: Optional[BooleanFilter] = Field(
        default_factory=BooleanFilter,
        description="Filter by active status"
    )
    
    # List filter (IN clause)
    category: Optional[ListFilter[str]] = Field(
        default_factory=ListFilter,
        description="Filter by categories"
    )
    
    # Numeric range
    price: Optional[NumericRangeFilter] = Field(
        default_factory=NumericRangeFilter,
        description="Filter by price range"
    )
    
    # Date range
    created_at: Optional[DateRangeFilter] = Field(
        default_factory=DateRangeFilter,
        description="Filter by creation date"
    )
    
    # Multi-column search
    search: Optional[SearchFilter] = Field(
        default_factory=SearchFilter,
        description="Search in name and description"
    )

    class Config:
        # Custom column mapping
        field_columns = {
            "search": ["name", "description"],  # OR search across columns
        }


# Use in endpoint
@app.get("/products")
async def list_products(
    session: Session = Depends(get_session),
    filters: ProductFilterSet = Depends(filter_as_query(ProductFilterSet)),
):
    query = select(Product)
    query = filters.apply_to_query(query, Product)
    return session.exec(query).all()
```

### Filter URL Examples

```bash
# Simple text search
GET /products?name=laptop

# With lookup operator
GET /products?name=lap&name[lookup]=startswith

# Boolean filter
GET /products?is_active=true

# List filter (IN clause)
GET /products?category=electronics&category=computers

# Numeric range
GET /products?price[min]=100&price[max]=500

# Date range
GET /products?created_at[min]=2024-01-01&created_at[max]=2024-12-31

# Combined filters
GET /products?is_active=true&category=electronics&price[min]=100
```

---

## Sorting

### Creating a SortingSet

```python
from fastapi_restkit.sortingset import SortingSet, SortableField, sorting_as_query


class ProductSortingSet(SortingSet):
    """Sorting options for products."""
    
    id: SortableField = SortableField(description="Product ID")
    name: SortableField = SortableField(description="Product name")
    price: SortableField = SortableField(description="Price")
    created_at: SortableField = SortableField(description="Creation date")
    
    # Map to different column name
    updated: SortableField = SortableField(
        description="Update date",
        column="updated_at",
    )

    class Config:
        default_sorting = ["created_at:desc"]


# Use in endpoint
@app.get("/products")
async def list_products(
    session: Session = Depends(get_session),
    sorting: ProductSortingSet = Depends(sorting_as_query(ProductSortingSet)),
):
    query = select(Product)
    query = sorting.apply_to_query(query, Product)
    return session.exec(query).all()
```

### Sorting URL Examples

```bash
# Ascending (default)
GET /products?sort_by=name

# Descending
GET /products?sort_by=price:desc

# Multiple fields
GET /products?sort_by=category:asc&sort_by=price:desc

# Results in: ORDER BY category ASC, price DESC
```

---

## Complete Example

Combining pagination, filtering, and sorting:

```python
from fastapi import APIRouter, Depends
from sqlmodel import Session, select
from fastapi_restkit import PaginationParams, paginate, PaginatedResponse
from fastapi_restkit.filterset import FilterSet, filter_as_query
from fastapi_restkit.sortingset import SortingSet, SortableField, sorting_as_query
from fastapi_restkit.filters import SearchFilter, BooleanFilter, NumericRangeFilter


class ProductFilterSet(FilterSet):
    name: Optional[SearchFilter] = Field(default_factory=SearchFilter)
    is_active: Optional[BooleanFilter] = Field(default_factory=BooleanFilter)
    price: Optional[NumericRangeFilter] = Field(default_factory=NumericRangeFilter)


class ProductSortingSet(SortingSet):
    name: SortableField = SortableField(description="Name")
    price: SortableField = SortableField(description="Price")
    created_at: SortableField = SortableField(description="Created")

    class Config:
        default_sorting = ["created_at:desc"]


router = APIRouter(prefix="/products", tags=["Products"])


@router.get("", response_model=PaginatedResponse[ProductRead])
async def list_products(
    session: Session = Depends(get_session),
    filters: ProductFilterSet = Depends(filter_as_query(ProductFilterSet)),
    sorting: ProductSortingSet = Depends(sorting_as_query(ProductSortingSet)),
    pagination: PaginationParams = Depends(),
):
    """
    List products with filtering, sorting, and pagination.
    
    **Filters:** name, is_active, price
    **Sorting:** name, price, created_at
    **Pagination:** page, page_size
    """
    query = select(Product)
    query = filters.apply_to_query(query, Product)
    query = sorting.apply_to_query(query, Product)
    return await paginate(session, query, pagination)
```

**Combined URL Example:**
```bash
GET /products?is_active=true&price[min]=100&price[max]=500&sort_by=price:asc&page=1&page_size=20
```

---

## Development

### Setup

```bash
# Clone the repository
git clone https://github.com/cacenot/fastapi-restkit.git
cd fastapi-restkit

# Install dependencies with uv
uv sync --dev

# Run tests
uv run pytest

# Run linter
uv run ruff check .

# Run formatter
uv run ruff format .
```

### Project Structure

```
fastapi-restkit/
├── src/
│   └── fastapi_restkit/
│       ├── __init__.py
│       ├── pagination.py     # Pagination logic
│       ├── filters.py        # Filter types
│       ├── filterset.py      # FilterSet base class
│       ├── sorting.py        # Sorting utilities
│       ├── sortingset.py     # SortingSet base class
│       ├── models.py         # Response models
│       └── dependencies.py   # FastAPI dependencies
├── tests/
├── docs/
└── pyproject.toml
```

## License

MIT License - see [LICENSE](LICENSE) for details.
