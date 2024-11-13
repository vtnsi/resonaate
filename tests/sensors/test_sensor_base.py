from __future__ import annotations

# Standard Library Imports
from copy import deepcopy
from datetime import datetime
from unittest.mock import MagicMock, Mock, create_autospec, patch

# Third Party Imports
import numpy as np
import pytest

# RESONAATE Imports
from resonaate.agents.sensing_agent import SensingAgent
from resonaate.agents.target_agent import TargetAgent
from resonaate.common.exceptions import ShapeError
from resonaate.common.labels import Explanation
from resonaate.data.observation import MissedObservation, Observation
from resonaate.physics.bodies.earth import Earth
from resonaate.physics.constants import RAD2DEG
from resonaate.physics.time.stardate import JulianDate, ScenarioTime
from resonaate.scenario.config.sensor_config import ConicFieldOfViewConfig
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
    sensor_agent.sensor_time_bias_event_queue = []
    return sensor_agent


@pytest.fixture(name="mocked_primary_target")
def getTargetAgent() -> TargetAgent:
    """Crate a mocked Target agent object."""
    target_agent = create_autospec(spec=TargetAgent, instance=True)
    target_agent.initial_state = np.array((0.0, Earth.radius * 2, 0.0, 0.0, 0.0, 0.0))
    target_agent.simulation_id = 123456
    target_agent.visual_cross_section = 10.0
    target_agent.reflectivity = 10.0
    return target_agent


@pytest.fixture(name="mocked_background_target")
def getBackgroundTargetAgent() -> TargetAgent:
    """Crate a mocked Target agent object."""
    background_target = create_autospec(spec=TargetAgent, instance=True)
    background_target.initial_state = np.array((0.0, Earth.radius * 2 + 1, 0.0, 0.0, 0.0, 0.0))
    return background_target


@patch.multiple(Sensor, __abstractmethods__=set())
def testSensorInit(base_sensor_args: dict, mocked_sensing_agent: SensingAgent):
    """Test initializing Sensor base class."""
    base_sensor = Sensor(**base_sensor_args)
    assert base_sensor
    assert np.allclose(base_sensor.az_mask, np.deg2rad(base_sensor_args["az_mask"]))
    assert np.allclose(base_sensor.el_mask, np.deg2rad(base_sensor_args["el_mask"]))
    assert np.isclose(
        base_sensor.effective_aperture_area,
        np.pi * (base_sensor_args["diameter"] * 0.5) ** 2,
    )
    assert np.isclose(base_sensor.aperture_diameter, base_sensor_args["diameter"])
    assert np.isclose(base_sensor.slew_rate, np.deg2rad(base_sensor_args["slew_rate"]))
    assert base_sensor.field_of_view is not None
    assert base_sensor.time_last_tasked >= 0.0

    # Should raise an error b/c not set
    match = r"SensingAgent.host was not \(or was incorrectly\) initialized"
    with pytest.raises(ValueError, match=match):
        _ = base_sensor.host

    init_boresight = np.array(
        [
            np.cos(np.deg2rad(45)) * np.cos(np.deg2rad(180)),
            np.cos(np.deg2rad(45)) * np.sin(np.deg2rad(180)),
            np.sin(np.deg2rad(45)),
        ],
    )
    assert np.allclose(base_sensor.boresight, init_boresight)

    base_sensor.host = mocked_sensing_agent
    assert base_sensor.host is not None
    assert base_sensor.time_last_tasked > 0.0


@patch.multiple(Sensor, __abstractmethods__=set())
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


@patch.multiple(Sensor, __abstractmethods__=set())
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


@patch.multiple(Sensor, __abstractmethods__=set())
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


@patch.multiple(Sensor, __abstractmethods__=set())
def testCanSlew(base_sensor_args: dict, mocked_sensing_agent: SensingAgent):
    """Test whether the sensor can slew to a target or not."""
    sensor = Sensor(**base_sensor_args)
    sensor.host = mocked_sensing_agent
    sensor.time_last_tasked = 0.0

    # Assumes 1 deg/sec slew rate & 60 sec dt
    assert not sensor.canSlew(np.array((1.0, 0.0, 0.0)))
    assert not sensor.canSlew(np.array((0.0, 1.0, 0.0)))
    assert not sensor.canSlew(np.array((0.5, 0.5, 0.5)))
    assert sensor.canSlew(np.array((-0.7, 0.0, 0.7)))
    assert sensor.canSlew(np.array((-0.7, 0.5, 0.7)))
    assert sensor.canSlew(np.array((-0.2, 0.0, 0.7)))


@patch.multiple(Sensor, __abstractmethods__=set())
def testInFOVConic(base_sensor_args: dict):
    """Test whether a target is in the field of view of the sensor."""
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


@patch.multiple(Sensor, __abstractmethods__=set())
def testInFOVRegular(base_sensor_args: dict):
    """Test whether a target is in the field of view of the sensor."""
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
    eci_sensor: np.ndarray,
    eci_tgt: np.ndarray,
    utc_date: datetime,
) -> np.ndarray:
    """Dummy slant range function; passes through the eci_tgt parameter."""
    return eci_tgt


