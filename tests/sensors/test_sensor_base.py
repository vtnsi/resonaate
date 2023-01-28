# pylint: disable=abstract-class-instantiated, invalid-name
from __future__ import annotations

# Standard Library Imports
from copy import deepcopy
from datetime import datetime
from unittest.mock import Mock, create_autospec, patch

# Third Party Imports
import numpy as np
import pytest

# RESONAATE Imports
from resonaate.agents.sensing_agent import SensingAgent
from resonaate.agents.target_agent import TargetAgent
from resonaate.common.exceptions import ShapeError
from resonaate.physics.bodies.earth import Earth
from resonaate.physics.constants import RAD2DEG
from resonaate.physics.time.stardate import JulianDate, ScenarioTime
from resonaate.scenario.config.sensor_config import FieldOfViewConfig
from resonaate.sensors import CONIC_FOV_LABEL, fieldOfViewFactory
from resonaate.sensors.field_of_view import ConicFoV, FieldOfView, RectangularFoV
from resonaate.sensors.radar import Radar
from resonaate.sensors.sensor_base import Sensor


@pytest.fixture(name="mocked_sensing_agent")
def getSensorAgent() -> SensingAgent:
    """Create a mocked sensing agent object."""
    sensor_agent = create_autospec(spec=SensingAgent, instance=True)
    sensor_agent.time = ScenarioTime(60.0)
    sensor_agent.name = "Test Sensor Agent"
    sensor_agent.simulation_id = 11111
    sensor_agent.agent_type = "Spacecraft"
    sensor_agent.truth_state = np.array((0.0, 0.0, 0.0, 0.0, 0.0, 0.0))
    return sensor_agent


@pytest.fixture(name="mocked_primary_target")
def getTargetAgent() -> TargetAgent:
    """Crate a mocked Target agent object."""
    target_agent = create_autospec(spec=TargetAgent, instance=True)
    target_agent.initial_state = np.array((0.0, Earth.radius * 2, 0.0, 0.0, 0.0, 0.0))
    return target_agent


@pytest.fixture(name="mocked_background_target")
def getBackgroundTargetAgent() -> TargetAgent:
    """Crate a mocked Target agent object."""
    background_target = create_autospec(spec=TargetAgent, instance=True)
    background_target.initial_state = np.array((0.0, Earth.radius * 2 + 1, 0.0, 0.0, 0.0, 0.0))
    return background_target


def testSensorInit(base_sensor_args: dict, mocked_sensing_agent: SensingAgent):
    """Test initializing Sensor base class."""
    base_sensor = Sensor(**base_sensor_args)
    assert base_sensor
    assert np.allclose(base_sensor.az_mask, np.deg2rad(base_sensor_args["az_mask"]))
    assert np.allclose(base_sensor.el_mask, np.deg2rad(base_sensor_args["el_mask"]))
    assert np.isclose(base_sensor.aperture_area, np.pi * (base_sensor_args["diameter"] * 0.5) ** 2)
    assert np.isclose(base_sensor.slew_rate, np.deg2rad(base_sensor_args["slew_rate"]))
    assert base_sensor.field_of_view is not None
    assert base_sensor.time_last_ob >= 0.0
    assert base_sensor.delta_boresight == 0.0
    assert base_sensor.host is None
    init_boresight = np.array(
        [
            np.cos(np.deg2rad(45)) * np.cos(np.deg2rad(180)),
            np.cos(np.deg2rad(45)) * np.sin(np.deg2rad(180)),
            np.sin(np.deg2rad(45)),
        ]
    )
    assert np.allclose(base_sensor.boresight, init_boresight)

    base_sensor.host = mocked_sensing_agent
    assert base_sensor.host is not None
    assert base_sensor.time_last_ob > 0.0


def testSensorInitAzElMask(base_sensor_args: dict):
    """Test edge case values for the az/el mask."""
    sen_args = deepcopy(base_sensor_args)

    # Limits test
    sen_args["az_mask"] = np.array((0.0, 360.0))
    _ = Sensor(**sen_args)

    # Order test
    sen_args["az_mask"] = np.array((350.0, 10.0))
    _ = Sensor(**sen_args)

    # Limits test
    sen_args["el_mask"] = np.array((-90.0, 90.0))
    _ = Sensor(**sen_args)

    # Order test
    sen_args["el_mask"] = np.array((20.0, -20.0))
    _ = Sensor(**sen_args)


