from __future__ import annotations

# Standard Library Imports
from unittest.mock import create_autospec

# Third Party Imports
import pytest

# RESONAATE Imports
from resonaate.scenario.scenario import Scenario


@pytest.fixture(name="mocked_scenario")
def getMockedScenario():
    """Get a mocked :class:`.Scenario` object."""
    mocked_scenario = create_autospec(Scenario, instance=True)
    return mocked_scenario
