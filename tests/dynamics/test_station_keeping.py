from __future__ import annotations

# Standard Library Imports
from typing import TYPE_CHECKING

# Third Party Imports
import numpy as np
import pytest
from scipy.linalg import norm

# RESONAATE Imports
from resonaate.dynamics.integration_events.station_keeping import (
    KeepGeoEastWest,
    KeepGeoNorthSouth,
    KeepLeoUp,
)
from resonaate.physics import constants as const
from resonaate.physics.bodies import Earth
from resonaate.physics.orbits.elements import ClassicalElements
from resonaate.physics.transforms import methods as transforms
from resonaate.physics.transforms.reductions import ReductionParams

# Local Imports
from .. import TEST_START_DATETIME, TEST_START_JD

# Type Checking Imports
if TYPE_CHECKING:
    # Third Party Imports
    from numpy import ndarray

    # RESONAATE Imports
    from resonaate.dynamics.celestial import Celestial


@pytest.fixture(name="duration")
def getPropagationDuration() -> float:
    """Get the duration of the propagation."""
    return 60.0 * 60.0


@pytest.fixture(name="leo_rso")
def getSatelliteLeo() -> int:
    """Return a LEO satellite RSO number."""
    return 41858


@pytest.fixture(name="leo_eci")
def getStateLeo() -> ndarray:
    """Return a LEO satellite ECI state."""
    return np.asarray(
        [
            6878.038277,
            -33.799030,
            -14.685957,
            0.037408,
            7.612516,
            -0.000253,
        ],
    )


@pytest.fixture(name="geo_rso")
def getSatelliteGeo() -> int:
    """Return a GEO satellite RSO number."""
    return 27414


@pytest.fixture(name="geo_eci")
def getStateGeo() -> ndarray:
    """Return a GEO satellite ECI state."""
    return np.asarray(
        [
            7772.578605391435,
            41451.327150257275,
            -13.013957256406881,
            -3.0166132050756818,
            0.566000461604396,
            0.17125923555827943,
        ],
    )


@pytest.fixture(name="leo_keep_up_sk")
def getLeoKeepUpSK(leo_rso: int, leo_eci: ndarray) -> KeepLeoUp:
    """Return a LEO station keeper object."""
    return KeepLeoUp.fromInitECI(
        rso_id=leo_rso,
        initial_eci=leo_eci,
        julian_date_start=TEST_START_JD,
    )


@pytest.fixture(name="geo_east_west_sk")
def getGeoEastWestSK(geo_rso: int, geo_eci: ndarray) -> KeepGeoEastWest:
    """Return a GEO station keeper object."""
    return KeepGeoEastWest.fromInitECI(
        rso_id=geo_rso,
        initial_eci=geo_eci,
        julian_date_start=TEST_START_JD,
    )


@pytest.fixture(name="geo_north_south_sk")
def getGeoNorthSouthSK(geo_rso: int, geo_eci: ndarray) -> KeepGeoNorthSouth:
    """Return a GEO station keeper object."""
    return KeepGeoNorthSouth.fromInitECI(
        rso_id=geo_rso,
        initial_eci=geo_eci,
        julian_date_start=TEST_START_JD,
    )


def testKeepLeoUpInit(leo_eci: ndarray, leo_keep_up_sk: KeepLeoUp):
    """Validate that the LEO station keeper object can be correctly instantiated."""
    leo_keep_up_sk.reductions = ReductionParams.build(TEST_START_DATETIME)
    assert np.array_equal(leo_keep_up_sk.initial_eci, leo_eci)
    assert leo_keep_up_sk.initial_coe == ClassicalElements.fromECI(leo_eci)
    assert leo_keep_up_sk.ntw_delta_v == 0.0


def testKeepLeoUpInterruptNotRequired(leo_eci: ndarray, leo_keep_up_sk: KeepLeoUp):
    """Validate that the LEO station keeper object doesn't incorrectly require interrupt."""
    leo_keep_up_sk.reductions = ReductionParams.build(TEST_START_DATETIME)
    assert leo_keep_up_sk.interruptRequired(0.0, leo_eci) is False
    assert leo_keep_up_sk(0.0, leo_eci) != 0


def testKeepLeoUpInterruptRequired(leo_eci: ndarray, leo_keep_up_sk: KeepLeoUp):
    """Validate that the LEO station keeper object correctly requires interrupt."""
    leo_keep_up_sk.reductions = ReductionParams.build(TEST_START_DATETIME)
    coe = ClassicalElements.fromECI(leo_eci)
    coe.sma -= KeepLeoUp.ALT_DRIFT_THRESHOLD * 1.01
    coe.semilatus_rectum = coe.sma * (1 - coe.ecc**2)
    coe.period = 2 * const.PI * np.sqrt(coe.sma**3 / Earth.mu)
    new_state = coe.toECI()
    assert leo_keep_up_sk.interruptRequired(0.0, new_state) is True
    assert leo_keep_up_sk(0.0, new_state) == 0


def testKeepLeoUpPropagation(
    leo_eci: ndarray,
    leo_keep_up_sk: KeepLeoUp,
    dynamics: Celestial,
    duration: float,
):
    """Validate that the LEO station keeping maneuver executes when it's supposed to."""
    leo_keep_up_sk.reductions = ReductionParams.build(TEST_START_DATETIME)
    leo_lla = transforms.ecef2lla(transforms.eci2ecef(leo_eci, TEST_START_DATETIME))
    leo_lla[2] -= KeepLeoUp.ALT_DRIFT_THRESHOLD * 1.01
    new_eci = transforms.ecef2eci(transforms.lla2ecef(leo_lla), TEST_START_DATETIME)
    dynamics.propagate(0.0, duration, new_eci, station_keeping=[leo_keep_up_sk])
    assert leo_keep_up_sk.getActivationDetails() != (None, None)


