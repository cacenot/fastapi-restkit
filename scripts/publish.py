#!/usr/bin/env python3
"""
Script to build and publish the package to PyPI.

Usage:
    python scripts/publish.py [--test]

Options:
    --test    Publish to TestPyPI instead of PyPI

Environment Variables:
    PYPI_TOKEN         PyPI API token for authentication
    PYPI_TEST_TOKEN    TestPyPI API token for authentication
"""

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path


def run_command(cmd: list[str], description: str) -> None:
    """Run a command and handle errors."""
    print(f"\n{'=' * 70}")
    print(f"🔨 {description}")
    print(f"{'=' * 70}")
    print(f"Running: {' '.join(cmd)}\n")

    result = subprocess.run(cmd, capture_output=False)

    if result.returncode != 0:
        print(f"\n❌ Error: {description} failed!")
        sys.exit(1)

    print(f"\n✅ {description} completed successfully!")


def clean_build_artifacts() -> None:
    """Remove build artifacts from previous builds."""
    print("\n🧹 Cleaning build artifacts...")

    dirs_to_remove = ["dist", "build", "*.egg-info"]
    for pattern in dirs_to_remove:
        for path in Path(".").glob(pattern):
            if path.is_dir():
                print(f"  Removing {path}/")
                shutil.rmtree(path)
            elif path.is_file():
                print(f"  Removing {path}")
                path.unlink()

    print("✅ Clean completed!")


def build_package() -> None:
    """Build the package."""
    run_command(["python", "-m", "build"], "Building package")


def check_package() -> None:
    """Check the package with twine."""
    run_command(["python", "-m", "twine", "check", "dist/*"], "Checking package")


def publish_package(test: bool = False) -> None:
    """Publish the package to PyPI or TestPyPI."""
    if test:
        repository_url = "https://test.pypi.org/legacy/"
        repository_name = "TestPyPI"
        token_env = "PYPI_TEST_TOKEN"
    else:
        repository_url = "https://upload.pypi.org/legacy/"
        repository_name = "PyPI"
        token_env = "PYPI_TOKEN"

    # Check for API token
    token = os.getenv(token_env)

    print(f"\n{'=' * 70}")
    print(f"📦 Publishing to {repository_name}")
    print(f"{'=' * 70}")

    if token:
        print(f"✓ Using API token from {token_env}")
    else:
        print(f"ℹ️  No {token_env} found, twine will prompt for credentials")

    cmd = ["python", "-m", "twine", "upload"]
    if test:
        cmd.extend(["--repository-url", repository_url])

    # Add authentication if token is available
    if token:
        cmd.extend(["--username", "__token__", "--password", token])

    cmd.append("dist/*")

    print(f"Running: {' '.join(cmd[: cmd.index('--password')] if token else cmd)}\n")
    result = subprocess.run(cmd)

    if result.returncode != 0:
        print(f"\n❌ Error: Publishing to {repository_name} failed!")
        sys.exit(1)

    print(f"\n✅ Successfully published to {repository_name}!")


def main() -> None:
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Build and publish the package to PyPI"
    )
    parser.add_argument(
        "--test", action="store_true", help="Publish to TestPyPI instead of PyPI"
    )
    parser.add_argument(
        "--skip-clean", action="store_true", help="Skip cleaning build artifacts"
    )

    args = parser.parse_args()

    print("\n" + "=" * 70)
    print("🚀 FastAPI RestKit - Build and Publish")
    print("=" * 70)

    # Clean build artifacts
    if not args.skip_clean:
        clean_build_artifacts()

    # Build the package
    build_package()

    # Check the package
    check_package()

    # Ask for confirmation before publishing
    repository = "TestPyPI" if args.test else "PyPI"
    print(f"\n{'=' * 70}")
    print(f"⚠️  Ready to publish to {repository}")
    print(f"{'=' * 70}")

    response = input(f"\nDo you want to continue? [y/N]: ")
    if response.lower() != "y":
        print("\n❌ Publish cancelled by user.")
        sys.exit(0)

    # Publish the package
    publish_package(test=args.test)

    print("\n" + "=" * 70)
    print("🎉 All done!")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
