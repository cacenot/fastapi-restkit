#!/usr/bin/env python3
"""
Release script: bump version, commit, and publish to PyPI.

Flow:
- ensure git working tree is clean
- ask for bump type (patch/minor/major)
- apply bump to pyproject.toml
- commit bump
- build + check + publish to PyPI using PYPI_TOKEN
"""

from __future__ import annotations

import os
import re
import shutil
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


def run_command_sanitized(cmd: list[str], description: str, cwd: Path, masked: str) -> None:
    print(f"\n{'=' * 70}")
    print(f"🔨 {description}")
    print(f"{'=' * 70}")
    print(f"Running: {masked}\n")
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


def clean_build_artifacts(cwd: Path) -> None:
    print("\n🧹 Cleaning build artifacts...")
    patterns = ["dist", "build", "*.egg-info"]
    for pattern in patterns:
        for path in cwd.glob(pattern):
            if path.is_dir():
                print(f"  Removing {path}/")
                shutil.rmtree(path)
            elif path.is_file():
                print(f"  Removing {path}")
                path.unlink()
    print("✅ Clean completed!")


def main() -> int:
    project_root = get_project_root()
    pyproject_path = project_root / "pyproject.toml"

    if not pyproject_path.exists():
        print(f"Error: {pyproject_path} not found")
        return 1

    if not git_is_clean(project_root):
        print("\n❌ Working tree is not clean. Commit or stash changes before release.")
        return 1

    token = os.getenv("PYPI_TOKEN")
    if not token:
        print("\n❌ PYPI_TOKEN is not set. Aborting release.")
        return 1

    bump_type = choose_bump_type()

    run_command(
        [sys.executable, "scripts/bump_version.py", bump_type],
        f"Bumping version ({bump_type})",
        cwd=project_root,
    )

    new_version = read_current_version(pyproject_path)

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

    clean_build_artifacts(project_root)
    run_command([sys.executable, "-m", "build"], "Building package", cwd=project_root)
    run_command(
        [sys.executable, "-m", "twine", "check", "dist/*"],
        "Checking package",
        cwd=project_root,
    )

    masked = "python -m twine upload --username __token__ --password *** dist/*"
    run_command_sanitized(
        [
            sys.executable,
            "-m",
            "twine",
            "upload",
            "--username",
            "__token__",
            "--password",
            token,
            "dist/*",
        ],
        "Publishing package to PyPI",
        cwd=project_root,
        masked=masked,
    )

    print(f"\n✅ Release completed: {new_version}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
