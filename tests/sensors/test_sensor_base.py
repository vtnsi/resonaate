# pylint: disable=abstract-class-instantiated
from __future__ import annotations

# Standard Library Imports
from copy import copy, deepcopy
from unittest.mock import Mock, create_autospec, patch

# Third Party Imports
import numpy as np
import pytest

# RESONAATE Imports
from resonaate.agents.sensing_agent import SensingAgent
from resonaate.common.exceptions import ShapeError
from resonaate.physics.time.stardate import ScenarioTime
from resonaate.sensors import FieldOfView
from resonaate.sensors.sensor_base import Sensor


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
        "calculate_fov": True,
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
    sensor_agent.agent_type = "Spacecraft"
    sensor_agent.truth_state = np.array((0.0, 0.0, 0.0, 0.0, 0.0, 0.0))
    return sensor_agent


@patch.multiple(Sensor, __abstractmethods__=set())
def testSensorInit(sensor_args: dict, mocked_sensing_agent: SensingAgent):
    """Test initializing Sensor base class."""
    base_sensor = Sensor(**sensor_args)
    assert base_sensor
    assert np.allclose(base_sensor.az_mask, np.deg2rad(sensor_args["az_mask"]))
    assert np.allclose(base_sensor.el_mask, np.deg2rad(sensor_args["el_mask"]))
    assert np.isclose(base_sensor.aperture_area, np.pi * (sensor_args["diameter"] * 0.5) ** 2)
    assert np.isclose(base_sensor.slew_rate, np.deg2rad(sensor_args["slew_rate"]))
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
    assert base_sensor.measurement_noise.shape == (2,)
    assert all(abs(base_sensor.measurement_noise) > 0.0)

    base_sensor.host = mocked_sensing_agent
    assert base_sensor.host is not None
    assert base_sensor.time_last_ob > 0.0


@patch.multiple(Sensor, __abstractmethods__=set())
def testSensorInitAzElMask(sensor_args: dict):
    """Test edge case values for the az/el mask."""
    sen_args = deepcopy(sensor_args)

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
def testSensorInitAzElMaskBadValues(sensor_args: dict):
    """Test bad values for the az/el mask."""
    value_err_msg = r"\w*Invalid value \[0, 2π] for az_mask\w*"
    sen_args = deepcopy(sensor_args)
    sen_args["az_mask"] = np.array((-181.0, 180.0))
    with pytest.raises(ValueError, match=value_err_msg):
        _ = Sensor(**sen_args)

    sen_args = deepcopy(sensor_args)
    sen_args["az_mask"] = np.array((0.0, 400.0))
    with pytest.raises(ValueError, match=value_err_msg):
        _ = Sensor(**sen_args)

    value_err_msg = r"\w*Invalid value \[-π/2, π/2] for el_mask\w*"
    sen_args = deepcopy(sensor_args)
    sen_args["el_mask"] = np.array((-91.0, 90.0))
    with pytest.raises(ValueError, match=value_err_msg):
        _ = Sensor(**sen_args)

    sen_args = deepcopy(sensor_args)
    sen_args["el_mask"] = np.array((-90.0, 100.0))
    with pytest.raises(ValueError, match=value_err_msg):
        _ = Sensor(**sen_args)


@patch.multiple(Sensor, __abstractmethods__=set())
def testSensorInitAzElMaskTypes(sensor_args: dict):
    """Test bad types for the az/el mask."""
    sen_args = deepcopy(sensor_args)
    sen_args["az_mask"] = np.array((-180.0, 180.0, 0.0))
    with pytest.raises(ShapeError, match=r"\w*Invalid shape for az_mask\w*"):
        _ = Sensor(**sen_args)

    sen_args = deepcopy(sensor_args)
    sen_args["el_mask"] = np.array((-90.0, 90.0, 0.0))
    with pytest.raises(ShapeError, match=r"\w*Invalid shape for el_mask\w*"):
        _ = Sensor(**sen_args)


@patch.multiple(Sensor, __abstractmethods__=set())
def testSensorInitRMatrix(sensor_args: dict):
    """Test good shapes for R matrix."""
    sen_args = deepcopy(sensor_args)
    sen_args["r_matrix"] = np.eye(2)
    _ = Sensor(**sen_args)
    sen_args["r_matrix"] = np.eye(3)
    _ = Sensor(**sen_args)
    sen_args["r_matrix"] = np.eye(4)
    _ = Sensor(**sen_args)
    sen_args["r_matrix"] = np.array((1.0, 1.0))
    _ = Sensor(**sen_args)
    sen_args["r_matrix"] = np.array(((2.0, 1.0, 4.0)))
    _ = Sensor(**sen_args)
    sen_args["r_matrix"] = np.array(((2.0), (1.0), (4.0)))
    _ = Sensor(**sen_args)


