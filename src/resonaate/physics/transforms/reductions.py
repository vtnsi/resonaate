"""Defines the IAU-76/FK5 Reduction Model.

This module handles logic pertaining to the FK5 Reduction for properly rotating ECEF (ITRF)
to/from ECI (GCRF). However, this module may later hold multiple forms of this reduction.
"""

from __future__ import annotations

# Standard Library Imports
from contextlib import suppress
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import TYPE_CHECKING

# Third Party Imports
from numpy import array_equal, asarray, cos, dot, fmod, matmul, sin

# Local Imports
# Package Imports
from ...parallel.key_value_store import KeyValueStore
from ...parallel.key_value_store.cache_transactions import (
    CacheMissError,
    UninitializedCacheError,
    ValueAlreadySetError,
)
from .. import constants as const
from ..maths import rot1, rot2, rot3
from ..time.conversions import dayOfYear, greenwichApparentTime, utc2TerrestrialTime
from .eops import EarthOrientationParameter, getEarthOrientationParameters
from .nutation import get1980NutationSeries

if TYPE_CHECKING:
    # Third Party Imports
    from numpy import ndarray


@dataclass
class ReductionParams:
    """A set of FK5 transformation data."""

    rot_pn: ndarray
    """Rotation matrix to go from TOD -> MOD -> ECI.

    TOD -> MOD [N]: Nutation matrix of nutation (IAU 1980 model).
    MOD -> ECI [P]: Precession matrix from from J2000 (IAU 1976 model).
    """

    rot_pnr: ndarray
    """Rotation matrix to go from PEF -> TOD -> MOD -> ECI.

    PEF -> TOD [R]: Rotation matrix of Greenwich Apparent Sidereal Time (IAU res 1982).
    TOD -> MOD [N]: Nutation matrix of nutation (IAU 1980 model).
    MOD -> ECI [P]: Precession matrix from from J2000 (IAU 1976 model).
    """

    rot_rnp: ndarray
    """Rotation matrix to go from ECI -> MOD -> TOD -> PEF.

    Transpose of :attr:`.rot_pnr`, see for more details.
    """

    rot_w: type
    """Complete polar motion matrix form.

    ECEF -> PEF [W]: Corrects for polar motion based on empirical EOP data.
    """

    rot_wt: ndarray
    """Transpose of :attr:`.rot_w`."""

    lod: float
    """Instantaneous rate of change of UT1 w.r.t UTC (seconds)."""

    eq_equinox: float
    """Equation of Equinoxes"""

    dut1: float
    """Difference between UTC and UT1 (seconds)."""

    date_time: datetime
    """The ``datetime`` object that these reduction parameters are valid for."""

    def __eq__(self, value: ReductionParams) -> bool:
        """Define equality conditions between two instances of :class:`.ReductionParams`."""
        return all(
            [
                array_equal(self.rot_pn, value.rot_pn),
                array_equal(self.rot_pnr, value.rot_pnr),
                array_equal(self.rot_rnp, value.rot_rnp),
                array_equal(self.rot_w, value.rot_w),
                array_equal(self.rot_wt, value.rot_wt),
                self.lod == value.lod,
                self.eq_equinox == value.eq_equinox,
                self.dut1 == value.dut1,
                self.date_time == value.date_time,
            ],
        )

    @classmethod
    def build(cls, utc_date: datetime, eops: EarthOrientationParameter = None) -> ReductionParams:
        """Factory method populating reduction parameters based on specified `date_time`.

        Args:
            utc_date (``datetime``): Date and time to populate reduction parameters for (in UTC).
            eops (:class:`.EarthOrientationParameter`, optional): Specific EOPs to use rather
                than lookup; useful for tests.

        Returns:
            :class:`.ReductionParams`: Populated reduction parameters based on specified `date_time`.
        """
        if not isinstance(utc_date, datetime):
            err = f"Building reduction parameters expects datetime, not {type(utc_date)}"
            raise TypeError(err)

        if not eops:
            eops = getEarthOrientationParameters(utc_date.date())

        polar_motion = PolarMotion(eops.x_p, eops.y_p)
        prec_nut = PrecessionNutation(
            utc_date,
            eops.delta_atomic_time,
            eops.d_delta_psi,
            eops.d_delta_eps,
        )
        rot_pef2tod = getRotR(utc_date, eops.delta_ut1, prec_nut.eq_equinox)
        rot_pnr = matmul(prec_nut.rot_pn, rot_pef2tod)

        return cls(
            rot_pn=prec_nut.rot_pn,
            rot_pnr=rot_pnr,
            rot_rnp=rot_pnr.T,
            rot_w=polar_motion.rot_w,
            rot_wt=polar_motion.rot_w.T,
            lod=eops.length_of_day,
            eq_equinox=prec_nut.eq_equinox,
            dut1=eops.delta_ut1,
            date_time=utc_date,
        )