def testSensorInitAzElMaskBadValues(base_sensor_args: dict):
    """Test bad values for the az/el mask."""
    value_err_msg = r"\w*Invalid value \[0, 2π] for az_mask\w*"
    sen_args = deepcopy(base_sensor_args)
    sen_args["az_mask"] = np.array((-181.0, 180.0))
    with pytest.raises(ValueError, match=value_err_msg):
        _ = Sensor(**sen_args)

    sen_args = deepcopy(base_sensor_args)
    sen_args["az_mask"] = np.array((0.0, 400.0))
    with pytest.raises(ValueError, match=value_err_msg):
        _ = Sensor(**sen_args)

    value_err_msg = r"\w*Invalid value \[-π/2, π/2] for el_mask\w*"
    sen_args = deepcopy(base_sensor_args)
    sen_args["el_mask"] = np.array((-91.0, 90.0))
    with pytest.raises(ValueError, match=value_err_msg):
        _ = Sensor(**sen_args)

    sen_args = deepcopy(base_sensor_args)
    sen_args["el_mask"] = np.array((-90.0, 100.0))
    with pytest.raises(ValueError, match=value_err_msg):
        _ = Sensor(**sen_args)


def testSensorInitAzElMaskTypes(base_sensor_args: dict):
    """Test bad types for the az/el mask."""
    sen_args = deepcopy(base_sensor_args)
    sen_args["az_mask"] = np.array((-180.0, 180.0, 0.0))
    with pytest.raises(ShapeError, match=r"\w*Invalid shape for az_mask\w*"):
        _ = Sensor(**sen_args)

    sen_args = deepcopy(base_sensor_args)
    sen_args["el_mask"] = np.array((-90.0, 90.0, 0.0))
    with pytest.raises(ShapeError, match=r"\w*Invalid shape for el_mask\w*"):
        _ = Sensor(**sen_args)


def testCanSlew(base_sensor_args: dict, mocked_sensing_agent: SensingAgent):
    """Test whether the sensor can slew to a target or not."""
    sensor = Sensor(**base_sensor_args)
    sensor.host = mocked_sensing_agent
    sensor.time_last_ob = 0.0

    # Assumes 1 deg/sec slew rate & 60 sec dt
    assert not sensor.canSlew(np.array((1.0, 0.0, 0.0)))
    assert not sensor.canSlew(np.array((0.0, 1.0, 0.0)))
    assert not sensor.canSlew(np.array((0.5, 0.5, 0.5)))
    assert sensor.canSlew(np.array((-0.7, 0.0, 0.7)))
    assert sensor.canSlew(np.array((-0.7, 0.5, 0.7)))
    assert sensor.canSlew(np.array((-0.2, 0.0, 0.7)))


def testInFOVConic(base_sensor_args: dict):
    """Test whether a target is in the field of view of the sensor."""
    # pylint:disable=protected-access
    sensor = Sensor(**base_sensor_args)
    sensor.field_of_view = ConicFoV(cone_angle=np.pi)

    tgt_sez = np.array((1.0, 0.0, 0.0, 0.0, 0.0, 0.0))
    bkg_sez = np.array((1.0, 1.0, 0.0, 0.0, 0.0, 0.0))
    assert sensor.field_of_view.inFieldOfView(tgt_sez, bkg_sez)

    bkg_sez = np.array((1.0, 0.0, 1.0, 0.0, 0.0, 0.0))
    assert sensor.field_of_view.inFieldOfView(tgt_sez, bkg_sez)

    bkg_sez = np.array((-1.0, 0.0, -1.0, 0.0, 0.0, 0.0))
    assert not sensor.field_of_view.inFieldOfView(tgt_sez, bkg_sez)

    sensor.field_of_view._cone_angle = np.pi / 2 - 1
    bkg_sez = np.array((1.0, 1.0, 0.0, 0.0, 0.0, 0.0))
    assert not sensor.field_of_view.inFieldOfView(tgt_sez, bkg_sez)


