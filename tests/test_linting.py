"""Tests for code quality checks (linting and type checking)."""
import subprocess
import sys
from pathlib import Path

import pytest


def get_project_root() -> Path:
    """Get the project root directory."""
    return Path(__file__).parent.parent


def get_python_files():
    """Get all Python files in the project (excluding .venv and tests)."""
    project_root = get_project_root()
    graphql_http_dir = project_root / "graphql_http"
    return list(graphql_http_dir.glob("**/*.py"))


class TestFlake8:
    """Test flake8 linting."""

    def test_flake8_graphql_http_package(self):
        """Test that graphql_http package passes flake8 checks."""
        project_root = get_project_root()
        graphql_http_dir = project_root / "graphql_http"

        result = subprocess.run(
            [sys.executable, "-m", "flake8", str(graphql_http_dir)],
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            pytest.fail(
                f"flake8 found issues:\n{result.stdout}\n{result.stderr}"
            )

    def test_flake8_tests_directory(self):
        """Test that tests directory passes flake8 checks."""
        project_root = get_project_root()
        tests_dir = project_root / "tests"

        result = subprocess.run(
            [sys.executable, "-m", "flake8", str(tests_dir)],
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            pytest.fail(
                f"flake8 found issues in tests:\n{result.stdout}\n{result.stderr}"
            )

    def test_flake8_server_module(self):
        """Test that server.py passes flake8 checks."""
        project_root = get_project_root()
        server_file = project_root / "graphql_http" / "server.py"

        result = subprocess.run(
            [sys.executable, "-m", "flake8", str(server_file)],
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            pytest.fail(
                f"flake8 found issues in server.py:\n{result.stdout}\n{result.stderr}"
            )


class TestPyright:
    """Test pyright type checking (optional - skipped if pyright not installed)."""

    @pytest.mark.skipif(
        subprocess.run(
            ["which", "pyright"],
            capture_output=True
        ).returncode != 0,
        reason="pyright not installed"
    )
    def test_pyright_graphql_http_package(self):
        """Test that graphql_http package passes pyright type checks."""
        project_root = get_project_root()
        graphql_http_dir = project_root / "graphql_http"

        result = subprocess.run(
            ["pyright", str(graphql_http_dir)],
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            pytest.fail(
                f"pyright found issues:\n{result.stdout}\n{result.stderr}"
            )

    @pytest.mark.skipif(
        subprocess.run(
            ["which", "pyright"],
            capture_output=True
        ).returncode != 0,
        reason="pyright not installed"
    )
    def test_pyright_server_module(self):
        """Test that server.py passes pyright type checks."""
        project_root = get_project_root()
        server_file = project_root / "graphql_http" / "server.py"

        result = subprocess.run(
            ["pyright", str(server_file)],
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            pytest.fail(
                f"pyright found issues in server.py:\n{result.stdout}\n{result.stderr}"
            )
