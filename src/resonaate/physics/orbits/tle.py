#!/usr/bin/python

"""Contains implementation of the TLE parser."""

# Standard Library Imports
from datetime import datetime
from functools import cached_property
from math import pi
from typing import TYPE_CHECKING

# Third Party Imports
from numpy import array, asarray, concatenate, cross, matmul, ndarray
from sgp4.earth_gravity import wgs72
from sgp4.io import twoline2rv

# Local Imports
from ...scenario.config.state_config import COEStateConfig, ECIStateConfig
from ..bodies.earth import Earth
from ..maths import rot3
from ..time.conversions import greenwichMeanTime
from ..time.stardate import JulianDate, datetimeToJulianDate, getCalendarDate, julianDateToDatetime
from ..transforms.methods import ecef2eci
from ..transforms.reductions import getReductionParameters, updateReductionParameters
from .anomaly import meanAnom2TrueAnom
from .conversions import OrbitalElementTuple, eci2coe

if TYPE_CHECKING:
    # Third Party Imports
    from sgp4.model import Satellite


# TODO: Move references to these constants a place in RESONAATE where they actually live.

G: float = 6.67430 * 10**-11
"""``float``: Gravitational constant in N*m^2*kg^-2."""

M_earth: float = 5.972 * 10**24
"""``float``: Mass of the Earth in kg."""


def teme2ecef(x_teme: ndarray, julian_date_start: JulianDate, reduction: dict) -> ndarray:
    """Convert an SGP4 output state vector (TEME) into an ECEF state vector.

    Args:
        x_teme (``ndarray``): 6x1 TEME state vector (km; km/sec)
        julian_date_start (``JulianDate``): start julian date
        reduction (``dict``): Resonaate reduction parameters. Usually retrieved by calling ``resonaate.physics.transforms.reductions.getReductionParameters()``.

    Returns:
        ``ndarray``: 6x1 ECEF state vector (km; km/sec)
    """
    rot_pef_2_teme = rot3(-1.0 * greenwichMeanTime(julian_date_start))
    rot_teme_2_pef = rot_pef_2_teme.T

    r_pef = matmul(rot_teme_2_pef, x_teme[0:3])
    r_ecef = matmul(reduction["rot_wt"], r_pef)

    om_earth = array([0, 0, Earth.spin_rate * (1 - reduction["lod"] / 86400.0)])

    v_pef = matmul(rot_teme_2_pef, x_teme[3:6]) - cross(om_earth, r_pef)
    v_ecef = matmul(reduction["rot_wt"], v_pef)

    return concatenate((r_ecef, v_ecef), axis=None)