def testInFOVRegular(base_sensor_args: dict):
    """Test whether a target is in the field of view of the sensor."""
    # pylint:disable=protected-access
    sensor = Sensor(**base_sensor_args)
    sensor.field_of_view = RectangularFoV(azimuth_angle=np.pi, elevation_angle=np.pi)
    tgt_sez = np.array((1.0, 0.0, 0.0, 0.0, 0.0, 0.0))
    bkg_sez = np.array((1.0, 1.0, 0.0, 0.0, 0.0, 0.0))
    assert sensor.field_of_view.inFieldOfView(tgt_sez, bkg_sez)

    bkg_sez = np.array((1.0, 0.0, 1.0, 0.0, 0.0, 0.0))
    assert sensor.field_of_view.inFieldOfView(tgt_sez, bkg_sez)

    bkg_sez = np.array((-1.0, 0.0, -1.0, 0.0, 0.0, 0.0))
    assert not sensor.field_of_view.inFieldOfView(tgt_sez, bkg_sez)

    sensor.field_of_view._azimuth_angle = np.pi / 2 - 1
    sensor.field_of_view._elevation_angle = np.pi / 2 - 1
    bkg_sez = np.array((1.0, 1.5, 0.0, 0.0, 0.0, 0.0))
    assert not sensor.field_of_view.inFieldOfView(tgt_sez, bkg_sez)


def _dummySlantRange(
    eci_sensor: np.ndarray, eci_tgt: np.ndarray, utc_date: datetime
) -> np.ndarray:
    """Dummy slant range function; passes through the eci_tgt parameter."""
    # pylint: disable=unused-argument
    return eci_tgt


@patch("resonaate.sensors.sensor_base.getSlantRangeVector", new=_dummySlantRange)
def testCheckTargetsInView(base_sensor_args: dict, mocked_sensing_agent: SensingAgent):
    """Checks whether list of targets is in the FOV of the sensor."""
    # pylint: disable=abstract-class-instantiated
    sensor = Sensor(**base_sensor_args)
    conic_fov_config = FieldOfViewConfig(fov_shape=CONIC_FOV_LABEL, cone_angle=np.pi * RAD2DEG - 1)
    sensor.field_of_view = fieldOfViewFactory(conic_fov_config)
    # Requires self.host.ecef_state to be set
    sensor.host = mocked_sensing_agent
    sensor.host.ecef_state = np.zeros(6)
    sensor.host.julian_date_epoch = JulianDate(2459569.75)

    # Target SEZ position
    tgt_sez = np.array((1.0, 0.0, 0.0, 0.0, 0.0, 0.0))

    # Create mocks for TargetAgent objects with `eci_state`
    agent_1 = Mock()
    agent_2 = Mock()
    agent_3 = Mock()
    agent_4 = Mock()
    agent_1.eci_state = np.array((1.0, 0.0, 0.0, 0.0, 0.0, 0.0))
    agent_2.eci_state = np.array((-1.0, 0.0, -1.0, 0.0, 0.0, 0.0))  # outside FOV
    agent_3.eci_state = np.array((1.0, 1.0, 0.0, 0.0, 0.0, 0.0))
    agent_4.eci_state = np.array((1.0, 0.0, 1.0, 0.0, 0.0, 0.0))

    targets_in_fov = sensor.checkTargetsInView(tgt_sez, [agent_1, agent_2, agent_3, agent_4])
    assert targets_in_fov == [agent_1, agent_3, agent_4]
    targets_in_fov = sensor.checkTargetsInView(tgt_sez, [agent_1, agent_2])
    assert targets_in_fov == [agent_1]
    targets_in_fov = sensor.checkTargetsInView(tgt_sez, [agent_3])
    assert targets_in_fov == [agent_3]
    targets_in_fov = sensor.checkTargetsInView(tgt_sez, [agent_2])
    assert not targets_in_fov


