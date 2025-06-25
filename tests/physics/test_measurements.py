from __future__ import annotations

# Standard Library Imports
import datetime
from itertools import permutations
from typing import TYPE_CHECKING
from unittest.mock import patch

# Third Party Imports
import numpy as np
import pytest

# RESONAATE Imports
import resonaate.physics.constants as const
from resonaate.common.exceptions import ShapeError
from resonaate.data.observation import Observation
from resonaate.physics.measurements import (
    MEASUREMENT_TYPE_MAP,
    Azimuth,
    Elevation,
    IsAngle,
    Measurement,
    MeasurementType,
    Range,
    RangeRate,
    getAzimuth,
    getAzimuthRate,
    getElevation,
    getElevationRate,
    getRange,
    getRangeRate,
)
from resonaate.physics.transforms.eops import (
    EarthOrientationParameter,
    setEarthOrientationParameters,
)
from resonaate.physics.transforms.methods import ecef2eci, getSlantRangeVector, lla2ecef, sez2eci

if TYPE_CHECKING:
    # Standard Library Imports
    from unittest.mock import MagicMock

# Type Checking Imports
if TYPE_CHECKING:
    # Third Party Imports
    from numpy import ndarray

# Vallado example 4-1 (pg. 273), second part
ECI: ndarray = np.array(
    [5036.736529, -10806.660797, -4534.633784, 2.6843855, -5.7595920, -2.4168093],
)
TRUE_RNG: float = 11710.812
TRUE_AZ: float = np.radians(210.8777747)
TRUE_EL: float = np.radians(-5.9409535)
TRUE_RNG_RT: float = 6.0842826
TRUE_AZ_RT: float = np.radians(0.00384011466)
TRUE_EL_RT: float = np.radians(0.01495847759)

# Vallado example 4-1
LLA: ndarray = np.array([np.radians(39.007), np.radians(-104.883), 2.19456])
CALENDAR_DATE: datetime.datetime = datetime.datetime(1994, 5, 14, 13, 11, 20, 598560)

# From celestrak.com for May 14, 1994
# 1994 05 14 49486  0.189443  0.306064 -0.1279402  0.0021743 -0.016163 -0.008660  0.000187  0.000039  28
EOP: EarthOrientationParameter = EarthOrientationParameter(
    datetime.date(1994, 5, 14),
    0,
    0,
    -0.016163 * const.ARCSEC2RAD,
    -0.008660 * const.ARCSEC2RAD,
    0,
    0.0021743,
    28,
)


@pytest.fixture(name="sez_state")
def convertToSEZ() -> ndarray:
    """Fixture to get properly converted SEZ observation vector."""
    setEarthOrientationParameters(CALENDAR_DATE, EOP)
    return getSlantRangeVector(ecef2eci(lla2ecef(LLA), CALENDAR_DATE), ECI, CALENDAR_DATE)


def testMeasurements(sez_state: ndarray):
    """Test measurements for az, el, range & their rates."""
    assert np.isclose(TRUE_AZ, getAzimuth(sez_state))
    assert np.isclose(TRUE_EL, getElevation(sez_state))
    assert np.isclose(TRUE_RNG, getRange(sez_state))
    assert np.isclose(TRUE_AZ_RT, getAzimuthRate(sez_state))
    assert np.isclose(TRUE_EL_RT, getElevationRate(sez_state))
    assert np.isclose(TRUE_RNG_RT, getRangeRate(sez_state))


TEST_SEZ_STATE = np.array(
    [
        -1.93819744e03,
        -2.38779276e03,
        3.11058441e02,
        -1.76725463e00,
        6.81911631e00,
        1.95015349e00,
    ],
)
TEST_SEN_LLA = np.array((0.4, -1.2, 0.4))
TEST_DATETIME = datetime.datetime(2021, 6, 14, 5, 8, 22)
TEST_SEN_ECI = ecef2eci(lla2ecef(TEST_SEN_LLA), TEST_DATETIME)
TEST_TGT_ECI = (
    sez2eci(TEST_SEZ_STATE, TEST_SEN_LLA[0], TEST_SEN_LLA[1], TEST_DATETIME) + TEST_SEN_ECI
)


