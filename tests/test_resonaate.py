from __future__ import annotations

# Standard Library Imports
import subprocess

# RESONAATE Imports
from resonaate.__main__ import main

# ruff: noqa: F401
# ruff: noqa: S603
# ruff: noqa: S607


def testModuleCommand():
    """Test that the module can be ran using `python -m`."""
    assert subprocess.call(["python", "-m", "resonaate", "-h"]) == 0


def testEntryPoint():
    """Test that the module can be ran using `resonaate` command directly."""
    assert subprocess.call(["resonaate", "-h"]) == 0
