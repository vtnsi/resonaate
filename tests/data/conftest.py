# pylint: disable=attribute-defined-outside-init
# Standard Library Imports
# Third Party Imports
import pytest

# RESONAATE Library Imports
try:
    # RESONAATE Imports
    from resonaate.data.agent import Agent
    from resonaate.data.epoch import Epoch
except ImportError as error:
    raise Exception(f"Please ensure you have appropriate packages installed:\n {error}") from error
# Testing Imports


EXAMPLE_RSO = {
    "name": "Sat1",
    "unique_id": 38093,
}


EXAMPLE_EPOCH = {
    "julian_date": 2458207.010416667,
    "timestampISO": "2019-01-01T00:01:00.000Z",
}


EXAMPLE_SENSOR_AGENT = {
    "name": "Sensor1",
    "unique_id": 100200,
}


@pytest.fixture(name="epoch")
def getEpoch():
    """Create a valid :class:`.Epoch` object."""
    return Epoch(**EXAMPLE_EPOCH)


@pytest.fixture(name="target_agent")
def getTargetAgent():
    """Create a valid :class:`.Agent` object."""
    return Agent(
        unique_id=EXAMPLE_RSO["unique_id"],
        name=EXAMPLE_RSO["name"],
    )


@pytest.fixture(name="sensor_agent")
def getSensorAgent():
    """Create a valid :class:`.Agent` object."""
    return Agent(
        unique_id=EXAMPLE_SENSOR_AGENT["unique_id"],
        name=EXAMPLE_SENSOR_AGENT["name"],
    )
