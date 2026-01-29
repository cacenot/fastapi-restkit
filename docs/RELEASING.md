# Releasing a New Version

This guide explains how to release a new version of fastapi-restkit.

## Release Script (single entrypoint)

The project ships a single release script:

```bash
python scripts/release.py
```

It will:

- ensure your git working tree is clean
- ask for the bump type (patch/minor/major)
- update `pyproject.toml`
- commit the bump
- create an annotated tag `vX.Y.Z`
- ask if you want to push commits and tags

---

## Complete Release Process

### 0. One-command Release (recommended)

```bash
python scripts/release.py
```

This will create the version commit + tag. When the tag is pushed, the GitHub
Action will build and publish the package to PyPI.

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

### 2. Run the release script

```bash
python scripts/release.py
```

If you choose to push, the tag will trigger the GitHub Action to publish to PyPI.

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
# Guided release (recommended)
python scripts/release.py
```

```bash
# Guided release (recommended)
python scripts/release.py
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
python scripts/release.py
```

### Git Tag Already Exists

```bash
# Delete local tag
git tag -d v0.1.1

# Delete remote tag
git push origin :refs/tags/v0.1.1

# Bump again
python scripts/release.py
```

### Build Fails

```bash
# Clean everything
rm -rf dist/ build/ *.egg-info/ .eggs/

# Check the GitHub Action logs for details
https://github.com/cacenot/fastapi-restkit/actions
```