def testGeoEastWestInit(geo_eci: ndarray, geo_east_west_sk: KeepGeoEastWest):
    """Validate that the GEO East-West station keeper object can be correctly instantiated."""
    geo_east_west_sk.reductions = ReductionParams.build(TEST_START_DATETIME)
    assert np.array_equal(geo_east_west_sk.initial_eci, geo_eci)
    assert geo_east_west_sk.initial_coe == ClassicalElements.fromECI(geo_eci)
    assert geo_east_west_sk.ntw_delta_v == 0.0


def testGeoEastWestInterruptNotRequired(geo_eci: ndarray, geo_east_west_sk: KeepGeoEastWest):
    """Validate that the GEO East-West station keeper object doesn't incorrectly require interrupt."""
    geo_east_west_sk.reductions = ReductionParams.build(TEST_START_DATETIME)
    assert geo_east_west_sk.interruptRequired(0.0, geo_eci) is False
    assert geo_east_west_sk(0.0, geo_eci) != 0


def testGeoEastWestInterruptRequired(geo_eci: ndarray, geo_east_west_sk: KeepGeoEastWest):
    """Validate that the GEO East-West station keeper object correctly requires interrupt."""
    geo_east_west_sk.reductions = ReductionParams.build(TEST_START_DATETIME)
    geo_lla = transforms.ecef2lla(transforms.eci2ecef(geo_eci, TEST_START_DATETIME))
    geo_lla[1] += geo_east_west_sk.LON_DRIFT_THRESHOLD * 1.01
    new_state = transforms.ecef2eci(transforms.lla2ecef(geo_lla), TEST_START_DATETIME)

    assert geo_east_west_sk.interruptRequired(0.0, new_state) is True
    assert geo_east_west_sk(0.0, new_state) == 0


def testGeoEastWestPropagation(
    geo_eci: ndarray,
    geo_east_west_sk: KeepGeoEastWest,
    dynamics: Celestial,
    duration: float,
):
    """Validate that the GEO East-West station keeping maneuver executes when it's supposed to."""
    geo_east_west_sk.reductions = ReductionParams.build(TEST_START_DATETIME)
    geo_lla = transforms.ecef2lla(transforms.eci2ecef(geo_eci, TEST_START_DATETIME))
    geo_lla[1] += geo_east_west_sk.LON_DRIFT_THRESHOLD * 1.01
    new_state = transforms.ecef2eci(transforms.lla2ecef(geo_lla), TEST_START_DATETIME)

    dynamics.propagate(0.0, duration, new_state, station_keeping=[geo_east_west_sk])
    assert geo_east_west_sk.getActivationDetails() != (None, None)


def testGeoNorthSouthInit(geo_eci: ndarray, geo_north_south_sk: KeepGeoNorthSouth):
    """Validate that the GEO North-South station keeper object can be correctly instantiated."""
    geo_north_south_sk.reductions = ReductionParams.build(TEST_START_DATETIME)
    assert np.array_equal(geo_north_south_sk.initial_eci, geo_eci)
    assert geo_north_south_sk.initial_coe == ClassicalElements.fromECI(geo_eci)
    assert geo_north_south_sk.ntw_delta_v == 0.0


def testGeoNorthSouthInterruptNotRequired(geo_eci: ndarray, geo_north_south_sk: KeepGeoNorthSouth):
    """Validate that the GEO North-South station keeper object doesn't incorrectly require interrupt."""
    geo_north_south_sk.reductions = ReductionParams.build(TEST_START_DATETIME)
    geo_north_south_sk.julian_date_start = TEST_START_JD
    assert geo_north_south_sk.interruptRequired(0.0, geo_eci) is False
    assert geo_north_south_sk(0.0, geo_eci) != 0


def testGeoNorthSouthInterruptRequired(geo_eci: ndarray, geo_north_south_sk: KeepGeoNorthSouth):
    """Validate that the GEO North-South station keeper object correctly requires interrupt."""
    geo_north_south_sk.reductions = ReductionParams.build(TEST_START_DATETIME)
    geo_lla = transforms.ecef2lla(transforms.eci2ecef(geo_eci, TEST_START_DATETIME))
    geo_lla[0] += geo_north_south_sk.LAT_DRIFT_THRESHOLD * 1.01
    new_state = transforms.ecef2eci(transforms.lla2ecef(geo_lla), TEST_START_DATETIME)
    assert geo_north_south_sk.interruptRequired(0.0, new_state) is True
    assert geo_north_south_sk(0.0, new_state) == 0
    assert norm(geo_north_south_sk.getStateChange(0, new_state)[3:]) > 0


def testGeoNorthSouthPropagation(
    geo_eci: ndarray,
    geo_north_south_sk: KeepGeoNorthSouth,
    dynamics: Celestial,
    duration: float,
):
    """Validate that the GEO North-South station keeping maneuver executes when it's supposed to."""
    geo_north_south_sk.reductions = ReductionParams.build(TEST_START_DATETIME)
    geo_lla = transforms.ecef2lla(transforms.eci2ecef(geo_eci, TEST_START_DATETIME))
    geo_lla[0] += geo_north_south_sk.LAT_DRIFT_THRESHOLD * 1.2
    new_eci = transforms.ecef2eci(transforms.lla2ecef(geo_lla), TEST_START_DATETIME)
    dynamics.propagate(0.0, duration, new_eci, station_keeping=[geo_north_south_sk])
    assert geo_north_south_sk.getActivationDetails() != (None, None)