def testIsVisible(base_sensor_args: dict, mocked_sensing_agent: SensingAgent):
    """Test that and RSO `isVisible`."""
    # pylint: disable=too-many-statements
    sensor = Sensor(**base_sensor_args)
    # Requires self.host.eci_state to be set
    sensor.host = mocked_sensing_agent
    sensor.host.eci_state = np.array((6378.0, 0.0, 0.0, 0.0, 0.0, 0.0))
    sensor.host.julian_date_epoch = JulianDate(2459569.75)

    # Target is visible initially
    tgt_eci_state = np.array((7800.0, 0.0, 0.0, 0.0, 0.0, 0.0))
    sez_state = np.array((1422, 0.0, 0.0, 0.0, 0.0, 0.0))
    visibility, _ = sensor.isVisible(tgt_eci_state, 10.0, 10.0, sez_state)
    assert visibility

    # Test min range with large enough to force failure
    sensor.minimum_range = 1e6
    visibility, _ = sensor.isVisible(tgt_eci_state, 10.0, 10.0, sez_state)
    assert not visibility
    # reasonable min range, but not zero
    sensor.minimum_range = 10.0
    visibility, _ = sensor.isVisible(tgt_eci_state, 10.0, 10.0, sez_state)
    assert visibility
    # min range of None
    sensor.minimum_range = None
    visibility, _ = sensor.isVisible(tgt_eci_state, 10.0, 10.0, sez_state)
    assert visibility
    # min range of zero
    sensor.minimum_range = 0.0
    visibility, _ = sensor.isVisible(tgt_eci_state, 10.0, 10.0, sez_state)
    assert visibility
    # min range reasonable, but not large enough
    sensor.minimum_range = 100.0
    visibility, _ = sensor.isVisible(tgt_eci_state, 10.0, 10.0, sez_state)
    assert visibility

    # Test max range with small enough to force failure
    sensor.maximum_range = 10.0
    visibility, _ = sensor.isVisible(tgt_eci_state, 10.0, 10.0, sez_state)
    assert not visibility
    # reasonable max range, but not infinity
    sensor.maximum_range = 1e6
    visibility, _ = sensor.isVisible(tgt_eci_state, 10.0, 10.0, sez_state)
    assert visibility
    # max range of None
    sensor.maximum_range = None
    visibility, _ = sensor.isVisible(tgt_eci_state, 10.0, 10.0, sez_state)
    assert visibility
    # max range of zero
    sensor.maximum_range = 0.0
    visibility, _ = sensor.isVisible(tgt_eci_state, 10.0, 10.0, sez_state)
    assert not visibility
    # max range of infinity
    sensor.maximum_range = np.inf
    visibility, _ = sensor.isVisible(tgt_eci_state, 10.0, 10.0, sez_state)
    assert visibility
    # Test LOS in view
    visibility, _ = sensor.isVisible(tgt_eci_state, 10.0, 10.0, sez_state)
    assert visibility
    # LOS not in View
    visibility, _ = sensor.isVisible(-tgt_eci_state, 10.0, 10.0, sez_state)
    assert not visibility
    # Test elevation mask constraint
    # Pass on boundaries
    sez_state = np.array((1422, 0.0, 0.0, 0.0, 0.0, 0.0))  # 0 elevation
    sensor.el_mask = np.deg2rad(np.array((0.0, 90.0)))
    visibility, _ = sensor.isVisible(tgt_eci_state, 10.0, 10.0, sez_state)
    assert visibility
    sez_state = np.array((0.0, 0.0, 1422.0, 0.0, 0.0, 0.0))  # 90 elevation
    visibility, _ = sensor.isVisible(tgt_eci_state, 10.0, 10.0, sez_state)
    assert visibility
    # Fail outside boundaries
    sez_state = np.array((1422, 0.0, 0.0, 0.0, 0.0, 0.0))  # 0 elevation
    sensor.el_mask = np.deg2rad(np.array((1.0, 89.0)))
    visibility, _ = sensor.isVisible(tgt_eci_state, 10.0, 10.0, sez_state)
    assert not visibility
    sez_state = np.array((0.0, 0.0, 1422.0, 0.0, 0.0, 0.0))  # 90 elevation
    visibility, _ = sensor.isVisible(tgt_eci_state, 10.0, 10.0, sez_state)
    assert not visibility

    # Pass in more normal case
    sez_state = np.array((0.0, 800.0, 1422.0, 0.0, 0.0, 0.0))  # 60 elevation
    sensor.el_mask = np.deg2rad(np.array((10.0, 89.9)))
    visibility, _ = sensor.isVisible(tgt_eci_state, 10.0, 10.0, sez_state)
    assert visibility

    # Test azimuth mask constraint
    sensor.el_mask = np.deg2rad(np.array((0.0, 90.0)))
    sensor.az_mask = np.deg2rad(np.array((0.0, 180.0)))
    sez_state = np.array((1422, 0.0, 0.0, 0.0, 0.0, 0.0))  # 180 azimuth
    visibility, _ = sensor.isVisible(tgt_eci_state, 10.0, 10.0, sez_state)
    assert visibility
    sez_state = np.array((-1422, 0.0, 0.0, 0.0, 0.0, 0.0))  # 0 azimuth
    visibility, _ = sensor.isVisible(tgt_eci_state, 10.0, 10.0, sez_state)
    assert visibility
    sez_state = np.array((-1422, 800.0, 0.0, 0.0, 0.0, 0.0))  # 30 azimuth
    visibility, _ = sensor.isVisible(tgt_eci_state, 10.0, 10.0, sez_state)
    assert visibility

    sensor.az_mask = np.deg2rad(np.array((10.0, 170.0)))
    sez_state = np.array((1422, 0.0, 0.0, 0.0, 0.0, 0.0))  # 180 azimuth
    visibility, _ = sensor.isVisible(tgt_eci_state, 10.0, 10.0, sez_state)
    assert not visibility
    sez_state = np.array((-1422, 0.0, 0.0, 0.0, 0.0, 0.0))  # 0 azimuth
    visibility, _ = sensor.isVisible(tgt_eci_state, 10.0, 10.0, sez_state)
    assert not visibility
    sez_state = np.array((-1422, 800.0, 0.0, 0.0, 0.0, 0.0))  # 30 azimuth
    visibility, _ = sensor.isVisible(tgt_eci_state, 10.0, 10.0, sez_state)
    assert visibility

    # Test azimuth mask constraint with flipped mask
    sensor.az_mask = np.deg2rad(np.array((180.0, 0.0)))
    sez_state = np.array((1422, 0.0, 0.0, 0.0, 0.0, 0.0))  # 180 azimuth
    visibility, _ = sensor.isVisible(tgt_eci_state, 10.0, 10.0, sez_state)
    assert visibility
    sez_state = np.array((-1422, 0.0, 0.0, 0.0, 0.0, 0.0))  # 0 azimuth
    visibility, _ = sensor.isVisible(tgt_eci_state, 10.0, 10.0, sez_state)
    assert visibility
    sez_state = np.array((-1422, -800.0, 0.0, 0.0, 0.0, 0.0))  # 330 azimuth
    visibility, _ = sensor.isVisible(tgt_eci_state, 10.0, 10.0, sez_state)
    assert visibility

    sensor.az_mask = np.deg2rad(np.array((190.0, 350.0)))
    sez_state = np.array((1422, 0.0, 0.0, 0.0, 0.0, 0.0))  # 180 azimuth
    visibility, _ = sensor.isVisible(tgt_eci_state, 10.0, 10.0, sez_state)
    assert not visibility
    sez_state = np.array((-1422, 0.0, 0.0, 0.0, 0.0, 0.0))  # 0 azimuth
    visibility, _ = sensor.isVisible(tgt_eci_state, 10.0, 10.0, sez_state)
    assert not visibility
    sez_state = np.array((-1422, -800.0, 0.0, 0.0, 0.0, 0.0))  # 330 azimuth
    visibility, _ = sensor.isVisible(tgt_eci_state, 10.0, 10.0, sez_state)
    assert visibility


