from __future__ import annotations

# Standard Library Imports
from unittest.mock import create_autospec

# Third Party Imports
import numpy as np
import pytest

# RESONAATE Imports
from resonaate.agents import GROUND_FACILITY_LABEL, SPACECRAFT_LABEL
from resonaate.agents.sensing_agent import SensingAgent
from resonaate.agents.target_agent import TargetAgent
from resonaate.physics.bodies.earth import Earth
from resonaate.physics.time.stardate import JulianDate, ScenarioTime, julianDateToDatetime
from resonaate.physics.transforms.methods import eci2ecef, getSlantRangeVector
from resonaate.physics.transforms.reductions import updateReductionParameters
from resonaate.sensors.optical import Optical


@pytest.fixture(name="sensor_args")
def getSensorArgs() -> dict:
    """Create dictionary of valid arguments to Sensor init."""
    return {
        "az_mask": np.array((0.0, 360.0)),
        "el_mask": np.array((0.0, 90.0)),
        "r_matrix": np.diag((1.0e-4, 2.5e-5)),
        "diameter": 10,
        "efficiency": 0.95,
        "exemplar": np.array((1.0, 42000.0)),
        "slew_rate": 1.0,
        "field_of_view": {"fov_shape": "conic"},
        "background_observations": True,
        "detectable_vismag": 20.0,
        "minimum_range": 0.0,
        "maximum_range": np.inf,
    }


@pytest.fixture(name="mocked_sensing_agent")
def getSensorAgent() -> SensingAgent:
    """Create a mocked sensing agent object."""
    sensor_agent = create_autospec(spec=SensingAgent, instance=True)
    sensor_agent.time = ScenarioTime(60.0)
    sensor_agent.name = "Test Sensor Agent"
    sensor_agent.simulation_id = 11111
    sensor_agent.truth_state = np.array((0.0, Earth.radius, 0.0, 0.0, 0.0, 0.0))
    sensor_agent.julian_date_epoch = JulianDate(2459486.09964)
    return sensor_agent


@pytest.fixture(name="mocked_primary_target")
def getTargetAgent() -> TargetAgent:
    """Crate a mocked Target agent object."""
    target_agent = create_autospec(spec=TargetAgent, instance=True)
    target_agent.initial_state = np.array((0.0, Earth.radius * 2, 0.0, 0.0, 0.0, 0.0))
    target_agent.visual_cross_section = 25.0
    target_agent.reflectivity = 0.21
    return target_agent


def testSensorInit(sensor_args: dict):
    """Test Optical Sensor Initialization.

    Args:
        sensor_args (dict):  dictionary of valid arguments to Sensor init
    """
    optical_sensor = Optical(**sensor_args)
    assert optical_sensor
    assert optical_sensor.detectable_vismag == sensor_args["detectable_vismag"]


def testGetMeasurements(sensor_args: dict):
    """Test Optical sensor `getMeasurements` function.

    Args:
        sensor_args (dict):  dictionary of valid arguments to Sensor init
    """
    optical_sensor = Optical(**sensor_args)
    measurements = optical_sensor.measurements(np.array([1, 2, 3]), noisy=True)
    assert measurements


def testIsVisible(
    mocked_sensing_agent: SensingAgent, sensor_args: dict, mocked_primary_target: TargetAgent
):
    """Test Optical sensor `isVisible` function.

    Args:
        mocked_sensing_agent (SensingAgent): mocked sensing agent object
        sensor_args (dict):  dictionary of valid arguments to Sensor init
        mocked_primary_target (TargetAgent): mocked Target agent object
    """
    space_optical = Optical(**sensor_args)
    mocked_sensing_agent.agent_type = SPACECRAFT_LABEL
    space_optical.host = mocked_sensing_agent

    updateReductionParameters(julianDateToDatetime(mocked_sensing_agent.julian_date_epoch))
    mocked_sensing_agent.ecef_state = eci2ecef(mocked_sensing_agent.truth_state)
    mocked_sensing_agent.eci_state = mocked_sensing_agent.truth_state
    slant_range_sez = getSlantRangeVector(
        mocked_sensing_agent.ecef_state, mocked_primary_target.initial_state
    )

    visibility, explanation = space_optical.isVisible(
        mocked_primary_target.initial_state,
        mocked_primary_target.visual_cross_section,
        mocked_primary_target.reflectivity,
        slant_range_sez,
    )

    assert visibility
    assert explanation.name == "VISIBLE"


def testIsNotVisible(
    mocked_sensing_agent: SensingAgent, sensor_args: dict, mocked_primary_target: TargetAgent
):
    """Test Optical sensor `getMeasurements` function.

    Args:
        mocked_sensing_agent (SensingAgent): mocked sensing agent object
        sensor_args (dict):  dictionary of valid arguments to Sensor init
        mocked_primary_target (TargetAgent): mocked Target agent object
    """
    ground_optical = Optical(**sensor_args)
    mocked_sensing_agent.agent_type = GROUND_FACILITY_LABEL
    ground_optical.host = mocked_sensing_agent

    updateReductionParameters(julianDateToDatetime(mocked_sensing_agent.julian_date_epoch))
    mocked_sensing_agent.ecef_state = eci2ecef(mocked_sensing_agent.truth_state)
    mocked_sensing_agent.eci_state = mocked_sensing_agent.truth_state
    slant_range_sez = getSlantRangeVector(
        mocked_sensing_agent.ecef_state, mocked_primary_target.initial_state
    )
    visibility, explanation = ground_optical.isVisible(
        mocked_primary_target.initial_state,
        mocked_primary_target.visual_cross_section,
        mocked_primary_target.reflectivity,
        slant_range_sez,
    )
    assert not visibility
    assert explanation.name == "GROUND_ILLUMINATION"

    visibility, explanation = ground_optical.isVisible(
        mocked_primary_target.initial_state,
        0.0,
        mocked_primary_target.reflectivity,
        slant_range_sez,
    )
    assert not visibility
    assert explanation.name == "SOLAR_FLUX"

    visibility, explanation = ground_optical.isVisible(
        mocked_primary_target.initial_state,
        0.0000000000001,
        0.0000000000001,
        slant_range_sez,
    )
    assert not visibility
    assert explanation.name == "VIZ_MAG"