@patch.multiple(Sensor, __abstractmethods__=set())
@patch("resonaate.sensors.sensor_base.getSlantRangeVector", new=_dummySlantRange)
def testCheckTargetsInView(base_sensor_args: dict, mocked_sensing_agent: SensingAgent):
    """Checks whether list of targets is in the FOV of the sensor."""
    sensor = Sensor(**base_sensor_args)
    conic_fov_config = ConicFieldOfViewConfig(cone_angle=np.pi * RAD2DEG - 1)
    sensor.field_of_view = FieldOfView.fromConfig(conic_fov_config)
    # Requires self.host.ecef_state to be set
    sensor.host = mocked_sensing_agent
    sensor.host.ecef_state = np.zeros(6)
    sensor.host.julian_date_epoch = JulianDate(2459569.75)

    # Target SEZ position
    pointing_sez = np.array((1.0, 0.0, 0.0, 0.0, 0.0, 0.0))

    # Test target outside FOV
    agent = Mock()
    agent.eci_state = np.array((-1.0, 0.0, -1.0, 0.0, 0.0, 0.0))  # outside FOV

    observation = sensor.attemptObservation(agent, pointing_sez)
    assert isinstance(observation, MissedObservation)

    # Test target inside FOV
    agent.eci_state = np.array((1.0, 0.0, 0.0, 0.0, 0.0, 0.0))  # inside FOV

    with (
        patch.object(
            sensor,
            "isVisible",
            return_value=(True, Explanation.VISIBLE),
        ) as mock_visible_check,
        patch.object(
            Observation,
            "fromMeasurement",
            return_value=create_autospec(Observation, instance=True),
        ) as mock_observation_from_measurement,
    ):
        observation = sensor.attemptObservation(agent, pointing_sez)
        assert isinstance(observation, Observation)
        mock_visible_check.assert_called_once()
        mock_observation_from_measurement.assert_called_once()


@patch.multiple(Sensor, __abstractmethods__=set())
def testIsVisible(base_sensor_args: dict, mocked_sensing_agent: SensingAgent):
    """Test that and RSO `isVisible`."""
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
def testCollectObservations(
    radar_sensor_args: dict,
    mocked_sensing_agent: SensingAgent,
    mocked_primary_target: TargetAgent,
):
    """Test `Sensor.collectObservations`."""
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

    # Test when target can be collected on
    good_obs, _, _, _ = mocked_sensing_agent.sensors.collectObservations(
        mocked_primary_target.initial_state,
        mocked_primary_target,
        [mocked_primary_target],
    )
    assert len(good_obs) == 1

    # Check that boresight was updated
    slant_range_sez = _dummySlantRange(
        mocked_sensing_agent.eci_state,
        mocked_primary_target.initial_state,
        mocked_sensing_agent.datetime_epoch,
    )
    assert np.allclose(
        mocked_sensing_agent.sensors.boresight,
        slant_range_sez[:3] / np.linalg.norm(slant_range_sez[:3]),
    )

    # Test when target is not in line of sight (Earth is blocking)
    mocked_sensing_agent.eci_state = np.array((0.0, -Earth.radius, 0.0, 0.0, 0.0, 0.0))

    mocked_sensing_agent.sensors.boresight = mocked_sensing_agent.sensors._setInitialBoresight()
    with patch.object(mocked_sensing_agent.sensors, "canSlew", return_value=True):
        good_obs, missed_obs, _, _ = mocked_sensing_agent.sensors.collectObservations(
            mocked_primary_target.initial_state,
            mocked_primary_target,
            [mocked_primary_target],
        )
        assert not good_obs

    # If target was in slew distance, then the boresight should have updated
    slant_range_sez = _dummySlantRange(
        mocked_sensing_agent.eci_state,
        mocked_primary_target.initial_state,
        mocked_sensing_agent.datetime_epoch,
    )
    assert np.allclose(
        mocked_sensing_agent.sensors.boresight,
        slant_range_sez[:3] / np.linalg.norm(slant_range_sez[:3]),
    )

    for missed_ob in missed_obs:
        assert missed_ob.reason == Explanation.LINE_OF_SIGHT.value

    mocked_sensing_agent.sensors.boresight = mocked_sensing_agent.sensors._setInitialBoresight()
    with patch.object(mocked_sensing_agent.sensors, "canSlew", return_value=False):
        good_obs, missed_obs, _, _ = mocked_sensing_agent.sensors.collectObservations(
            mocked_primary_target.initial_state,
            mocked_primary_target,
            [mocked_primary_target],
        )
        assert not good_obs

    # If the sensor rejected the task because it could not slew to the target, then boresight should not have changed
    slant_range_sez = _dummySlantRange(
        mocked_sensing_agent.eci_state,
        mocked_primary_target.initial_state,
        mocked_sensing_agent.datetime_epoch,
    )
    assert np.allclose(
        mocked_sensing_agent.sensors.boresight,
        mocked_sensing_agent.sensors._setInitialBoresight(),
    )
    for missed_ob in missed_obs:
        assert missed_ob.reason == Explanation.SLEW_DISTANCE.value


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
    good_obs, _, _, _ = mocked_sensing_agent.sensors.collectObservations(
        mocked_primary_target.initial_state,
        mocked_primary_target,
        [mocked_background_target],
    )
    assert len(good_obs) == 2