def getRotR(utc_date: datetime, delta_ut1: float, eq_equinox: float) -> ndarray:
    """Rotation matrix to go from Pseudo-Earth Fixed (PEF) to True Of Date (TOD) inertial frame.

    Args:
        utc_date (datetime): Date and time to generate the rotation matrix for (in UTC).
        delta_ut1 (float): Difference between UTC and UT1 (seconds).
        eq_equinox (float): Equation of Equinoxes.

    Returns:
        ndarray: Rotation matrix to go from Pseudo-Earth Fixed (PEF) to True Of Date (TOD) inertial
            frame.
    """
    seconds = utc_date.second + utc_date.microsecond / 1e6
    elapsed_days = (
        dayOfYear(
            utc_date.year,
            utc_date.month,
            utc_date.day,
            utc_date.hour,
            utc_date.minute,
            seconds + delta_ut1,
        )
        - 1
    )
    # Find Greenwich apparent sidereal time. [radians]
    greenwich_apparent_sidereal_time = greenwichApparentTime(
        utc_date.year,
        elapsed_days,
        eq_equinox,
    )

    return rot3(-1.0 * greenwich_apparent_sidereal_time)


class PolarMotion:
    """Object encapsulating values associated with the polar motion of the Earth.

    Attributes:
        rot_w (ndarray): Rotation matrix to go from ECEF to Pseudo-Earth Fixed (PEF).
    """

    def __init__(self, x_p: float, y_p: float):
        """Construct rotation matrix based on specified `x_p` and `y_p`.

        Args:
            x_p (float): Polar motion x coordinate (radians).
            y_p (float): Polar motion y coordinate (radians).
        """
        # Polar motion - Vallado 4th Ed. Eq 3-77 (full) & Eq 3-78 (simplified)
        c_x, s_x = cos(x_p), sin(x_p)
        c_y, s_y = cos(y_p), sin(y_p)

        # Complete polar motion matrix form
        self.rot_w = asarray(
            [
                [c_x, 0, -s_x],
                [s_x * s_y, c_y, c_x * s_y],
                [s_x * c_y, -s_y, c_x * c_y],
            ],
        )


class PrecessionNutation:
    """Object encapsulating values associated with the precession and nutation of the Earth.

    Attributes:
        zeta (float): Precession angle zeta.
        theta (float): Precession angle theta.
        z_p (float): Precession angle "z_p".
        delta_psi (float): Delta psi nutation parameter.
        true_eps (float): True obliquity of the ecliptic.
        mean_eps (float): Mean obliquity of the ecliptic.
        eq_equinox (float): Equation of the Equinoxes.
        rot_tod2mod (ndarray): Rotation matrix to go from True Of Date (TOD) to Mean Of Date
            (MOD). (A.k.a. matrix [N]).
        rot_mod2eci (ndarray): Rotation matrix to go from MOD to ECI. (A.k.a. matrix [P]).
        rot_pn (ndarray): Rotation matrix to go from TOD to ECI (a.k.a matrix [P][N]).
    """

    def __init__(
        self,
        utc_date: datetime,
        delta_atomic_time: float,
        d_delta_psi: float,
        d_delta_eps: float,
    ):
        """Calculate precession and nutation based on current time and corrections.

        Args:
            utc_date (datetime): Date and time to calculate precession and nutation for (in UTC).
            delta_atomic_time (float): Difference in atomic time w.r.t UTC, via leap seconds.
            d_delta_psi (float): EOP correction to psi nutation parameter.
            d_delta_eps (float): EOP correction to epsilon nutation parameter.
        """
        # get terrestrial time, in Julian centuries
        seconds = utc_date.second + utc_date.microsecond / 1e6
        _, ttt = utc2TerrestrialTime(
            utc_date.year,
            utc_date.month,
            utc_date.day,
            utc_date.hour,
            utc_date.minute,
            seconds,
            delta_atomic_time,
        )
        # Get precession angles. Vallado 4th Ed. Eq 3-88
        self.zeta = (2306.2181 * ttt + 0.30188 * ttt**2 + 0.017998 * ttt**3) * const.ARCSEC2RAD
        self.theta = (2004.3109 * ttt - 0.42665 * ttt**2 - 0.041833 * ttt**3) * const.ARCSEC2RAD
        self.z_p = (2306.2181 * ttt + 1.09468 * ttt**2 + 0.018203 * ttt**3) * const.ARCSEC2RAD

        # Get nutation params. Use all 106 terms, and 2 extra terms in the Eq. of Equinoxes. IAU-76/FK5 Reduction.
        # [NOTE] EOP corrections not added when converting to mean J2000 according to Vallado
        #           They are added here because we are rotating to GCRF instead
        self.delta_psi, self.true_eps, self.mean_eps, self.eq_equinox = _getNutationParameters(
            ttt,
            d_delta_psi,
            d_delta_eps,
        )

        self.rot_tod2mod = matmul(
            rot1(-1.0 * self.mean_eps),
            matmul(rot3(self.delta_psi), rot1(self.true_eps)),
        )
        self.rot_mod2eci = matmul(rot3(self.zeta), matmul(rot2(-1.0 * self.theta), rot3(self.z_p)))
        self.rot_pn = matmul(self.rot_mod2eci, self.rot_tod2mod)


