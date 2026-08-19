# Author: Wagner Bianchi <wagnerbianchijr@gmail.com>
# Created: 2026-08-19

import subprocess
import sys


def test_main_module_can_be_invoked():
    """Test that __main__.py can be invoked as a module."""
    result = subprocess.run(
        [sys.executable, "-m", "tsdbenv", "--version"],
        capture_output=True,
        text=True,
        timeout=5,
    )
    assert result.returncode == 0
    assert "tsdbenv" in result.stdout
