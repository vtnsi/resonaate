from __future__ import annotations

# Third Party Imports
import pytest

# RESONAATE Imports
from resonaate.common.config import putResonaateArgs


@pytest.fixture(name="put_main_init_arg")
def _putMainInitArg():
    """Fixture setting RESONAATE CLI args environment variable."""
    putResonaateArgs(["configs/json/main_init.json"])
    yield
    putResonaateArgs([])