def _getNutationParameters(ttt, dd_psi, dd_eps, num=2):
    """Calculate Nutation Parameters for IAU-76/FK5 Reduction.

    References:
        :cite:t:`vallado_2013_astro`, Eqn 3-79, 3-81 - 3-83

    Note: L suffix for Lunar, S suffix for Solar

    Args:
        ttt (``float``): terrestrial time in Julian centuries
        dd_psi (``float``): EOP correction to psi nutation parameter
        dd_eps (``float``): EOP correction to epsilon nutation parameter
        num (int, optional): whether to correct equation of equinox. Defaults to 2.

    Returns:
        ``tuple``: set of parameters defining nutation behavior
    """
    # Convenience variables
    ttt2 = ttt * ttt
    ttt3 = ttt2 * ttt

    # Find the mean obliquity of the ecliptic. Convert to between [0,2pi].
    # Vallado 4th Ed. Eqn 3-81 (could use Eqn 3-68?)
    mean_eps = 23.439291 - 0.0130042 * ttt - 1.64e-7 * ttt2 + 5.04e-7 * ttt3
    mean_eps = fmod(mean_eps, 360) * const.DEG2RAD

    # Determine coefficients for IAU-80 nutation. Convert to between [0,2pi].
    # Vallado 4th Ed. Eqn 3-82 (From Errata)
    mean_anom_l = (
        134.96298139 + (1325 * 360 + 198.8673981) * ttt + 0.0086972 * ttt2 + 1.78e-5 * ttt3
    )
    mean_anom_s = 357.52772333 + (99 * 360 + 359.0503400) * ttt - 0.0001603 * ttt2 - 3.3e-6 * ttt3
    mean_arg_lat_l = (
        93.27191028 + (1342 * 360 + 82.0175381) * ttt - 0.0036825 * ttt2 + 3.1e-6 * ttt3
    )
    elongation_s = (
        297.85036306 + (1236 * 360 + 307.1114800) * ttt - 0.0019142 * ttt2 + 5.3e-6 * ttt3
    )
    raan_l = 125.04452222 - (5 * 360 + 134.1362608) * ttt + 0.0020708 * ttt2 + 2.2e-6 * ttt3
    corrected = (
        fmod([mean_anom_l, mean_anom_s, mean_arg_lat_l, elongation_s, raan_l], 360) * const.DEG2RAD
    )

    # Coefficients for longitude & obliquity correction
    rar_80, iar_80 = get1980NutationSeries()

    # Initialize & calculate nutation/obliquity corrections. Convert to between [0,2pi].
    # Vallado 4th Ed Eq 3-83
    temp_val = (
        iar_80[::, 0] * corrected[0]
        + iar_80[::, 1] * corrected[1]
        + iar_80[::, 2] * corrected[2]
        + iar_80[::, 3] * corrected[3]
        + iar_80[::, 4] * corrected[4]
    ).flatten()
    delta_psi = dot((rar_80[::, 0] + rar_80[::, 1] * ttt).flatten(), sin(temp_val))
    delta_eps = dot((rar_80[::, 2] + rar_80[::, 3] * ttt).flatten(), cos(temp_val))
    # Corrections for FK5 - Makes consistent with GCRF.
    delta_psi = fmod(delta_psi, const.TWOPI) + dd_psi
    delta_eps = fmod(delta_eps, const.TWOPI) + dd_eps
    # Get true obliquity of the ecliptic
    true_eps = mean_eps + delta_eps

    # Correction coefficients for equation of equinox (Eq 3-79 Vallado Ed. 4)
    equinox_c1 = 0.00264 * const.ARCSEC2RAD
    equinox_c2 = 0.000063 * const.ARCSEC2RAD
    # Determine the equation of equinoxes.
    eq_equinox = delta_psi * cos(mean_eps)
    # Before Feb 27, 1997 extra terms not used.
    if ((ttt * 36525 + 2451545) > 2450449.5) and (num > 0):
        eq_equinox += equinox_c1 * sin(corrected[4]) + equinox_c2 * sin(2.0 * corrected[4])

    return delta_psi, true_eps, mean_eps, eq_equinox