@patch("resonaate.sensors.sensor_base.getSlantRangeVector", new=_dummySlantRange)
def testNoMissedObservation(
    radar_sensor_args: dict,
    mocked_sensing_agent: SensingAgent,
    mocked_primary_target: TargetAgent,
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
    _, missed_obs, _, _ = mocked_sensing_agent.sensors.collectObservations(
        mocked_primary_target.initial_state,
        mocked_primary_target,
        [mocked_primary_target],
    )
    assert not missed_obs


@patch("resonaate.sensors.sensor_base.getSlantRangeVector", new=_dummySlantRange)
def testMissedObservation(
    radar_sensor_args: dict,
    mocked_sensing_agent: SensingAgent,
    mocked_primary_target: TargetAgent,
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
    _, bad_obs, _, _ = mocked_sensing_agent.sensors.collectObservations(
        mocked_primary_target.initial_state,
        mocked_primary_target,
        [mocked_primary_target],
    )
    assert len(bad_obs) == 1


def testBuildSigmaObs():
    """To be implemented."""


@patch("resonaate.sensors.sensor_base.getSlantRangeVector")
@patch.multiple(Sensor, __abstractmethods__=set())
def testAttemptObservation(
    slant_range_patch: Mock,
    base_sensor_args: dict,
    mocked_sensing_agent: SensingAgent,
    mocked_primary_target: TargetAgent,
):
    """Test that observations and missed observations are encoded correctly."""
    sensor = Sensor(**base_sensor_args)
    # Requires self.host.eci_state to be set
    sensor.host = mocked_sensing_agent
    sensor.host.eci_state = np.array((6378.0, 0.0, 0.0, 0.0, 0.0, 0.0))
    sensor.host.julian_date_epoch = JulianDate(2459569.75)
    sensor.field_of_view = ConicFoV(cone_angle=np.deg2rad(45.0))

    slant_range_patch.return_value = np.array((1422, 0.0, 0.0, 0.0, 0.0, 0.0))
    mocked_primary_target.eci_state = np.array((7800.0, 0.0, 0.0, 0.0, 0.0, 0.0))

    # Test when target is outside elevation mask
    sensor.el_mask = np.deg2rad(np.array((1.0, 1.1)))
    missed_ob = sensor.attemptObservation(
        mocked_primary_target,
        pointing_sez=np.array((1422, 0.0, 0.0, 0.0, 0.0, 0.0)),
    )
    assert isinstance(missed_ob, MissedObservation)
    assert missed_ob.reason == Explanation.ELEVATION_MASK.value

    # Test when target is inside elevation mask
    sensor.el_mask = np.deg2rad(np.array((-90.0, 89.0)))
    ob = sensor.attemptObservation(
        mocked_primary_target,
        pointing_sez=np.array((1422, 0.0, 0.0, 0.0, 0.0, 0.0)),
    )
    assert isinstance(ob, Observation)

    # Test when target is outside the field of view
    with patch.object(sensor.field_of_view, "inFieldOfView", return_value=False):
        missed_ob = sensor.attemptObservation(
            mocked_primary_target,
            pointing_sez=np.array((1422, 0.0, 0.0, 0.0, 0.0, 0.0)),
        )
        assert isinstance(missed_ob, MissedObservation)
        assert missed_ob.reason == Explanation.FIELD_OF_VIEW.value

    # Test when target is not visible
    mock_explanation = MagicMock()
    mock_explanation.value = "mock_explanation"
    with patch.object(sensor, "isVisible", return_value=(False, mock_explanation)):
        missed_ob = sensor.attemptObservation(
            mocked_primary_target,
            pointing_sez=np.array((1422, 0.0, 0.0, 0.0, 0.0, 0.0)),
        )
        assert isinstance(missed_ob, MissedObservation)
        assert missed_ob.reason == mock_explanation.value


@patch.multiple(Sensor, __abstractmethods__=set())
def testDeltaBoresight(base_sensor_args: dict):
    """Test that angular separation from boresight is calculated correctly."""
    sensor = Sensor(**base_sensor_args)
    sensor.boresight = np.array((1.0, 0.0, 0.0))

    sez_position = np.array((0.0, 1.0, 0.0))
    assert sensor.deltaBoresight(sez_position) == np.pi / 2

    sez_position = np.array((0.0, 0.0, -1.0))
    assert sensor.deltaBoresight(sez_position) == np.pi / 2

    sez_position = np.array((-1.0, 0.0, 0.0))
    assert sensor.deltaBoresight(sez_position) == np.pi

    sez_position = np.array((1.0, 0.0, 0.0))
    assert sensor.deltaBoresight(sez_position) == 0.0


def testAttemptNoisyObservation():
    """To be implemented."""