@patch.multiple(Sensor, __abstractmethods__=set())
def testSensorInitBadRMatrix(sensor_args: dict):
    """Test bad shapes & value for R matrix."""
    shape_err_msg = r"\w*Invalid shape for r_matrix\w*"
    sen_args = deepcopy(sensor_args)
    sen_args["r_matrix"] = 10.0
    with pytest.raises(AttributeError):
        _ = Sensor(**sen_args)

    sen_args["r_matrix"] = np.array(((2, 3, 0), (4, 5, 7)))
    with pytest.raises(ShapeError, match=shape_err_msg):
        _ = Sensor(**sen_args)

    sen_args["r_matrix"] = np.array(((-5, 0.5), (1, 1)))
    with pytest.raises(ValueError, match=r"\w*non-positive definite r_matrix\w*"):
        _ = Sensor(**sen_args)


@patch.multiple(Sensor, __abstractmethods__=set())
def testGetSensorData(sensor_args: dict, mocked_sensing_agent: SensingAgent):
    """Test retrieve dictionary of sensor data."""
    sensor = Sensor(**sensor_args)
    sensor.host = mocked_sensing_agent

    # Test space sensor types
    expected = {
        "name": mocked_sensing_agent.name,
        "id": mocked_sensing_agent.simulation_id,
        "covariance": sensor_args["r_matrix"].tolist(),
        "slew_rate": np.deg2rad(sensor_args["slew_rate"]),
        "azimuth_range": np.deg2rad(sensor_args["az_mask"]).tolist(),
        "elevation_range": np.deg2rad(sensor_args["el_mask"]).tolist(),
        "efficiency": sensor_args["efficiency"],
        "aperture_area": np.pi * (sensor_args["diameter"] * 0.5) ** 2,
        "sensor_type": "Sensor",
        "exemplar": sensor_args["exemplar"].tolist(),
        "field_of_view": sensor.field_of_view,
    }

    expected_space = deepcopy(expected)
    expected_space.update(
        {
            "host_type": mocked_sensing_agent.agent_type,
            "init_eci": mocked_sensing_agent.truth_state.tolist(),
        }
    )
    assert sensor.getSensorData() == expected_space

    # Test ground sensor types
    ground_sensor_agent = copy(mocked_sensing_agent)
    ground_sensor_agent.agent_type = "GroundFacility"
    ground_sensor_agent.lla_state = np.array((10, 2.5, 0.3))
    expected_ground = deepcopy(expected)
    expected_ground.update(
        {
            "host_type": ground_sensor_agent.agent_type,
            "lat": ground_sensor_agent.lla_state[0],
            "lon": ground_sensor_agent.lla_state[1],
            "alt": ground_sensor_agent.lla_state[2],
        }
    )
    sensor.host = ground_sensor_agent
    assert sensor.getSensorData() == expected_ground


@patch.multiple(Sensor, __abstractmethods__=set())
def testCanSlew(sensor_args: dict, mocked_sensing_agent: SensingAgent):
    """Test whether the sensor can slew to a target or not."""
    sensor = Sensor(**sensor_args)
    sensor.host = mocked_sensing_agent
    sensor.time_last_ob = 0.0

    # Assumes 1 deg/sec slew rate & 60 sec dt
    assert not sensor.canSlew(np.array((1.0, 0.0, 0.0)))
    assert not sensor.canSlew(np.array((0.0, 1.0, 0.0)))
    assert not sensor.canSlew(np.array((0.5, 0.5, 0.5)))
    assert sensor.canSlew(np.array((-0.7, 0.0, 0.7)))
    assert sensor.canSlew(np.array((-0.7, 0.5, 0.7)))
    assert sensor.canSlew(np.array((-0.2, 0.0, 0.7)))


