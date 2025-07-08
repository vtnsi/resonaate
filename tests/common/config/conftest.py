from __future__ import annotations

# Third Party Imports
import pytest

# RESONAATE Imports
from resonaate.common.config import getConfig, putResonaateArgs, rootConfigSpec


@pytest.fixture(autouse=True)
def _clearCaches():
    """Make sure cached info is cleared between tests."""
    yield
    rootConfigSpec.cache_clear()
    getConfig.cache_clear()


@pytest.fixture(name="put_main_init_arg")
def _putMainInitArg():
    """Fixture setting RESONAATE CLI args environment variable."""
    putResonaateArgs(["configs/json/main_init.json"])
    yield
    putResonaateArgs([])