@patch("resonaate.sensors.sensor_base.getSlantRangeVector", new=_dummySlantRange)
def testCollectObservationsInFoVNoBackground(
    radar_sensor_args: dict, mocked_sensing_agent: SensingAgent, mocked_primary_target: TargetAgent
):
    """Test that an RSO is in the FoV."""
    sensor = Radar(**radar_sensor_args)
    sensor.host = mocked_sensing_agent
    sensor.calculate_background = False
    sensor.field_of_view = create_autospec(spec=FieldOfView, instance=True)
    sensor.field_of_view.fov_shape = "conic"
    sensor.field_of_view.cone_angle = np.pi
    sensor.maximum_range = 1000000
    sensor.minimum_range = 1.0

    mocked_sensing_agent.sensors = sensor
    mocked_sensing_agent.ecef_state = np.array((0.0, Earth.radius, 0.0, 0.0, 0.0, 0.0))
    mocked_sensing_agent.eci_state = np.array((0.0, Earth.radius, 0.0, 0.0, 0.0, 0.0))
    mocked_sensing_agent.time = ScenarioTime(300)
    mocked_sensing_agent.sensor_time_bias_event_queue = []
    mocked_sensing_agent.lla_state = np.array((0.0, 0.0, Earth.radius))
    mocked_sensing_agent.julian_date_epoch = JulianDate(2459304.1701388885)

    mocked_primary_target.eci_state = mocked_primary_target.initial_state
    mocked_primary_target.visual_cross_section = 25.0
    good_obs, _ = mocked_sensing_agent.sensors.collectObservations(
        mocked_primary_target.initial_state, mocked_primary_target, [mocked_primary_target]
    )
    assert len(good_obs) == 1