@patch.multiple(Sensor, __abstractmethods__=set())
def testGetMeasurements(sensor_args: dict):
    """Test calling getMeasurement & getNoisyMeasurement."""
    # pylint: disable=invalid-name
    sensor = Sensor(**sensor_args)
    sensor.getMeasurements = Mock()  # pylint: disable=invalid-name
    sensor.getMeasurements.return_value = {
        "measurement_1": 1.0,
        "measurement_2": 20.0,
    }
    _ = sensor.getMeasurements(None, noisy=False)
    sensor.getMeasurements.assert_called_once()
    sensor.getMeasurements.assert_called_with(None, noisy=False)
    sensor.getMeasurements.reset_mock()
    sensor.getNoisyMeasurements(None)
    sensor.getMeasurements.assert_called_once()
    sensor.getMeasurements.assert_called_with(None, noisy=True)


@patch.multiple(Sensor, __abstractmethods__=set())
def testInFOVConic(sensor_args: dict):
    """Test whether a target is in the field of view of the sensor."""
    sensor = Sensor(**sensor_args)
    sensor.field_of_view = create_autospec(spec=FieldOfView, instance=True)
    sensor.field_of_view.fov_shape = "conic"
    sensor.field_of_view.cone_angle = np.pi

    tgt_sez = np.array((1.0, 0.0, 0.0))
    bkg_sez = np.array((0.0, 1.0, 0.0))
    assert sensor.inFOV(tgt_sez, bkg_sez)

    bkg_sez = np.array((0.0, 0.0, 1.0))
    assert sensor.inFOV(tgt_sez, bkg_sez)

    bkg_sez = np.array((-1.0, 0.0, -1.0))
    assert not sensor.inFOV(tgt_sez, bkg_sez)

    sensor.field_of_view.cone_angle = np.pi / 2
    bkg_sez = np.array((0.0, 0.5, 0.0))
    assert not sensor.inFOV(tgt_sez, bkg_sez)


@patch.multiple(Sensor, __abstractmethods__=set())
def testInFOVRegular(sensor_args: dict):
    """Test whether a target is in the field of view of the sensor."""
    sensor = Sensor(**sensor_args)
    sensor.field_of_view = create_autospec(spec=FieldOfView, instance=True)
    sensor.field_of_view.fov_shape = "rectangular"
    sensor.field_of_view.azimuth_angle = np.pi
    sensor.field_of_view.elevation_angle = np.pi

    tgt_sez = np.array((1.0, 0.0, 0.0, 0.0, 0.0, 0.0))
    bkg_sez = np.array((0.0, 1.0, 0.0, 0.0, 0.0, 0.0))
    assert sensor.inFOV(tgt_sez, bkg_sez)

    bkg_sez = np.array((0.0, 1.0, 1.0, 0.0, 0.0, 0.0))
    assert sensor.inFOV(tgt_sez, bkg_sez)

    bkg_sez = np.array((-1.0, 0.0, -1.0, 0.0, 0.0, 0.0))
    assert not sensor.inFOV(tgt_sez, bkg_sez)

    sensor.field_of_view.azimuth_angle = np.pi / 2
    sensor.field_of_view.elevation_angle = np.pi / 2
    bkg_sez = np.array((0.0, 0.5, 0.5, 0.0, 0.0, 0.0))
    assert not sensor.inFOV(tgt_sez, bkg_sez)


@patch.multiple(Sensor, __abstractmethods__=set())
def testInFOVBad(sensor_args: dict):
    """Test a bad FOV shape."""
    sensor = Sensor(**sensor_args)
    sensor.field_of_view = create_autospec(spec=FieldOfView, instance=True)
    sensor.field_of_view.fov_shape = "bad_fov_shape"
    with pytest.raises(ValueError, match=r"Wrong FoV shape\w*"):
        sensor.inFOV(np.array((0.0, 0.0, 0.0)), np.array((0.0, 0.0, 0.0)))


def _dummySlantRange(ecef_sensor: np.ndarray, eci_tgt: np.ndarray) -> np.ndarray:
    """Dummy slant range function; passes through the eci_tgt parameter."""
    # pylint: disable=unused-argument
    return eci_tgt


