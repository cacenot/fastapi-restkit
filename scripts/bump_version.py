#!/usr/bin/env python3
"""
Version bump script for fastapi-restkit.

Usage:
    python scripts/bump_version.py patch   # 0.1.0 -> 0.1.1
    python scripts/bump_version.py minor   # 0.1.0 -> 0.2.0
    python scripts/bump_version.py major   # 0.1.0 -> 1.0.0
    python scripts/bump_version.py 0.2.5   # Set specific version
    
Options:
    --dry-run    Show what would be changed without modifying files
    --tag        Create git tag after bump
    --push       Push changes and tag to remote
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path


def get_project_root() -> Path:
    """Get the project root directory."""
    return Path(__file__).parent.parent


def read_current_version(pyproject_path: Path) -> str:
    """Read current version from pyproject.toml."""
    content = pyproject_path.read_text()
    match = re.search(r'^version\s*=\s*"([^"]+)"', content, re.MULTILINE)
    if not match:
        raise ValueError("Could not find version in pyproject.toml")
    return match.group(1)


def parse_version(version: str) -> tuple[int, int, int]:
    """Parse version string into tuple of (major, minor, patch)."""
    match = re.match(r"^(\d+)\.(\d+)\.(\d+)", version)
    if not match:
        raise ValueError(f"Invalid version format: {version}")
    return int(match.group(1)), int(match.group(2)), int(match.group(3))


def bump_version(current: str, bump_type: str) -> str:
    """
    Bump version based on type.
    
    Args:
        current: Current version string (e.g., "0.1.0")
        bump_type: One of "major", "minor", "patch" or a specific version
        
    Returns:
        New version string
    """
    # If bump_type looks like a version, use it directly
    if re.match(r"^\d+\.\d+\.\d+", bump_type):
        return bump_type
    
    major, minor, patch = parse_version(current)
    
    if bump_type == "major":
        return f"{major + 1}.0.0"
    elif bump_type == "minor":
        return f"{major}.{minor + 1}.0"
    elif bump_type == "patch":
        return f"{major}.{minor}.{patch + 1}"
    else:
        raise ValueError(f"Invalid bump type: {bump_type}. Use major, minor, patch, or a version number.")


def update_pyproject(pyproject_path: Path, old_version: str, new_version: str) -> None:
    """Update version in pyproject.toml."""
    content = pyproject_path.read_text()
    new_content = re.sub(
        rf'^version\s*=\s*"{re.escape(old_version)}"',
        f'version = "{new_version}"',
        content,
        flags=re.MULTILINE,
    )
    pyproject_path.write_text(new_content)


def run_command(cmd: list[str], check: bool = True) -> subprocess.CompletedProcess:
    """Run a shell command."""
    print(f"  $ {' '.join(cmd)}")
    return subprocess.run(cmd, check=check, capture_output=True, text=True)


def git_commit_and_tag(version: str, tag: bool = False, push: bool = False) -> None:
    """Commit version change and optionally create tag."""
    # Stage pyproject.toml
    run_command(["git", "add", "pyproject.toml"])
    
    # Commit
    run_command(["git", "commit", "-m", f"chore: bump version to {version}"])
    print(f"  ✓ Committed version bump")
    
    if tag:
        tag_name = f"v{version}"
        run_command(["git", "tag", "-a", tag_name, "-m", f"Release {version}"])
        print(f"  ✓ Created tag: {tag_name}")
    
    if push:
        run_command(["git", "push"])
        print(f"  ✓ Pushed commits")
        if tag:
            run_command(["git", "push", "--tags"])
            print(f"  ✓ Pushed tags")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Bump version for fastapi-restkit",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python scripts/bump_version.py patch          # 0.1.0 -> 0.1.1
    python scripts/bump_version.py minor          # 0.1.0 -> 0.2.0
    python scripts/bump_version.py major          # 0.1.0 -> 1.0.0
    python scripts/bump_version.py 0.2.5          # Set to 0.2.5
    python scripts/bump_version.py patch --tag    # Bump and create git tag
    python scripts/bump_version.py minor --push   # Bump, tag, and push
        """,
    )
    parser.add_argument(
        "bump_type",
        help="Type of version bump: major, minor, patch, or specific version (e.g., 0.2.0)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be changed without modifying files",
    )
    parser.add_argument(
        "--tag",
        action="store_true",
        help="Create git tag after version bump",
    )
    parser.add_argument(
        "--push",
        action="store_true",
        help="Push changes and tag to remote (implies --tag)",
    )
    
    args = parser.parse_args()
    
    # --push implies --tag
    if args.push:
        args.tag = True
    
    project_root = get_project_root()
    pyproject_path = project_root / "pyproject.toml"
    
    if not pyproject_path.exists():
        print(f"Error: {pyproject_path} not found")
        return 1
    
    try:
        current_version = read_current_version(pyproject_path)
        new_version = bump_version(current_version, args.bump_type)
    except ValueError as e:
        print(f"Error: {e}")
        return 1
    
    print(f"\n📦 fastapi-restkit version bump")
    print(f"   {current_version} → {new_version}\n")
    
    if args.dry_run:
        print("🔍 Dry run - no changes made")
        print(f"   Would update: {pyproject_path}")
        if args.tag:
            print(f"   Would create tag: v{new_version}")
        if args.push:
            print(f"   Would push to remote")
        return 0
    
    # Update pyproject.toml
    update_pyproject(pyproject_path, current_version, new_version)
    print(f"✓ Updated {pyproject_path.name}")
    
    # Git operations
    if args.tag or args.push:
        print("\n📝 Git operations:")
        try:
            git_commit_and_tag(new_version, tag=args.tag, push=args.push)
        except subprocess.CalledProcessError as e:
            print(f"\n❌ Git command failed: {e.stderr}")
            return 1
    
    print(f"\n✅ Version bumped to {new_version}")
    
    if not args.tag:
        print(f"\nNext steps:")
        print(f"  git add pyproject.toml")
        print(f"  git commit -m 'chore: bump version to {new_version}'")
        print(f"  git tag -a v{new_version} -m 'Release {new_version}'")
        print(f"  git push && git push --tags")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