@patch("resonaate.sensors.sensor_base.getSlantRangeVector", new=_dummySlantRange)
def testCollectObservationsNotInFoVNoBackground(
    radar_sensor_args: dict, mocked_sensing_agent: SensingAgent, mocked_primary_target: TargetAgent
):
    """Test that an RSO is Not in the FoV."""
    sensor = Radar(**radar_sensor_args)
    sensor.host = mocked_sensing_agent
    sensor.calculate_background = False
    sensor.field_of_view = create_autospec(spec=FieldOfView, instance=True)
    sensor.field_of_view.fov_shape = "conic"
    sensor.field_of_view.cone_angle = np.pi
    sensor.maximum_range = 100000

    mocked_sensing_agent.sensors = sensor
    mocked_sensing_agent.ecef_state = np.array((0.0, Earth.radius, 0.0, 0.0, 0.0, 0.0))
    mocked_sensing_agent.eci_state = np.array((0.0, -Earth.radius, 0.0, 0.0, 0.0, 0.0))
    mocked_sensing_agent.time = ScenarioTime(300)
    mocked_sensing_agent.sensor_time_bias_event_queue = []
    mocked_sensing_agent.lla_state = np.array((0.0, 0.0, Earth.radius))
    mocked_sensing_agent.julian_date_epoch = JulianDate(2459304.1701388885)

    mocked_primary_target.eci_state = mocked_primary_target.initial_state
    mocked_primary_target.visual_cross_section = 25.0
    good_obs, _ = mocked_sensing_agent.sensors.collectObservations(
        mocked_primary_target.initial_state, mocked_primary_target, [mocked_primary_target]
    )
    assert not good_obs


@patch("resonaate.sensors.sensor_base.getSlantRangeVector", new=_dummySlantRange)
def testCollectObservationsWithBackground(
    radar_sensor_args: dict,
    mocked_sensing_agent: SensingAgent,
    mocked_primary_target: TargetAgent,
    mocked_background_target: TargetAgent,
):
    """Test that background RSO is in the FoV."""
    sensor = Radar(**radar_sensor_args)
    sensor.host = mocked_sensing_agent
    sensor.calculate_background = True
    sensor.field_of_view = create_autospec(spec=FieldOfView, instance=True)
    sensor.field_of_view.fov_shape = "conic"
    sensor.field_of_view.cone_angle = np.pi
    sensor.maximum_range = 100000

    mocked_sensing_agent.sensors = sensor
    mocked_sensing_agent.ecef_state = np.array((0.0, Earth.radius, 0.0, 0.0, 0.0, 0.0))
    mocked_sensing_agent.eci_state = np.array((0.0, Earth.radius, 0.0, 0.0, 0.0, 0.0))
    mocked_sensing_agent.time = ScenarioTime(300)
    mocked_sensing_agent.sensor_time_bias_event_queue = []
    mocked_sensing_agent.lla_state = np.array((0.0, 0.0, Earth.radius))
    mocked_sensing_agent.julian_date_epoch = JulianDate(2459304.1701388885)

    mocked_primary_target.eci_state = mocked_primary_target.initial_state
    mocked_primary_target.visual_cross_section = 25.0

    mocked_background_target.eci_state = mocked_background_target.initial_state
    mocked_background_target.visual_cross_section = 25.0
    good_obs, _ = mocked_sensing_agent.sensors.collectObservations(
        mocked_primary_target.initial_state,
        mocked_primary_target,
        [mocked_background_target],
    )
    assert len(good_obs) == 2


