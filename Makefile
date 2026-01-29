.PHONY: help install install-dev test lint format type-check clean build publish publish-test release bump-patch bump-minor bump-major bump-version bump-patch-tag bump-minor-tag bump-major-tag bump-patch-push bump-minor-push bump-major-push

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
	@echo "  make publish          Build and publish to PyPI"
	@echo "  make publish-test     Build and publish to TestPyPI"
	@echo "  make release          Bump, commit, and publish to PyPI"
	@echo ""
	@echo "Version Management:"
	@echo "  make bump-patch       Bump patch version (0.1.0 -> 0.1.1)"
	@echo "  make bump-minor       Bump minor version (0.1.0 -> 0.2.0)"
	@echo "  make bump-major       Bump major version (0.1.0 -> 1.0.0)"
	@echo "  make bump-version     Set specific version (usage: make bump-version VERSION=0.2.0)"
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

# Publish to PyPI
publish:
	python scripts/publish.py

# Publish to TestPyPI
publish-test:
	python scripts/publish.py --test

# Bump, commit, and publish to PyPI
release:
	python scripts/release.py

# Bump patch version (0.1.0 -> 0.1.1)
bump-patch:
	python scripts/bump_version.py patch

# Bump minor version (0.1.0 -> 0.2.0)
bump-minor:
	python scripts/bump_version.py minor

# Bump major version (0.1.0 -> 1.0.0)
bump-major:
	python scripts/bump_version.py major

# Set specific version
bump-version:
ifndef VERSION
	@echo "Error: VERSION is required. Usage: make bump-version VERSION=0.2.0"
	@exit 1
endif
	python scripts/bump_version.py $(VERSION)

# Bump patch version and create git tag
bump-patch-tag:
	python scripts/bump_version.py patch --tag

# Bump minor version and create git tag
bump-minor-tag:
	python scripts/bump_version.py minor --tag

# Bump major version and create git tag
bump-major-tag:
	python scripts/bump_version.py major --tag

# Bump patch version, tag, and push
bump-patch-push:
	python scripts/bump_version.py patch --push

# Bump minor version, tag, and push
bump-minor-push:
	python scripts/bump_version.py minor --push

# Bump major version, tag, and push
bump-major-push:
	python scripts/bump_version.py major --push
