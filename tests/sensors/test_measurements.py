from __future__ import annotations

# Standard Library Imports
import datetime
from typing import TYPE_CHECKING

# Third Party Imports
import numpy as np
import pytest

# RESONAATE Imports
import resonaate.physics.constants as const
from resonaate.physics.time.stardate import JulianDate
from resonaate.physics.transforms.eops import EarthOrientationParameter
from resonaate.physics.transforms.methods import getSlantRangeVector, lla2ecef
from resonaate.physics.transforms.reductions import updateReductionParameters
from resonaate.sensors.measurements import (
    getAzimuth,
    getAzimuthRate,
    getElevation,
    getElevationRate,
    getRange,
    getRangeRate,
)

# Type Checking Imports
if TYPE_CHECKING:
    # Third Party Imports
    from numpy import ndarray

# Vallado example 4-1 (pg. 273), second part
ECI: ndarray = np.asarray(
    [5036.736529, -10806.660797, -4534.633784, 2.6843855, -5.7595920, -2.4168093]
)
TRUE_RNG: float = 11710.812
TRUE_AZ: float = np.radians(210.8777747)
TRUE_EL: float = np.radians(-5.9409535)
TRUE_RNG_RT: float = 6.0842826
TRUE_AZ_RT: float = np.radians(0.00384011466)
TRUE_EL_RT: float = np.radians(0.01495847759)

# Vallado example 4-1
LLA: ndarray = np.asarray([np.radians(39.007), np.radians(-104.883), 2.19456])
JULIAN_DATE: JulianDate = JulianDate.getJulianDate(1994, 5, 14, 13, 11, 20.59856)

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
def convertToSEZ(teardown_kvs) -> ndarray:
    """Fixture to get properly converted SEZ observation vector."""
    # pylint: disable=unused-argument
    updateReductionParameters(JULIAN_DATE, eops=EOP)
    return getSlantRangeVector(lla2ecef(LLA), ECI)


def testMeasurements(sez_state: ndarray):
    """Test measurements for az, el, range & their rates."""
    assert np.isclose(TRUE_AZ, getAzimuth(sez_state))
    assert np.isclose(TRUE_EL, getElevation(sez_state))
    assert np.isclose(TRUE_RNG, getRange(sez_state))
    assert np.isclose(TRUE_AZ_RT, getAzimuthRate(sez_state))
    assert np.isclose(TRUE_EL_RT, getElevationRate(sez_state))
    assert np.isclose(TRUE_RNG_RT, getRangeRate(sez_state))