@patch("resonaate.sensors.sensor_base.getSlantRangeVector", new=_dummySlantRange)
def testNoMissedObservation(
    radar_sensor_args: dict, mocked_sensing_agent: SensingAgent, mocked_primary_target: TargetAgent
):
    """Test that an RSO is in the FoV."""
    sensor = Radar(**radar_sensor_args)
    sensor.host = mocked_sensing_agent
    sensor.calculate_background = False
    sensor.field_of_view = create_autospec(spec=FieldOfView, instance=True)
    sensor.field_of_view.fov_shape = "conic"
    sensor.field_of_view.cone_angle = np.pi
    sensor.maximum_range = 10000000

    mocked_sensing_agent.sensors = sensor
    mocked_sensing_agent.ecef_state = np.array((0.0, Earth.radius, 0.0, 0.0, 0.0, 0.0))
    mocked_sensing_agent.eci_state = np.array((0.0, Earth.radius, 0.0, 0.0, 0.0, 0.0))
    mocked_sensing_agent.time = ScenarioTime(300)
    mocked_sensing_agent.sensor_time_bias_event_queue = []
    mocked_sensing_agent.lla_state = np.array((0.0, 0.0, Earth.radius))
    mocked_sensing_agent.julian_date_epoch = JulianDate(2459304.1701388885)

    mocked_primary_target.eci_state = mocked_primary_target.initial_state
    mocked_primary_target.visual_cross_section = 25.0
    _, missed_obs = mocked_sensing_agent.sensors.collectObservations(
        mocked_primary_target.initial_state, mocked_primary_target, [mocked_primary_target]
    )
    assert not missed_obs


@patch("resonaate.sensors.sensor_base.getSlantRangeVector", new=_dummySlantRange)
def testMissedObservation(
    radar_sensor_args: dict, mocked_sensing_agent: SensingAgent, mocked_primary_target: TargetAgent
):
    """Test that an RSO is Not in the FoV."""
    sensor = Radar(**radar_sensor_args)
    sensor.host = mocked_sensing_agent
    sensor.calculate_background = False
    sensor.field_of_view = create_autospec(spec=FieldOfView, instance=True)
    sensor.field_of_view.fov_shape = "conic"
    sensor.field_of_view.cone_angle = np.pi
    sensor.maximum_range = 100000

    mocked_sensing_agent.sensors = sensor
    mocked_sensing_agent.ecef_state = np.array((0.0, Earth.radius, 0.0, 0.0, 0.0, 0.0))
    mocked_sensing_agent.eci_state = np.array((0.0, -Earth.radius, 0.0, 0.0, 0.0, 0.0))
    mocked_sensing_agent.time = ScenarioTime(300)
    mocked_sensing_agent.sensor_time_bias_event_queue = []
    mocked_sensing_agent.lla_state = np.array((0.0, 0.0, Earth.radius))
    mocked_sensing_agent.julian_date_epoch = JulianDate(2459304.1701388885)

    mocked_primary_target.eci_state = mocked_primary_target.initial_state
    mocked_primary_target.visual_cross_section = 25.0
    _, bad_obs = mocked_sensing_agent.sensors.collectObservations(
        mocked_primary_target.initial_state, mocked_primary_target, [mocked_primary_target]
    )
    assert len(bad_obs) == 1


def testBuildSigmaObs():
    """To be implemented."""


def testAttemptObservation():
    """To be implemented."""


def testAttemptNoisyObservation():
    """To be implemented."""
