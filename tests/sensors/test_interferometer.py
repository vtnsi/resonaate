"""Defines Interferometer Sensor unit test."""

# Standard Library Imports
from __future__ import annotations
from unittest.mock import create_autospec

# Third Party Imports
import numpy as np
import pytest

# RESONAATE Imports
from resonaate.agents.sensing_agent import SensingAgent
from resonaate.agents.target_agent import TargetAgent
from resonaate.common.labels import Explanation, PlatformLabel
from resonaate.physics.bodies.earth import Earth
from resonaate.physics.time.stardate import JulianDate, ScenarioTime, julianDateToDatetime
from resonaate.physics.transforms.methods import eci2ecef, getSlantRangeVector
from resonaate.sensors.interferometer import Interferometer

@pytest.fixture(name="mocked_sensing_agent")
def getSensorAgent() -> SensingAgent:
    """Create a mocked sensing agent object."""
    sensor_agent = create_autospec(spec=SensingAgent, instance=True)
    sensor_agent.time = ScenarioTime(60.0)
    sensor_agent.name = "Test Interferometer Agent"
    sensor_agent.simulation_id = 11111
    sensor_agent.truth_state = np.array((0.0, Earth.radius + 1000, 10.0, 0.0, 0.0, 0.0))
    sensor_agent.julian_date_epoch = JulianDate(2459486.09964)
    return sensor_agent


@pytest.fixture(name="mocked_primary_target")
def getTargetAgent() -> TargetAgent:
    """Create a mocked Target agent object."""
    target_agent = create_autospec(spec=TargetAgent, instance=True)
    target_agent.initial_state = np.array((0.0, Earth.radius * 2, 20.0, 0.0, 0.0, 0.0))
    target_agent.visual_cross_section = 0.0 # Doesnt matter for interferometer, but needed to satisfy the function signature of isVisible
    target_agent.reflectivity = 0.0 # Doesnt matter for interferometer, but needed to satisfy the function signature of isVisible
    return target_agent

def testSensorInit(interferometer_sensor_args: dict):
    """Test interferometer sensor initialization.

    Args:
        interferometer_sensor_args(``dict``): arguments to interferometer init.
    """
    interferometer = Interferometer(**interferometer_sensor_args)
    assert interferometer

def testIsVisible(
    mocked_sensing_agent: SensingAgent,
    interferometer_sensor_args: dict,
    mocked_primary_target: TargetAgent,
):
    """Test Interferometer sensor `isVisible` function.

    Args:
        mocked_sensing_agent (:class:`.SensingAgent`): mocked sensing agent object
        interferometer_sensor_args (``dict``):  dictionary of valid arguments to Sensor init
        mocked_primary_target (:class:`.TargetAgent`): mocked Target agent object
    """
    interferometer_sensor = Interferometer(**interferometer_sensor_args)
    mocked_sensing_agent.agent_type = PlatformLabel.GROUND_FACILITY
    interferometer_sensor.host = mocked_sensing_agent

    utc_datetime = julianDateToDatetime(mocked_sensing_agent.julian_date_epoch)
    mocked_sensing_agent.ecef_state = eci2ecef(mocked_sensing_agent.truth_state, utc_datetime)
    mocked_sensing_agent.eci_state = mocked_sensing_agent.truth_state
    slant_range_sez = getSlantRangeVector(
        mocked_sensing_agent.eci_state,
        mocked_primary_target.initial_state,
        utc_datetime,
    )

    visibility, explanation = interferometer_sensor.isVisible(
        mocked_primary_target.initial_state,
        mocked_primary_target.visual_cross_section,
        mocked_primary_target.reflectivity,
        slant_range_sez,
    )

    assert visibility
    assert explanation == Explanation.VISIBLE