class FK5Cache(str, Enum):
    """Enumerated constants for names of FK5 caches."""

    POLAR_MOTION: str = "fk5_polar_motion"
    """str: Cache for :class:`.PolarMotion` objects.

    Cache values stored here should be valid for 24 hours (based on EOPs).
    """

    PREC_NUT: str = "fk5_prec_nut"
    """str: Cache for :class:`.PrecessionNutation` objects.

    Cache values stored here should be valid for ... XXX
    """


@dataclass
class CachedReductionParams(ReductionParams):
    """A set of FK5 transformation data that relies on the :class:`.KeyValueStore` cache."""

    @classmethod
    def build(cls, utc_date: datetime, eops: EarthOrientationParameter = None) -> ReductionParams:
        """Factory method populating reduction parameters based on specified `date_time`.

        This method relies on caching parameters in the :class:`.KeyValueStore` for different time
        spans. After extensive analysis, it was found that this methodology is on the order of 8x
        _slower_ than just calculating the FK5 parameters. Therefore, this methodology should not
        be used unless the supporting caching tech is vastly improved.

        Args:
            utc_date (``datetime``): Date and time to populate reduction parameters for (in UTC).
            eops (:class:`.EarthOrientationParameter`, optional): Specific EOPs to use rather
                than lookup; useful for tests.

        Returns:
            :class:`.ReductionParams`: Populated reduction parameters based on specified `date_time`.
        """
        if not isinstance(utc_date, datetime):
            err = f"Building reduction parameters expects datetime, not {type(utc_date)}"
            raise TypeError(err)

        if not eops:
            eops = getEarthOrientationParameters(utc_date.date())

        try:
            polar_motion = KeyValueStore.cacheGrab(
                FK5Cache.POLAR_MOTION,
                utc_date.date().isoformat(),
            )
        except (CacheMissError, UninitializedCacheError) as err:
            if isinstance(err, UninitializedCacheError):
                with suppress(ValueAlreadySetError):  # multiprocess race condition
                    KeyValueStore.initCache(FK5Cache.POLAR_MOTION)

            polar_motion = PolarMotion(eops.x_p, eops.y_p)
            KeyValueStore.cachePut(
                FK5Cache.POLAR_MOTION,
                utc_date.date().isoformat(),
                polar_motion,
            )

        dt_trunc_min = datetime(
            year=utc_date.year,
            month=utc_date.month,
            day=utc_date.day,
            hour=utc_date.hour,
            minute=utc_date.minute,
        )
        try:
            prec_nut = KeyValueStore.cacheGrab(
                FK5Cache.PREC_NUT,
                dt_trunc_min.isoformat(),
            )
        except (CacheMissError, UninitializedCacheError) as err:
            if isinstance(err, UninitializedCacheError):
                with suppress(ValueAlreadySetError):  # multiprocess race condition
                    KeyValueStore.initCache(FK5Cache.PREC_NUT)

            prec_nut = PrecessionNutation(
                (dt_trunc_min + timedelta(seconds=30)),
                eops.delta_atomic_time,
                eops.d_delta_psi,
                eops.d_delta_eps,
            )
            KeyValueStore.cachePut(
                FK5Cache.PREC_NUT,
                dt_trunc_min.isoformat(),
                prec_nut,
            )

        rot_pef2tod = getRotR(utc_date, eops.delta_ut1, prec_nut.eq_equinox)
        rot_pnr = matmul(prec_nut.rot_pn, rot_pef2tod)

        return cls(
            rot_pn=prec_nut.rot_pn,
            rot_pnr=rot_pnr,
            rot_rnp=rot_pnr.T,
            rot_w=polar_motion.rot_w,
            rot_wt=polar_motion.rot_w.T,
            lod=eops.length_of_day,
            eq_equinox=prec_nut.eq_equinox,
            dut1=eops.delta_ut1,
            date_time=utc_date,
        )