class _BaseTLE:
    """Basic representation of TLE Information."""

    def __init__(self, data: str) -> None:
        """Initializes the object.

        Args:
            data (str): 2 or 3 line TLE string.
        """
        self._data: str = data
        self._lines: list[str] = self._data.split("\n")

        assert len(self._lines) in {  # noqa: S101
            2,
            3,
        }, "Invalid number of lines. TLE requires 2 or 3 lines."
        self._has_title_line: bool = {2: False, 3: True}[len(self._lines)]

        self._title_line: str = ""
        self._line_1: str = self._lines[0]
        self._line_2: str = self._lines[1]
        if self._has_title_line:
            self._title_line = self._lines[0]
            self._line_1 = self._lines[1]
            self._line_2 = self._lines[2]

    @cached_property
    def name(self) -> str:
        """``str | None``: The name of the satellite. Returns '' if no title line is present in the TLE."""
        if not self._has_title_line:
            return ""
        return self._title_line

    @cached_property
    def catalogNumber(self) -> int:
        """``int``: The Sattelite Catalog Number."""
        return int(self._line_1[2:7])

    @cached_property
    def launchYear(self) -> int:
        """``int``: The last two digits of the launch year."""
        return int(self._line_1[9:11])

    @cached_property
    def launchNumber(self) -> int:
        """``int``: The launch number of that year."""
        return int(self._line_1[11:14])

    @cached_property
    def pieceOfLaunch(self) -> str:
        """``str``: Alphabetical launch piece (A for first item in launch, B for second, and so on...)."""
        return self._line_1[14:17]

    @cached_property
    def epoch(self) -> JulianDate:
        """``JulianDate``: The Epoch."""
        year: int = int(self._line_1[18:20])
        if year > 50:
            year += 1900
        elif year <= 50:
            year += 2000
        day: float = float(self._line_1[20:32])

        # Get the initial julian date value at new years of the start year, then add the day offset to it.
        epoch: JulianDate = datetimeToJulianDate(datetime(year, 1, 1))
        epoch += day

        return JulianDate(epoch)

    @cached_property
    def inclination(self) -> float:
        """``float``: Inclination of the orbit in degrees. Note that this is the mean value, not the true COE."""
        return float(self._line_2[8:16])

    @cached_property
    def rightAscension(self) -> float:
        """``float``: Right ascension of the ascending node in degrees. Note that this is the mean value, not the true COE."""
        return float(self._line_2[17:25])

    @cached_property
    def eccentricity(self) -> float:
        """``float``: Orbit eccentricity. Note that this is the mean value, not the true COE."""
        return float(self._line_2[26:33]) / 10**7

    @cached_property
    def argumentOfPeriapsis(self) -> float:
        """``float``: Argument of periapsis in degrees. Note that this is the mean value, not the true COE."""
        return float(self._line_2[34:42])

    @cached_property
    def meanAnomolay(self) -> float:
        """``float``: Mean anomaly in degrees. Note that this is the mean value, not the true COE."""
        return float(self._line_2[43:51])

    @cached_property
    def trueAnomaly(self) -> float:
        """``float``: The true anomaly in degrees. Note that this is the mean value, not the true COE."""
        assert self.eccentricity < 1, "Only valid for eccentricities < 1."  # noqa: S101
        return meanAnom2TrueAnom(self.meanAnomolay)

    @cached_property
    def meanMotion(self) -> float:
        """``float``: Revolutions per day. Note that this is the mean value, not the true COE."""
        return float(self._line_2[52:63])

    @cached_property
    def semiMajorAxis(self) -> float:
        """``float``: Semi-major axis, in km. Note that this is the mean value, not the true COE."""
        p = 1 / self.meanMotion * 3600 * 24  # Convert to period in seconds
        n: float = 2 * pi / p  # Calculate mean motion in radians per unit time.
        return (G * M_earth / (n**2)) ** (1 / 3.0) / 1000  # Calculate the semi major axis

    @cached_property
    def revolutionNumberAtEpoch(self) -> int:
        """``int``: Number of completed orbits at the start epoch."""
        return int(self._line_2[63:68])


class InitStateLoader(_BaseTLE):
    """Contains behavior needed to build a resonaate initial state config from TLE data."""

    def __init__(self, data: str) -> None:
        """Initializes the object.

        Args:
            data (str): 2 or 3 line TLE string.
        """
        super().__init__(data)
        self._sgp4_obj: Satellite = twoline2rv(self._line_1, self._line_2, wgs72)

    @cached_property
    def propagateInitECI(self) -> ndarray:
        """Propagates the TLE at time-step 0 using the sgp4 algorithm to compute the intial ECI state.

        Returns:
            ndarray: Initial 6-element ECI state vector.
        """
        epoch: JulianDate = self.epoch
        updateReductionParameters(epoch)
        pos_teme, vel_teme = self._sgp4_obj.propagate(*getCalendarDate(epoch))
        x_teme = asarray(pos_teme + vel_teme)
        x_ecef = teme2ecef(x_teme, epoch, getReductionParameters())
        init_eci = ecef2eci(x_ecef, julianDateToDatetime(epoch))
        pos = init_eci[0:3].tolist()
        vel = init_eci[3:6].tolist()
        return array(pos + vel)

    @cached_property
    def propagateInitCOE(self) -> OrbitalElementTuple:
        """Propagates the TLE at time-step 0 using the sgp4 algorithm, and returns true classical orbital elements.

        Returns:
            OrbitalElementTuple: Tuple containing all elements in the following order: sma, ecc, inc, raan, argp, true_anom.
        """
        init_eci = self.propagateInitECI()
        return eci2coe(init_eci)

    @cached_property
    def initECIStateConfig(self) -> ECIStateConfig:
        """Propagates the initial ECI state and builds a state config object.

        Returns:
            ECIStateConfig: Initial State Config object representing the initial ECI state.
        """
        eci = self.propagateInitECI().tolist()
        return ECIStateConfig(
            type="eci",
            position=eci[0:3],
            velocity=eci[3:6],
        )

    @cached_property
    def initCOEStateConfig(self) -> COEStateConfig:
        """Propagates the initial state of the object and builds a COEStateConfig.

        Returns:
            COEStateConfig: COEStateConfig containing truth orbital elements.
        """
        coe = self.propagateInitCOE()
        return COEStateConfig(
            type="coe",
            semi_major_axis=coe[0],
            eccentricity=coe[1],
            inclination=coe[2],
            true_anomaly=coe[5],
            right_ascension=coe[3],
            argument_periapsis=coe[4],
        )
