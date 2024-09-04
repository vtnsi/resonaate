"""Contains implementation of the TLE parser."""

# Standard Library Imports
from datetime import datetime
from functools import cached_property
from math import pi
from typing import TYPE_CHECKING

# Third Party Imports
from numpy import array, asarray, ndarray
from sgp4.earth_gravity import wgs72
from sgp4.io import twoline2rv

# Local Imports
from ...scenario.config.state_config import COEStateConfig, ECIStateConfig
from ..orbits.utils import getSmaFromMeanMotion
from ..time.stardate import JulianDate, datetimeToJulianDate, getCalendarDate, julianDateToDatetime
from ..transforms.methods import ecef2eci, teme2ecef
from .anomaly import meanAnom2TrueAnom
from .conversions import OrbitalElementTuple, eci2coe

if TYPE_CHECKING:
    # Third Party Imports
    from sgp4.model import Satellite


class TLELoader:
    """Basic representation of TLE Information and implementation of a TLE parser."""

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

        self._sgp4_obj: Satellite = twoline2rv(self._line_1, self._line_2, wgs72)

    @cached_property
    def name(self) -> str:
        """``str | None``: The name of the satellite. Returns ``None`` if no title line is present in the TLE."""
        if not self._has_title_line:
            return None
        return self._title_line

    @cached_property
    def catalog_number(self) -> int:
        """``int``: The Sattelite Catalog Number."""
        return int(self._line_1[2:7])

    @cached_property
    def launch_year(self) -> int:
        """``int``: The last two digits of the launch year."""
        return int(self._line_1[9:11])

    @cached_property
    def launch_number(self) -> int:
        """``int``: The launch number of that year."""
        return int(self._line_1[11:14])

    @cached_property
    def epoch(self) -> JulianDate:
        """``JulianDate``: The Epoch."""
        year: int = int(self._line_1[18:20])
        if year > 57:
            year += 1900
        elif year <= 57:
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
    def right_ascension(self) -> float:
        """``float``: Right ascension of the ascending node in degrees. Note that this is the mean value, not the true COE."""
        return float(self._line_2[17:25])

    @cached_property
    def eccentricity(self) -> float:
        """``float``: Orbit eccentricity. Note that this is the mean value, not the true COE."""
        return float(self._line_2[26:33]) / 10**7

    @cached_property
    def argument_of_periapsis(self) -> float:
        """``float``: Argument of periapsis in degrees. Note that this is the mean value, not the true COE."""
        return float(self._line_2[34:42])

    @cached_property
    def mean_anomaly(self) -> float:
        """``float``: Mean anomaly in degrees. Note that this is the mean value, not the true COE."""
        return float(self._line_2[43:51])

    @cached_property
    def true_anomaly(self) -> float:
        """``float``: The true anomaly in degrees. Note that this is the mean value, not the true COE."""
        assert self.eccentricity < 1, "Only valid for eccentricities < 1."  # noqa: S101
        return meanAnom2TrueAnom(self.mean_anomaly)

    @cached_property
    def mean_motion(self) -> float:
        """``float``: Radians / sec. Note that this is the mean value, not the true COE."""
        return float(self._line_2[52:63]) * pi / 43200

    @cached_property
    def semi_major_axis(self) -> float:
        """``float``: Semi-major axis, in km. Note that this is the mean value, not the true COE."""
        return getSmaFromMeanMotion(self.mean_motion)

    @cached_property
    def revolution_number_at_epoch(self) -> int:
        """``int``: Number of completed orbits at the start epoch."""
        return int(self._line_2[63:68])

    @cached_property
    def init_eci(self) -> ndarray:
        """Propagates the TLE at time-step 0 using the sgp4 algorithm to compute the intial ECI state.

        Returns:
            ndarray: Initial 6-element ECI state vector.
        """
        epoch: JulianDate = self.epoch
        utc_datetime = julianDateToDatetime(epoch)
        pos_teme, vel_teme = self._sgp4_obj.propagate(*getCalendarDate(epoch))
        x_teme = asarray(pos_teme + vel_teme)
        x_ecef = teme2ecef(
            x_teme,
            utc_datetime,
        )
        init_eci = ecef2eci(x_ecef, utc_datetime)
        pos = init_eci[0:3].tolist()
        vel = init_eci[3:6].tolist()
        return array(pos + vel)

    @cached_property
    def init_coe(self) -> OrbitalElementTuple:
        """Propagates the TLE at time-step 0 using the sgp4 algorithm, and returns true classical orbital elements.

        Returns:
            OrbitalElementTuple: Tuple containing all elements in the following order: sma, ecc, inc, raan, argp, true_anom.
        """
        init_eci = self.init_eci
        return eci2coe(init_eci)

    @cached_property
    def init_eci_config(self) -> ECIStateConfig:
        """Propagates the initial ECI state and builds a state config object.

        Returns:
            ECIStateConfig: Initial State Config object representing the initial ECI state.
        """
        eci = self.init_eci.tolist()
        return ECIStateConfig(
            type="eci",
            position=eci[0:3],
            velocity=eci[3:6],
        )

    @cached_property
    def init_coe_config(self) -> COEStateConfig:
        """Propagates the initial state of the object and builds a COEStateConfig.

        Returns:
            COEStateConfig: COEStateConfig containing truth orbital elements.
        """
        coe = self.init_coe
        return COEStateConfig(
            type="coe",
            semi_major_axis=coe[0],
            eccentricity=coe[1],
            inclination=coe[2],
            true_anomaly=coe[5],
            right_ascension=coe[3],
            argument_periapsis=coe[4],
        )
