from __future__ import annotations

# Standard Library Imports
import datetime

# Third Party Imports
import numpy as np
import pytest

# RESONAATE Imports
import resonaate.physics.constants as const
from resonaate.physics.time.conversions import utc2TerrestrialTime
from resonaate.physics.time.stardate import JulianDate, julianDateToDatetime
from resonaate.physics.transforms.eops import EarthOrientationParameter, MissingEOP
from resonaate.physics.transforms.reductions import ReductionParams


def testReductionParamsBuild() -> None:
    """Test creation and retrieving of values in KVS."""
    utc = datetime.datetime(2022, 6, 10, 4, 12, 30)

    # Test no KVS started
    reductions = ReductionParams.build(utc)
    assert reductions.date_time == utc

    # Make sure we can build another date without error
    new_utc = utc - datetime.timedelta(days=1)
    reductions = ReductionParams.build(new_utc)
    assert reductions.date_time == new_utc


def testFK5ReductionAlgorithm():
    """Numerically validate reduction algorithm against results from IERS."""
    # Correct values, taken from IERS examples
    correct_tt = 54195.500754444444444
    correct_ut1 = 54195.499999165813831
    correct_np_mat = np.asarray(
        [
            [0.999998403176203, -0.001639032970562, -0.000712190961847],
            [0.001639000942243, 0.999998655799521, -0.000045552846624],
            [0.000712264667137, 0.000044385492226, 0.999999745354454],
        ],
    )
    correct_rnp_mat = np.asarray(
        [
            [0.973104317592265, 0.230363826166883, -0.000703332813776],
            [-0.230363798723533, 0.973104570754697, 0.000120888299841],
            [0.000712264667137, 0.000044385492226, 0.999999745354454],
        ],
    )
    correct_full_mat = np.asarray(
        [
            [0.973104317712772, 0.230363826174782, -0.000703163477127],
            [-0.230363800391868, 0.973104570648022, 0.000118545116892],
            [0.000711560100206, 0.000046626645796, 0.999999745754058],
        ],
    )

    # Given UTC
    year, month, day, hour, minute, second = 2007, 4, 5, 12, 0, 0
    # Given Julian date & Julian date at 0 hrs
    calendar_date = datetime.datetime(year, month, day, hour, minute, second)
    julian_day = JulianDate.getJulianDate(year, month, day, 0, 0, 0)
    # Given Polar motion (arcsec -> rad)
    x_p = 0.0349282 * const.ARCSEC2RAD
    y_p = 0.4833163 * const.ARCSEC2RAD
    # Given UT1-UTC (s)
    dut1 = -0.072073685
    # Given Nut corrections wrt IAU 1976/1980 (mas->rad)
    ddp80 = -55.0655 * const.ARCSEC2RAD / 1000
    dde80 = -6.3580 * const.ARCSEC2RAD / 1000
    # Given delta atomic time (s)
    dat = 33.0

    # Time checks [TODO]: Move this check to conversions unit-test
    _, ttt = utc2TerrestrialTime(year, month, day, hour, minute, second, dat)
    assert np.isclose(ttt * 36525 + 2451545 - 2400000.5, correct_tt)  # places=9
    utc = hour * 3600 + minute * 60 + second
    tut = utc + dut1
    ut1 = julian_day + tut * const.SEC2DAYS
    assert np.isclose(ut1 - 2400000.5, correct_ut1)  # places=9

    # Calculate the required parameters
    lod = 0.00001
    eops = EarthOrientationParameter(
        datetime.date(year, month, day),
        x_p,
        y_p,
        ddp80,
        dde80,
        dut1,
        lod,
        dat,
    )
    # (rot_pn, rot_pnr, rot_rnp, rot_w, rot_wt, eops, gast, eq_equinox)
    params = ReductionParams.build(calendar_date, eops=eops)
    rot_wt = params.rot_wt
    rot_rnp = params.rot_rnp
    rot_np = params.rot_pn.T

    # Implement the full rotation from terrestrial (ITRF) to celestial (GCRF)
    full_mat = np.matmul(rot_wt, rot_rnp)

    # Compare versus results given in document
    assert np.allclose(correct_np_mat, rot_np, atol=1e-10, rtol=1e-9)
    assert np.allclose(correct_rnp_mat, rot_rnp, atol=1e-10, rtol=1e-9)
    assert np.allclose(correct_full_mat, full_mat, atol=1e-10, rtol=1e-9)


def testInvalidJulianDate():
    """Test catching a bad :class:`.JulianDate` objects."""
    # Ridiculous date
    julian_date = JulianDate(3)
    error_msg = r"year [-]*\d+ is out of range"
    with pytest.raises(ValueError, match=error_msg):
        julianDateToDatetime(julian_date)

    # Less ridiculous date, but before range of EOPs
    calendar_date = datetime.datetime(2000, 1, 24, 7, 23, 56, 900000)
    with pytest.raises(MissingEOP):
        ReductionParams.build(calendar_date)

    # Date past range of EOPs
    calendar_date = datetime.datetime(2050, 1, 24, 7, 23, 56, 900000)
    with pytest.raises(MissingEOP):
        ReductionParams.build(calendar_date)

    with pytest.raises(TypeError):
        ReductionParams.build(julian_date)