@patch("resonaate.sensors.sensor_base.getSlantRangeVector", new=_dummySlantRange)
@patch.multiple(Sensor, __abstractmethods__=set())
def testCheckTargetsInView(sensor_args: dict, mocked_sensing_agent: SensingAgent):
    """Checks whether list of targets is in the FOV of the sensor."""
    # pylint: disable=abstract-class-instantiated
    sensor = Sensor(**sensor_args)
    sensor.field_of_view = create_autospec(spec=FieldOfView, instance=True)
    sensor.field_of_view.fov_shape = "conic"
    sensor.field_of_view.cone_angle = np.pi
    # Requires self.host.ecef_state to be set
    sensor.host = mocked_sensing_agent
    sensor.host.ecef_state = np.array((0.0, 0.0, 0.0, 0.0, 0.0, 0.0))

    # Target SEZ position
    tgt_sez = np.array((1.0, 0.0, 0.0, 0.0, 0.0, 0.0))

    # Create mocks for TargetAgent objects with `eci_state`
    agent_1 = Mock()
    agent_2 = Mock()
    agent_3 = Mock()
    agent_4 = Mock()
    agent_1.eci_state = np.array((0.0, 1.0, 0.0, 0.0, 0.0, 0.0))
    agent_2.eci_state = np.array((-1.0, 0.0, -1.0, 0.0, 0.0, 0.0))  # outside FOV
    agent_3.eci_state = np.array((0.0, 1.0, 0.0, 0.0, 0.0, 0.0))
    agent_4.eci_state = np.array((1.0, 0.0, 0.0, 0.0, 0.0, 0.0))

    targets_in_fov = sensor.checkTargetsInView(tgt_sez, [agent_1, agent_2, agent_3, agent_4])
    assert targets_in_fov == [agent_1, agent_3, agent_4]
    targets_in_fov = sensor.checkTargetsInView(tgt_sez, [agent_1, agent_2])
    assert targets_in_fov == [agent_1]
    targets_in_fov = sensor.checkTargetsInView(tgt_sez, [agent_3])
    assert targets_in_fov == [agent_3]
    targets_in_fov = sensor.checkTargetsInView(tgt_sez, [agent_2])
    assert not targets_in_fov


