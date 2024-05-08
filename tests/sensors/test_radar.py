"""Defines Radar Sensor unit tests."""

from __future__ import annotations

# Standard Library Imports
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
from resonaate.sensors.radar import Radar


@pytest.fixture(name="mocked_sensing_agent")
def getSensorAgent() -> SensingAgent:
    """Create a mocked sensing agent object."""
    sensor_agent = create_autospec(spec=SensingAgent, instance=True)
    sensor_agent.time = ScenarioTime(60.0)
    sensor_agent.name = "Test Sensor Agent"
    sensor_agent.simulation_id = 11111
    sensor_agent.truth_state = np.array((0.0, Earth.radius + 1000, 10.0, 0.0, 0.0, 0.0))
    sensor_agent.julian_date_epoch = JulianDate(2459486.09964)
    return sensor_agent


@pytest.fixture(name="mocked_primary_target")
def getTargetAgent() -> TargetAgent:
    """Crate a mocked Target agent object."""
    target_agent = create_autospec(spec=TargetAgent, instance=True)
    target_agent.initial_state = np.array((0.0, Earth.radius * 2, 20.0, 0.0, 0.0, 0.0))
    target_agent.visual_cross_section = 25.0
    target_agent.reflectivity = 0.21
    return target_agent


def testSensorInit(radar_sensor_args: dict):
    """Test Radar Sensor Initialization.

    Args:
        radar_sensor_args (``dict``):  dictionary of valid arguments to Sensor init
    """
    radar_sensor = Radar(**radar_sensor_args)
    assert radar_sensor
    assert radar_sensor.tx_power == radar_sensor_args["tx_power"]


def testIsVisible(
    mocked_sensing_agent: SensingAgent,
    radar_sensor_args: dict,
    mocked_primary_target: TargetAgent,
):
    """Test Optical sensor `isVisible` function.

    Args:
        mocked_sensing_agent (:class:`.SensingAgent`): mocked sensing agent object
        radar_sensor_args (``dict``):  dictionary of valid arguments to Sensor init
        mocked_primary_target (:class:`.TargetAgent`): mocked Target agent object
    """
    radar_sensor = Radar(**radar_sensor_args)
    mocked_sensing_agent.agent_type = PlatformLabel.SPACECRAFT
    radar_sensor.host = mocked_sensing_agent

    utc_datetime = julianDateToDatetime(mocked_sensing_agent.julian_date_epoch)
    mocked_sensing_agent.ecef_state = eci2ecef(mocked_sensing_agent.truth_state, utc_datetime)
    mocked_sensing_agent.eci_state = mocked_sensing_agent.truth_state
    slant_range_sez = getSlantRangeVector(
        mocked_sensing_agent.eci_state,
        mocked_primary_target.initial_state,
        utc_datetime,
    )

    visibility, explanation = radar_sensor.isVisible(
        mocked_primary_target.initial_state,
        mocked_primary_target.visual_cross_section,
        mocked_primary_target.reflectivity,
        slant_range_sez,
    )

    assert visibility
    assert explanation == Explanation.VISIBLE


def testIsNotVisible(
    mocked_sensing_agent: SensingAgent,
    radar_sensor_args: dict,
    mocked_primary_target: TargetAgent,
):
    """Test Optical sensor `getMeasurements` function.

    Args:
        mocked_sensing_agent (:class:`.SensingAgent`): mocked sensing agent object
        radar_sensor_args (``dict``):  dictionary of valid arguments to Sensor init
        mocked_primary_target (:class:`.TargetAgent`): mocked Target agent object
    """
    radar_sensor = Radar(**radar_sensor_args)
    mocked_sensing_agent.agent_type = PlatformLabel.GROUND_FACILITY
    radar_sensor.host = mocked_sensing_agent

    utc_datetime = julianDateToDatetime(mocked_sensing_agent.julian_date_epoch)
    mocked_sensing_agent.ecef_state = eci2ecef(mocked_sensing_agent.truth_state, utc_datetime)
    mocked_sensing_agent.eci_state = mocked_sensing_agent.truth_state
    slant_range_sez = np.array([1e10, 1e10, 1e10, 0.0, 0.0, 0.0])

    # Check Ground Illumination
    visibility, explanation = radar_sensor.isVisible(
        mocked_primary_target.initial_state,
        mocked_primary_target.visual_cross_section,
        mocked_primary_target.reflectivity,
        slant_range_sez,
    )
    assert not visibility
    assert explanation == Explanation.RADAR_SENSITIVITY
