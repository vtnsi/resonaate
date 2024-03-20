"""Defines Optical Sensor unit tests."""

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
from resonaate.physics.sensor_utils import GALACTIC_CENTER_ECI
from resonaate.physics.time.stardate import JulianDate, ScenarioTime, julianDateToDatetime
from resonaate.physics.transforms.methods import eci2ecef, getSlantRangeVector, lla2eci
from resonaate.sensors.optical import Optical


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


def testSensorInit(optical_sensor_args: dict):
    """Test Optical Sensor Initialization.

    Args:
        optical_sensor_args (``dict``):  dictionary of valid arguments to Sensor init
    """
    optical_sensor = Optical(**optical_sensor_args)
    assert optical_sensor
    assert optical_sensor.detectable_vismag == optical_sensor_args["detectable_vismag"]


def testIsVisible(
    mocked_sensing_agent: SensingAgent,
    optical_sensor_args: dict,
    mocked_primary_target: TargetAgent,
):
    """Test Optical sensor `isVisible` function.

    Args:
        mocked_sensing_agent (:class:`.SensingAgent`): mocked sensing agent object
        optical_sensor_args (``dict``):  dictionary of valid arguments to Sensor init
        mocked_primary_target (:class:`.TargetAgent`): mocked Target agent object
    """
    space_optical = Optical(**optical_sensor_args)
    mocked_sensing_agent.agent_type = PlatformLabel.SPACECRAFT
    space_optical.host = mocked_sensing_agent

    utc_datetime = julianDateToDatetime(mocked_sensing_agent.julian_date_epoch)
    mocked_sensing_agent.ecef_state = eci2ecef(mocked_sensing_agent.truth_state, utc_datetime)
    mocked_sensing_agent.eci_state = mocked_sensing_agent.truth_state
    slant_range_sez = getSlantRangeVector(
        mocked_sensing_agent.eci_state,
        mocked_primary_target.initial_state,
        utc_datetime,
    )

    visibility, explanation = space_optical.isVisible(
        mocked_primary_target.initial_state,
        mocked_primary_target.visual_cross_section,
        mocked_primary_target.reflectivity,
        slant_range_sez,
    )

    assert visibility
    assert explanation == Explanation.VISIBLE


def testIsNotVisibleSolarFlux(
    mocked_sensing_agent: SensingAgent,
    optical_sensor_args: dict,
    mocked_primary_target: TargetAgent,
):
    """Test Optical sensor `isVisible` function for solar flux.

    Args:
        mocked_sensing_agent (:class:`.SensingAgent`): mocked sensing agent object
        optical_sensor_args (``dict``):  dictionary of valid arguments to Sensor init
        mocked_primary_target (:class:`.TargetAgent`): mocked Target agent object
    """
    ground_optical = Optical(**optical_sensor_args)
    mocked_sensing_agent.agent_type = PlatformLabel.GROUND_FACILITY
    ground_optical.host = mocked_sensing_agent

    utc_datetime = julianDateToDatetime(mocked_sensing_agent.julian_date_epoch)
    mocked_sensing_agent.ecef_state = eci2ecef(mocked_sensing_agent.truth_state, utc_datetime)
    mocked_sensing_agent.eci_state = mocked_sensing_agent.truth_state
    slant_range_sez = getSlantRangeVector(
        mocked_sensing_agent.eci_state,
        mocked_primary_target.initial_state,
        utc_datetime,
    )

    # Check Solar Flux
    visibility, explanation = ground_optical.isVisible(
        mocked_primary_target.initial_state,
        0.0,
        mocked_primary_target.reflectivity,
        slant_range_sez,
    )
    assert not visibility
    assert explanation == Explanation.SOLAR_FLUX


