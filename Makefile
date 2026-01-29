.PHONY: help install install-dev test lint format type-check clean build release

# Default target
help:
	@echo "FastAPI RestKit - Available Commands"
	@echo "======================================"
	@echo ""
	@echo "Setup:"
	@echo "  make install          Install package dependencies"
	@echo "  make install-dev      Install package with dev dependencies"
	@echo ""
	@echo "Development:"
	@echo "  make test             Run tests with pytest"
	@echo "  make lint             Run linter (ruff)"
	@echo "  make format           Format code with ruff"
	@echo "  make type-check       Run type checker (mypy)"
	@echo ""
	@echo "Build & Publish:"
	@echo "  make clean            Clean build artifacts"
	@echo "  make build            Build the package"
	@echo "  make release          Bump, tag, and optionally push"
	@echo ""

# Install package
install:
	pip install -e .

# Install with dev dependencies
install-dev:
	pip install -e ".[dev]"

# Run tests
test:
	pytest tests/ -v

# Run linter
lint:
	ruff check src/ tests/

# Format code
format:
	ruff format src/ tests/
	ruff check --fix src/ tests/

# Run type checker
type-check:
	mypy src/

# Clean build artifacts
clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf .ruff_cache/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

# Build package
build: clean
	python -m build

# Bump, tag, and optionally push
release:
	python scripts/release.py