@patch("resonaate.physics.measurements.getRange")
def testRange(mocked_range_func: MagicMock) -> None:
    """Test range measurement type."""
    range_meas = Range()
    assert range_meas.LABEL in Observation.MUTABLE_COLUMN_NAMES
    assert isinstance(range_meas.is_angular, IsAngle)
    range_meas.calculate(TEST_SEN_ECI, TEST_TGT_ECI, TEST_DATETIME)
    mocked_range_func.assert_called_once()


@patch("resonaate.physics.measurements.getRangeRate")
def testRangeRate(mocked_range_rate_func: MagicMock):
    """Test range rate measurement type."""
    range_rate_meas = RangeRate()
    assert range_rate_meas.LABEL in Observation.MUTABLE_COLUMN_NAMES
    assert isinstance(range_rate_meas.is_angular, IsAngle)
    range_rate_meas.calculate(TEST_SEN_ECI, TEST_TGT_ECI, TEST_DATETIME)
    mocked_range_rate_func.assert_called_once()


@patch("resonaate.physics.measurements.getAzimuth")
def testAzimuth(mocked_azimuth_func: MagicMock):
    """Test azimuth measurement type."""
    azimuth_meas = Azimuth()
    assert azimuth_meas.LABEL in Observation.MUTABLE_COLUMN_NAMES
    assert isinstance(azimuth_meas.is_angular, IsAngle)
    azimuth_meas.calculate(TEST_SEN_ECI, TEST_TGT_ECI, TEST_DATETIME)
    mocked_azimuth_func.assert_called_once()


@patch("resonaate.physics.measurements.getElevation")
def testElevation(mocked_elevation_func: MagicMock):
    """Test elevation measurement type."""
    elevation_meas = Elevation()
    assert elevation_meas.LABEL in Observation.MUTABLE_COLUMN_NAMES
    assert isinstance(elevation_meas.is_angular, IsAngle)
    elevation_meas.calculate(TEST_SEN_ECI, TEST_TGT_ECI, TEST_DATETIME)
    mocked_elevation_func.assert_called_once()


def testMeasurementConstructor() -> None:
    """Test the main constructor for Measurement class."""
    meas_types = (Range(), RangeRate(), Elevation(), Azimuth())
    r_matrix = np.eye(len(meas_types))
    measurement = Measurement(meas_types, r_matrix)
    assert set(measurement._measurements) == set(meas_types)
    assert measurement.angular_values[0] == IsAngle.NOT_ANGLE
    assert measurement.angular_values[1] == IsAngle.NOT_ANGLE
    assert measurement.angular_values[2] == IsAngle.ANGLE_NEG_PI_PI
    assert measurement.angular_values[3] == IsAngle.ANGLE_0_2PI
    assert measurement.labels == [meas_type.LABEL for meas_type in meas_types]
    assert measurement.dim == len(meas_types)

    for meas_type in measurement._measurements:
        assert meas_type.LABEL in measurement.labels
        assert isinstance(meas_type, MeasurementType)


@pytest.mark.parametrize("meas_types", permutations(MEASUREMENT_TYPE_MAP.keys(), 2))
def testMeasurementAltConstructor(meas_types: tuple[str]) -> None:
    """Test the alternative constructor for Measurement class."""
    r_matrix = np.eye(len(meas_types))
    measurement = Measurement.fromMeasurementLabels(meas_types, r_matrix)
    assert set(measurement.labels) == set(meas_types)
    assert measurement.dim == len(meas_types)

    for idx, meas_type in enumerate(measurement._measurements):
        assert (
            measurement.angular_values[idx] == MEASUREMENT_TYPE_MAP[meas_type.LABEL]().is_angular
        )
        assert meas_type.LABEL in measurement.labels
        assert isinstance(meas_type, MeasurementType)