def testIsNotVisibleVismag(
    mocked_sensing_agent: SensingAgent,
    optical_sensor_args: dict,
    mocked_primary_target: TargetAgent,
):
    """Test Optical sensor `isVisible` function for visual magnitude.

    Args:
        mocked_sensing_agent (:class:`.SensingAgent`): mocked sensing agent object
        optical_sensor_args (``dict``):  dictionary of valid arguments to Sensor init
        mocked_primary_target (:class:`.TargetAgent`): mocked Target agent object
    """
    ground_optical = Optical(**optical_sensor_args)
    mocked_sensing_agent.agent_type = PlatformLabel.GROUND_FACILITY
    ground_optical.host = mocked_sensing_agent

    utc_datetime = julianDateToDatetime(mocked_sensing_agent.julian_date_epoch)
    mocked_sensing_agent.ecef_state = eci2ecef(mocked_sensing_agent.truth_state, utc_datetime)
    mocked_sensing_agent.eci_state = mocked_sensing_agent.truth_state
    slant_range_sez = getSlantRangeVector(
        mocked_sensing_agent.eci_state,
        mocked_primary_target.initial_state,
        utc_datetime,
    )

    # Check Visual Magnitude
    visibility, explanation = ground_optical.isVisible(
        mocked_primary_target.initial_state,
        0.0000000000001,
        0.0000000000001,
        slant_range_sez,
    )
    assert not visibility
    assert explanation == Explanation.VIZ_MAG


def testIsNotVisibleGroundIllumination(
    mocked_sensing_agent: SensingAgent,
    optical_sensor_args: dict,
    mocked_primary_target: TargetAgent,
):
    """Test Optical sensor `isVisible` function for ground illumination.

    Args:
        mocked_sensing_agent (:class:`.SensingAgent`): mocked sensing agent object
        optical_sensor_args (``dict``):  dictionary of valid arguments to Sensor init
        mocked_primary_target (:class:`.TargetAgent`): mocked Target agent object
    """
    ground_optical = Optical(**optical_sensor_args)
    mocked_sensing_agent.agent_type = PlatformLabel.GROUND_FACILITY
    ground_optical.host = mocked_sensing_agent

    utc_datetime = julianDateToDatetime(mocked_sensing_agent.julian_date_epoch)
    mocked_sensing_agent.ecef_state = eci2ecef(mocked_sensing_agent.truth_state, utc_datetime)
    mocked_sensing_agent.eci_state = mocked_sensing_agent.truth_state
    slant_range_sez = getSlantRangeVector(
        mocked_sensing_agent.eci_state,
        mocked_primary_target.initial_state,
        utc_datetime,
    )

    # Check Ground Illumination
    visibility, explanation = ground_optical.isVisible(
        mocked_primary_target.initial_state,
        mocked_primary_target.visual_cross_section,
        mocked_primary_target.reflectivity,
        slant_range_sez,
    )
    assert not visibility
    assert explanation == Explanation.GROUND_ILLUMINATION


def testIsNotVisibleGalacticBelt(
    mocked_sensing_agent: SensingAgent,
    optical_sensor_args: dict,
    mocked_primary_target: TargetAgent,
):
    """Test Optical sensor `isVisible` function for galactic Belt.

    Args:
        mocked_sensing_agent (:class:`.SensingAgent`): mocked sensing agent object
        optical_sensor_args (``dict``):  dictionary of valid arguments to Sensor init
        mocked_primary_target (:class:`.TargetAgent`): mocked Target agent object
    """
    ground_optical = Optical(**optical_sensor_args)
    ground_optical.el_mask[0] = -np.pi / 2
    mocked_sensing_agent.agent_type = PlatformLabel.GROUND_FACILITY
    utc_datetime = julianDateToDatetime(mocked_sensing_agent.julian_date_epoch)

    # Southern Hemisphere LLA
    mocked_sensing_agent.truth_state = lla2eci([np.deg2rad(-60), np.deg2rad(0), 300], utc_datetime)
    ground_optical.host = mocked_sensing_agent

    mocked_sensing_agent.ecef_state = eci2ecef(mocked_sensing_agent.truth_state, utc_datetime)
    mocked_sensing_agent.eci_state = mocked_sensing_agent.truth_state
    slant_range_sez = getSlantRangeVector(
        mocked_sensing_agent.eci_state,
        mocked_primary_target.initial_state,
        utc_datetime,
    )

    # Check Galactic Belt
    galactic_belt_state = np.array(
        [
            GALACTIC_CENTER_ECI[0] * 1e-12,
            GALACTIC_CENTER_ECI[1] * 1e-12,
            GALACTIC_CENTER_ECI[2] * 1e-12,
            0,
            0,
            0,
        ],
    )

    visibility, explanation = ground_optical.isVisible(
        galactic_belt_state,
        mocked_primary_target.visual_cross_section,
        mocked_primary_target.reflectivity,
        slant_range_sez,
    )

    assert not visibility
    assert explanation == Explanation.GALACTIC_EXCLUSION
