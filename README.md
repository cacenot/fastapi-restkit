# FastAPI RestKit

[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

Pagination utilities for FastAPI with SQLModel ORM.

## Features

- 🚀 **Easy pagination** for SQLModel queries
- 📦 **Generic response models** with type hints
- ⚡ **FastAPI dependencies** ready to use
- 🔍 **Async support** out of the box

## Installation

```bash
pip install fastapi-restkit
```

Or with uv:

```bash
uv add fastapi-restkit
```

## Quick Start

```python
from fastapi import FastAPI, Depends
from sqlmodel import Session
from fastapi_restkit import PaginationParams, paginate, PaginatedResponse

app = FastAPI()

@app.get("/items", response_model=PaginatedResponse[Item])
async def list_items(
    session: Session = Depends(get_session),
    pagination: PaginationParams = Depends(),
):
    return await paginate(session, select(Item), pagination)
```

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
│       ├── pagination.py     # Core pagination logic
│       ├── models.py         # Response models
│       └── dependencies.py   # FastAPI dependencies
├── tests/
├── docs/
└── pyproject.toml
```

## License

MIT License - see [LICENSE](LICENSE) for details.
