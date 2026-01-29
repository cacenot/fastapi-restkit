#!/usr/bin/env python3
"""
Release script: bump version, commit, create tag, and optionally push tag.

Flow:
- ensure git working tree is clean
- ask for bump type (patch/minor/major)
- apply bump to pyproject.toml
- commit bump
- create git tag
- ask whether to push commits and tags
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path


def get_project_root() -> Path:
    return Path(__file__).parent.parent


def run_command(cmd: list[str], description: str, cwd: Path) -> None:
    print(f"\n{'=' * 70}")
    print(f"🔨 {description}")
    print(f"{'=' * 70}")
    print(f"Running: {' '.join(cmd)}\n")
    result = subprocess.run(cmd, cwd=cwd)
    if result.returncode != 0:
        print(f"\n❌ Error: {description} failed!")
        sys.exit(result.returncode)
    print(f"\n✅ {description} completed successfully!")


def git_is_clean(cwd: Path) -> bool:
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=cwd,
        capture_output=True,
        text=True,
    )
    return result.returncode == 0 and result.stdout.strip() == ""


def read_current_version(pyproject_path: Path) -> str:
    content = pyproject_path.read_text()
    match = re.search(r'^version\s*=\s*"([^"]+)"', content, re.MULTILINE)
    if not match:
        raise ValueError("Could not find version in pyproject.toml")
    return match.group(1)


def parse_version(version: str) -> tuple[int, int, int]:
    match = re.match(r"^(\d+)\.(\d+)\.(\d+)", version)
    if not match:
        raise ValueError(f"Invalid version format: {version}")
    return int(match.group(1)), int(match.group(2)), int(match.group(3))


def bump_version(current: str, bump_type: str) -> str:
    major, minor, patch = parse_version(current)

    if bump_type == "major":
        return f"{major + 1}.0.0"
    if bump_type == "minor":
        return f"{major}.{minor + 1}.0"
    if bump_type == "patch":
        return f"{major}.{minor}.{patch + 1}"

    raise ValueError(f"Invalid bump type: {bump_type}")


def update_pyproject(pyproject_path: Path, old_version: str, new_version: str) -> None:
    content = pyproject_path.read_text()
    new_content = re.sub(
        rf'^version\s*=\s*"{re.escape(old_version)}"',
        f'version = "{new_version}"',
        content,
        flags=re.MULTILINE,
    )
    pyproject_path.write_text(new_content)


def choose_bump_type() -> str:
    print("\nSelect version bump type:")
    print("  1) patch")
    print("  2) minor")
    print("  3) major")
    choice = input("\nEnter choice [1-3]: ").strip()
    mapping = {"1": "patch", "2": "minor", "3": "major"}
    while choice not in mapping:
        choice = input("Invalid choice. Enter 1, 2, or 3: ").strip()
    return mapping[choice]


def ask_yes_no(prompt: str) -> bool:
    answer = input(f"{prompt} [y/N]: ").strip().lower()
    return answer == "y"


def main() -> int:
    project_root = get_project_root()
    pyproject_path = project_root / "pyproject.toml"

    if not pyproject_path.exists():
        print(f"Error: {pyproject_path} not found")
        return 1

    if not git_is_clean(project_root):
        print("\n❌ Working tree is not clean. Commit or stash changes before release.")
        return 1

    bump_type = choose_bump_type()

    try:
        current_version = read_current_version(pyproject_path)
        new_version = bump_version(current_version, bump_type)
    except ValueError as e:
        print(f"Error: {e}")
        return 1

    update_pyproject(pyproject_path, current_version, new_version)
    print(f"\n📦 Version bump: {current_version} → {new_version}")

    run_command(
        ["git", "add", "pyproject.toml"],
        "Staging version bump",
        cwd=project_root,
    )
    run_command(
        ["git", "commit", "-m", f"chore: bump version to {new_version}"],
        "Committing version bump",
        cwd=project_root,
    )

    run_command(
        ["git", "tag", "-a", f"v{new_version}", "-m", f"Release {new_version}"],
        "Creating git tag",
        cwd=project_root,
    )

    if ask_yes_no("\nPush commit and tag to remote?"):
        run_command(["git", "push"], "Pushing commits", cwd=project_root)
        run_command(["git", "push", "--tags"], "Pushing tags", cwd=project_root)

    print(f"\n✅ Release prepared: v{new_version}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
