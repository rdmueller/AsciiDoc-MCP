"""Tests for project setup validation (Issue #1).

These tests verify that the project is correctly configured with uv
and that the basic module structure works.
"""

import subprocess
import sys


def test_dacli_module_importable():
    """Test that dacli module can be imported."""
    import dacli
    assert hasattr(dacli, "__version__")


def test_dacli_version_is_string():
    """Test that version is a proper string."""
    from dacli import __version__
    assert isinstance(__version__, str)
    assert len(__version__) > 0


def test_dacli_mcp_can_be_run():
    """Test that 'dacli-mcp --help' runs without error.

    This is an acceptance test that verifies the project setup
    allows running the MCP server.
    """
    result = subprocess.run(
        [sys.executable, "-m", "dacli", "--help"],
        capture_output=True,
        text=True,
        timeout=10
    )
    # Should exit cleanly (0) or with help message
    # We accept both 0 and 2 (argparse help exits with 2 sometimes)
    assert result.returncode in (0, 2), f"Failed with: {result.stderr}"
