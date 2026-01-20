# Releasing a New Version

This guide explains how to release a new version of fastapi-restkit.

## Version Bump Script

The project includes a script to automate version bumping:

```bash
python scripts/bump_version.py <bump_type> [options]
```

### Bump Types

| Type | Description | Example |
|------|-------------|---------|
| `patch` | Bug fixes, small changes | `0.1.0` → `0.1.1` |
| `minor` | New features, backwards compatible | `0.1.0` → `0.2.0` |
| `major` | Breaking changes | `0.1.0` → `1.0.0` |
| `X.Y.Z` | Set specific version | `0.1.0` → `0.2.5` |

### Options

| Option | Description |
|--------|-------------|
| `--dry-run` | Preview changes without modifying files |
| `--tag` | Create git tag after bump |
| `--push` | Push commits and tags to remote (implies `--tag`) |

### Examples

```bash
# Preview what would change
python scripts/bump_version.py patch --dry-run

# Bump patch version (0.1.0 → 0.1.1)
python scripts/bump_version.py patch

# Bump minor version (0.1.0 → 0.2.0)
python scripts/bump_version.py minor

# Bump major version (0.1.0 → 1.0.0)
python scripts/bump_version.py major

# Set specific version
python scripts/bump_version.py 0.2.5

# Bump and create git tag
python scripts/bump_version.py patch --tag

# Bump, tag, and push to remote
python scripts/bump_version.py minor --push
```

---

## Complete Release Process

### 1. Prepare the Release

```bash
# Make sure you're on main branch
git checkout main
git pull origin main

# Run tests
uv run pytest

# Run linting
uv run ruff check .
uv run ruff format --check .
```

### 2. Bump Version

```bash
# For a patch release (bug fixes)
python scripts/bump_version.py patch --push

# For a minor release (new features)
python scripts/bump_version.py minor --push

# For a major release (breaking changes)
python scripts/bump_version.py major --push
```

### 3. Build the Package

```bash
# Clean previous builds
rm -rf dist/ build/

# Build
uv build
```

### 4. Publish to PyPI

```bash
# Upload to PyPI
uv run twine upload dist/*

# Enter credentials when prompted:
# Username: __token__
# Password: pypi-YOUR_API_TOKEN
```

### 5. Create GitHub Release (Optional)

1. Go to https://github.com/cacenot/fastapi-restkit/releases
2. Click "Create a new release"
3. Select the tag created (e.g., `v0.2.0`)
4. Write release notes
5. Publish release

---

## Quick Release Commands

One-liner for a complete release:

```bash
# Patch release
python scripts/bump_version.py patch --push && rm -rf dist/ && uv build && uv run twine upload dist/*

# Minor release
python scripts/bump_version.py minor --push && rm -rf dist/ && uv build && uv run twine upload dist/*

# Major release
python scripts/bump_version.py major --push && rm -rf dist/ && uv build && uv run twine upload dist/*
```

---

## Version Numbering Guidelines

Follow [Semantic Versioning](https://semver.org/):

- **MAJOR** (`1.0.0`): Incompatible API changes
- **MINOR** (`0.1.0`): New functionality, backwards compatible
- **PATCH** (`0.0.1`): Bug fixes, backwards compatible

### When to Bump

| Change Type | Version Bump |
|-------------|--------------|
| Bug fix | `patch` |
| New filter type | `minor` |
| New feature | `minor` |
| Performance improvement | `patch` |
| Documentation only | `patch` |
| Breaking API change | `major` |
| Deprecation removal | `major` |

---

## Troubleshooting

### PyPI Upload Fails

```bash
# Check if version already exists on PyPI
pip index versions fastapi-restkit

# If version exists, bump again
python scripts/bump_version.py patch --push
```

### Git Tag Already Exists

```bash
# Delete local tag
git tag -d v0.1.1

# Delete remote tag
git push origin :refs/tags/v0.1.1

# Bump again
python scripts/bump_version.py patch --push
```

### Build Fails

```bash
# Clean everything
rm -rf dist/ build/ *.egg-info/ .eggs/

# Reinstall build tools
uv add --dev build twine

# Try again
uv build
```