@patch.multiple(Sensor, __abstractmethods__=set())
def testIsVisible(sensor_args: dict, mocked_sensing_agent: SensingAgent):
    """To be implemented."""
    sensor = Sensor(**sensor_args)
    # Requires self.host.eci_state to be set
    sensor.host = mocked_sensing_agent
    sensor.host.eci_state = np.array((6378.0, 0.0, 0.0, 0.0, 0.0, 0.0))

    # Target is visible initially
    tgt_eci_state = np.array((7800.0, 0.0, 0.0, 0.0, 0.0, 0.0))
    sez_state = np.array((1422, 0.0, 0.0, 0.0, 0.0, 0.0))
    assert sensor.isVisible(tgt_eci_state, 10.0, 10.0, sez_state)

    # Test min range with large enough to force failure
    sensor.minimum_range = 1e6
    assert not sensor.isVisible(tgt_eci_state, 10.0, 10.0, sez_state)
    # reasonable min range, but not zero
    sensor.minimum_range = 10.0
    assert sensor.isVisible(tgt_eci_state, 10.0, 10.0, sez_state)
    # min range of None
    sensor.minimum_range = None
    assert sensor.isVisible(tgt_eci_state, 10.0, 10.0, sez_state)
    # min range of zero
    sensor.minimum_range = 0.0
    assert sensor.isVisible(tgt_eci_state, 10.0, 10.0, sez_state)
    # min range reasonable, but not large enough
    sensor.minimum_range = 100.0
    assert sensor.isVisible(tgt_eci_state, 10.0, 10.0, sez_state)

    # Test max range with small enough to force failure
    sensor.maximum_range = 10.0
    assert not sensor.isVisible(tgt_eci_state, 10.0, 10.0, sez_state)
    # reasonable max range, but not infinity
    sensor.maximum_range = 1e6
    assert sensor.isVisible(tgt_eci_state, 10.0, 10.0, sez_state)
    # max range of None
    sensor.maximum_range = None
    assert sensor.isVisible(tgt_eci_state, 10.0, 10.0, sez_state)
    # max range of zero
    sensor.maximum_range = 0.0
    assert not sensor.isVisible(tgt_eci_state, 10.0, 10.0, sez_state)
    # max range of infinity
    sensor.maximum_range = np.inf
    assert sensor.isVisible(tgt_eci_state, 10.0, 10.0, sez_state)

    # Test LOS in view & on opposite side of Earth
    assert sensor.isVisible(tgt_eci_state, 10.0, 10.0, sez_state)
    assert not sensor.isVisible(-tgt_eci_state, 10.0, 10.0, sez_state)

    # Test elevation mask constraint
    # Pass on boundaries
    sez_state = np.array((1422, 0.0, 0.0, 0.0, 0.0, 0.0))  # 0 elevation
    sensor.el_mask = np.deg2rad(np.array((0.0, 90.0)))
    assert sensor.isVisible(tgt_eci_state, 10.0, 10.0, sez_state)
    sez_state = np.array((0.0, 0.0, 1422.0, 0.0, 0.0, 0.0))  # 90 elevation
    assert sensor.isVisible(tgt_eci_state, 10.0, 10.0, sez_state)
    # Fail outside boundaries
    sez_state = np.array((1422, 0.0, 0.0, 0.0, 0.0, 0.0))  # 0 elevation
    sensor.el_mask = np.deg2rad(np.array((1.0, 89.0)))
    assert not sensor.isVisible(tgt_eci_state, 10.0, 10.0, sez_state)
    sez_state = np.array((0.0, 0.0, 1422.0, 0.0, 0.0, 0.0))  # 90 elevation
    assert not sensor.isVisible(tgt_eci_state, 10.0, 10.0, sez_state)

    # Pass in more normal case
    sez_state = np.array((0.0, 800.0, 1422.0, 0.0, 0.0, 0.0))  # 60 elevation
    sensor.el_mask = np.deg2rad(np.array((10.0, 89.9)))
    assert sensor.isVisible(tgt_eci_state, 10.0, 10.0, sez_state)

    # Test azimuth mask constraint
    sensor.el_mask = np.deg2rad(np.array((0.0, 90.0)))
    sensor.az_mask = np.deg2rad(np.array((0.0, 180.0)))
    sez_state = np.array((1422, 0.0, 0.0, 0.0, 0.0, 0.0))  # 180 azimuth
    assert sensor.isVisible(tgt_eci_state, 10.0, 10.0, sez_state)
    sez_state = np.array((-1422, 0.0, 0.0, 0.0, 0.0, 0.0))  # 0 azimuth
    assert sensor.isVisible(tgt_eci_state, 10.0, 10.0, sez_state)
    sez_state = np.array((-1422, 800.0, 0.0, 0.0, 0.0, 0.0))  # 30 azimuth
    assert sensor.isVisible(tgt_eci_state, 10.0, 10.0, sez_state)

    sensor.az_mask = np.deg2rad(np.array((10.0, 170.0)))
    sez_state = np.array((1422, 0.0, 0.0, 0.0, 0.0, 0.0))  # 180 azimuth
    assert not sensor.isVisible(tgt_eci_state, 10.0, 10.0, sez_state)
    sez_state = np.array((-1422, 0.0, 0.0, 0.0, 0.0, 0.0))  # 0 azimuth
    assert not sensor.isVisible(tgt_eci_state, 10.0, 10.0, sez_state)
    sez_state = np.array((-1422, 800.0, 0.0, 0.0, 0.0, 0.0))  # 30 azimuth
    assert sensor.isVisible(tgt_eci_state, 10.0, 10.0, sez_state)

    # Test azimuth mask constraint with flipped mask
    sensor.az_mask = np.deg2rad(np.array((180.0, 0.0)))
    sez_state = np.array((1422, 0.0, 0.0, 0.0, 0.0, 0.0))  # 180 azimuth
    assert sensor.isVisible(tgt_eci_state, 10.0, 10.0, sez_state)
    sez_state = np.array((-1422, 0.0, 0.0, 0.0, 0.0, 0.0))  # 0 azimuth
    assert sensor.isVisible(tgt_eci_state, 10.0, 10.0, sez_state)
    sez_state = np.array((-1422, -800.0, 0.0, 0.0, 0.0, 0.0))  # 330 azimuth
    assert sensor.isVisible(tgt_eci_state, 10.0, 10.0, sez_state)

    sensor.az_mask = np.deg2rad(np.array((190.0, 350.0)))
    sez_state = np.array((1422, 0.0, 0.0, 0.0, 0.0, 0.0))  # 180 azimuth
    assert not sensor.isVisible(tgt_eci_state, 10.0, 10.0, sez_state)
    sez_state = np.array((-1422, 0.0, 0.0, 0.0, 0.0, 0.0))  # 0 azimuth
    assert not sensor.isVisible(tgt_eci_state, 10.0, 10.0, sez_state)
    sez_state = np.array((-1422, -800.0, 0.0, 0.0, 0.0, 0.0))  # 330 azimuth
    assert sensor.isVisible(tgt_eci_state, 10.0, 10.0, sez_state)


def testCollectObservations():
    """To be implemented."""


def testBuildSigmaObs():
    """To be implemented."""


def testMakeObservation():
    """To be implemented."""


def testMakeNoisyObservation():
    """To be implemented."""
