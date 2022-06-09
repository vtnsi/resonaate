"""Pytest fixtures shared across the events tests."""
# Standard Library Imports
from unittest.mock import create_autospec
# Third Party Imports
import pytest
# RESONAATE Imports
try:
    from resonaate.scenario.scenario import Scenario
except ImportError as error:
    raise Exception(
        f"Please ensure you have appropriate packages installed:\n {error}"
    ) from error


@pytest.fixture(name="mocked_scenario")
def getMockedScenario():
    """Get a mocked :class:`.Scenario` object."""
    mocked_scenario = create_autospec(Scenario)
    return mocked_scenario
