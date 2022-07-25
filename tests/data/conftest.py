from __future__ import annotations

# Standard Library Imports
from typing import TYPE_CHECKING

# Third Party Imports
import pytest

# RESONAATE Imports
from resonaate.data.agent import AgentModel
from resonaate.data.epoch import Epoch

# Type Checking Imports
if TYPE_CHECKING:
    # Standard Library Imports
    from typing import Any

EXAMPLE_RSO: dict[str, Any] = {
    "name": "Sat1",
    "unique_id": 38093,
}


EXAMPLE_EPOCH: dict[str, Any] = {
    "julian_date": 2458207.010416667,
    "timestampISO": "2019-01-01T00:01:00.000Z",
}


EXAMPLE_SENSOR_AGENT: dict[str, Any] = {
    "name": "Sensor1",
    "unique_id": 100200,
}


@pytest.fixture(name="epoch")
def getEpoch() -> Epoch:
    """Create a valid :class:`.Epoch` object."""
    return Epoch(**EXAMPLE_EPOCH)


@pytest.fixture(name="target_agent")
def getTargetAgent() -> AgentModel:
    """Create a valid :class:`.AgentModel` object."""
    return AgentModel(
        unique_id=EXAMPLE_RSO["unique_id"],
        name=EXAMPLE_RSO["name"],
    )


@pytest.fixture(name="sensor_agent")
def getSensorAgent() -> AgentModel:
    """Create a valid :class:`.AgentModel` object."""
    return AgentModel(
        unique_id=EXAMPLE_SENSOR_AGENT["unique_id"],
        name=EXAMPLE_SENSOR_AGENT["name"],
    )