@pytest.fixture(name="measurement")
def getBaseMeasurement() -> Measurement:
    """Create a Measurement with basic params."""
    meas_types = ["azimuth_rad", "elevation_rad"]
    r_matrix = np.eye(len(meas_types)) * 1e-4
    return Measurement.fromMeasurementLabels(meas_types, r_matrix)


def testRMatrix() -> None:
    """Tests proper and improper r_matrix arguments."""
    meas_types = ["azimuth_rad", "elevation_rad"]
    n_dim = len(meas_types)

    # Good R matrices
    r_matrix = np.eye(n_dim)
    measurement = Measurement.fromMeasurementLabels(meas_types, r_matrix)
    assert measurement.r_matrix.shape == (n_dim, n_dim)
    assert not np.allclose(measurement._sqrt_noise_covar, np.zeros(n_dim))

    r_matrix = np.ones((n_dim,))
    measurement = Measurement.fromMeasurementLabels(meas_types, r_matrix)
    assert measurement.r_matrix.shape == (n_dim, n_dim)
    assert not np.allclose(measurement._sqrt_noise_covar, np.zeros(n_dim))

    # Bad R matrix values (negative definite, zero)
    r_matrix = -1.0 * np.eye(n_dim)
    error_msg = r"Measurement: non-positive definite r_matrix: .*"
    with pytest.raises(ValueError, match=error_msg):
        _ = Measurement.fromMeasurementLabels(meas_types, r_matrix)

    r_matrix = np.zeros(n_dim)
    with pytest.raises(ValueError, match=error_msg):
        _ = Measurement.fromMeasurementLabels(meas_types, r_matrix)

    # Bad R matrix shapes (not 1-dim or square, not len of meas types)
    r_matrix = np.ones((n_dim, 3))
    error_msg = r"Measurement: Invalid shape for r_matrix: .*"
    with pytest.raises(ShapeError, match=error_msg):
        _ = Measurement.fromMeasurementLabels(meas_types, r_matrix)

    r_matrix = np.ones((n_dim, 1))
    with pytest.raises(ShapeError, match=error_msg):
        _ = Measurement.fromMeasurementLabels(meas_types, r_matrix)

    r_matrix = np.ones(n_dim + 1)
    error_msg = r"Measurement: Shape for r_matrix doesn't match measurement length: .*"
    with pytest.raises(ShapeError, match=error_msg):
        _ = Measurement.fromMeasurementLabels(meas_types, r_matrix)

    r_matrix = np.eye(n_dim + 1)
    with pytest.raises(ShapeError, match=error_msg):
        _ = Measurement.fromMeasurementLabels(meas_types, r_matrix)


def testNoise(measurement: Measurement) -> None:
    """Tests generating noise vectors."""
    noise = measurement.noise
    assert noise.shape == (len(measurement.labels),)
    assert noise.shape[0] == measurement.r_matrix.shape[0]
    assert not np.allclose(noise, np.zeros_like(noise))
    assert not np.allclose(noise, measurement.noise)


def testCalculateMeasurement(measurement: Measurement) -> None:
    """Tests calculating normal and noisy measurement vectors."""
    norm_meas_vector = measurement.calculateMeasurement(
        TEST_SEN_ECI,
        TEST_TGT_ECI,
        TEST_DATETIME,
        noisy=False,
    )
    noisy_meas_vector = measurement.calculateNoisyMeasurement(
        TEST_SEN_ECI,
        TEST_TGT_ECI,
        TEST_DATETIME,
    )
    assert norm_meas_vector.keys() == noisy_meas_vector.keys()
    for meas_type, noisy_val in noisy_meas_vector.items():
        assert noisy_val != norm_meas_vector[meas_type]
        assert (noisy_val - norm_meas_vector[meas_type]) <= 1.0
