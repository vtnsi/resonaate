"""Defines class structure for IOD methods that utilize the ``physics.orbit_determination`` module."""

from __future__ import annotations

# Standard Library Imports
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING

# Third Party Imports
from numpy import concatenate
from scipy.linalg import norm
from sqlalchemy import asc
from sqlalchemy.orm import Query

# Local Imports
from ..common.labels import SensorLabel
from ..data import getDBConnection
from ..data.observation import Observation
from ..physics.constants import DAYS2SEC
from ..physics.orbit_determination.lambert import determineTransferDirection
from ..physics.orbits.utils import getPeriod, getSemiMajorAxis
from ..physics.time.stardate import JulianDate, ScenarioTime
from ..physics.transforms.methods import radarObs2eciPosition
from .adaptive.initialization import lambertInitializationFactory

if TYPE_CHECKING:
    # Third Party Imports
    from numpy import ndarray
    from typing_extensions import Self

    # Local Imports
    from ..data.resonaate_database import ResonaateDatabase
    from ..physics.orbit_determination import OrbitDeterminationFunction
    from ..scenario.config.estimation_config import InitialOrbitDeterminationConfig


@dataclass(frozen=True)
class IODSolution:
    """Data class to define IOD output information."""

    state_vector: ndarray | None
    """Associated State vector from converged IOD or ``None`` if not converged."""

    convergence: bool
    """True if IOD successfully converged."""

    message: str
    """Context for convergence success or failure."""


class InitialOrbitDetermination(ABC):
    r"""Abstract class that encapsulates Initial Orbit Determination methods."""

    LABEL: str | None = None

    def __init__(
        self,
        minimum_observation_spacing: int,
        orbit_determination_method: OrbitDeterminationFunction,
        sat_num: int,
        julian_date_start: JulianDate,
    ) -> None:
        r"""Initialize Initial Orbit Determination.

        Args:
            minimum_observation_spacing (``int``): minimum number of seconds required between observations.
            orbit_determination_method (``callable``): :func:`.OrbitDeterminationFunction` function.
            sat_num (``int``): Satcat ID of RSO
            julian_date_start (:class:`.JulianDate`): Starting JulianDate of the scenario

        """
        self.minimum_observation_spacing: int = minimum_observation_spacing
        """``int``: minimum number of seconds required between observations."""
        self.orbit_determination_method: OrbitDeterminationFunction = orbit_determination_method
        """:class:`.OrbitDeterminationFunction`: OD function used to initialize different models, see :mod:`.lambert`."""
        self.sat_num: int = sat_num
        """``int``: unique ID number of the satellite on which IOD is performed."""
        self.julian_date_start: JulianDate = julian_date_start
        """:class:`.JulianDate`: Julian date epoch of the start of the simulation."""
        self.min_observations: int = 2
        """``int``: minimum number of observations required to perform IOD. Defaults to 2."""

    @classmethod
    def fromConfig(
        cls,
        iod_config: InitialOrbitDeterminationConfig,
        sat_num: int,
        julian_date_start: JulianDate,
    ) -> Self:
        """Create initial orbit determination from a config object.

        Args:
            iod_config (:class:`.InitialOrbitDeterminationConfig`): IOD method associated with the estimate
            sat_num (``int``): Satcat ID of RSO
            julian_date_start (:class:`.JulianDate`): Starting JulianDate of the scenario
        Returns:
            class:`.InitialOrbitDeterminationConfig`: constructed adaptive estimation object
        """
        raise NotImplementedError

    def getPreviousObservations(
        self,
        database: ResonaateDatabase,
        start_time: ScenarioTime,
        end_time: ScenarioTime,
    ) -> list[Observation]:
        """Get the Previous observations.

        Args:
            database (:class:`.ResonaateDatabase`): Current scenario database.
            start_time (:class:`.ScenarioTime`): Lower Bound for query.
            end_time (:class:`.ScenarioTime`): Upper Bound for query.

        Returns:
            ``list`` list of `Observation` objects
        """
        raise NotImplementedError

    def checkSinglePass(
        self,
        ob1_eci: ndarray,
        ob1_jdate: JulianDate,
        ob2_jdate: JulianDate,
    ) -> bool:
        """Ensure observations are from the same pass.

        Note:
            First JD must be strictly less than the second one.

        Args:
            ob1_eci (``ndarray``): ECI sate vector at the time of first observation
            ob1_jdate (:class:`.JulianDate`): JulianDate of first observation
            ob2_jdate (:class:`.JulianDate`): JulianDate of second observation

        Returns:
            ``bool``: whether or not obs are from the same pass
        """
        sma = getSemiMajorAxis(norm(ob1_eci[:3]), norm(ob1_eci[3:]))
        period = getPeriod(sma)
        transit_time = (ob2_jdate - ob1_jdate) * DAYS2SEC
        if transit_time >= period:
            return False
        if transit_time <= 0:
            raise ValueError("First JulianDate must be strictly less than the second one.")

        return transit_time

    @abstractmethod
    def determineNewEstimateState(
        self,
        observations: list[Observation],
        detection_time: ScenarioTime,
        current_time: ScenarioTime,
    ) -> IODSolution:
        r"""Determine the state vector of an RSO estimate via IOD.

        Args:
            observations (``list``): :class:`.Observation` associated with this timestep
            detection_time (:class:`.ScenarioTime`): Lower Bound for query.
            current_time (:class:`.ScenarioTime`): Upper Bound for query.

        Returns:
            .IODSolution: solution information including whether it converged, the state vector
                if it converged, and if it didn't converge a message detailing why.
        """
        raise NotImplementedError


class LambertIOD(InitialOrbitDetermination):
    """Lambert Version of IOD."""

    @classmethod
    def fromConfig(
        cls,
        iod_config: InitialOrbitDeterminationConfig,
        sat_num: int,
        julian_date_start: JulianDate,
    ) -> Self:
        """Create initial orbit determination from a config object.

        Args:
            iod_config (:class:`.InitialOrbitDeterminationConfig`): IOD method associated with the estimate
            sat_num (``int``): Target satellite catalog number
            julian_date_start (:class:`.JulianDate`): starting Julian Date of the scenario

        Returns:
            class:`.InitialOrbitDetermination`: constructed adaptive estimation object
        """
        return cls(
            iod_config.minimum_observation_spacing,
            lambertInitializationFactory(iod_config.name),
            sat_num,
            julian_date_start,
        )

    def getPreviousObservations(
        self,
        database: ResonaateDatabase,
        start_time: ScenarioTime,
        end_time: ScenarioTime,
    ) -> list[Observation]:
        """Retrieve and RSO's previous observations.

        Args:
            database (:class:`.ResonaateDatabase`): RESONAATE internal database object.
            start_time (:class:`.ScenarioTime`): time of start of the current scenario
            end_time (:class:`.ScenarioTime`): time of the current scenario

        Returns:
            ``list``: the last :math:`N` :class:`.Observation` objects since ``start_time``
        """
        start_jdate = ScenarioTime(start_time).convertToJulianDate(self.julian_date_start)
        current_jdate = ScenarioTime(end_time).convertToJulianDate(self.julian_date_start)
        # [TODO] Improve the method for checking observation state dimensions
        observation_query = (
            Query(Observation)
            .filter(Observation.target_id == self.sat_num)
            .filter(Observation.julian_date <= current_jdate)
            .filter(Observation.julian_date >= start_jdate)
            .filter(
                Observation.sensor_type != SensorLabel.OPTICAL,
            )  # Only Radar/AdvRadar Obs for Lambert IOD
            .order_by(asc(Observation.julian_date))
        )

        return database.getData(observation_query)

    def determineNewEstimateState(
        self,
        observations: list[Observation],
        detection_time: ScenarioTime,
        current_time: ScenarioTime,
    ) -> IODSolution:
        r"""Determine the state vector of an RSO estimate via IOD.

        Args:
            observations (``list``): :class:`.Observation` associated with this timestep
            detection_time (:class:`.ScenarioTime`): time that IOD is flagged
            current_time (:class:`.ScenarioTime`): current scenario time

        Returns:
            .IODSolution: solution information including whether it converged, the state vector
                if it converged, and if it didn't converge a message detailing why.
        """
        if not observations:
            msg = "No Observations for IOD"
            return IODSolution(None, False, msg)

        # load path to on-disk database for the current scenario run
        database = getDBConnection()

        # Ensure observations are from the same pass
        current_julian_date = ScenarioTime(current_time).convertToJulianDate(
            self.julian_date_start,
        )

        # Count the number of unique observation times
        previous_observation = self.getPreviousObservations(database, detection_time, current_time)

        # Ensure there are observations of the RSO you're trying to do IOD for
        if len(previous_observation) == 0:
            msg = f"No observations in database of RSO {self.sat_num}"
            return IODSolution(None, False, msg)

        # [NOTE]: the `+1` is here because the observation from the current timestep is not yet in the database
        if len(previous_observation) + 1 < self.min_observations:
            msg = f"Not enough observations to perform IOD {len(previous_observation)}"
            return IODSolution(None, False, msg)

        # Get position from Radar observation between maneuver detection time and now
        initial_position = radarObs2eciPosition(previous_observation[-1])

        # Get position from Radar observation from current timestep
        if (final_position := self._determineFinalState(observations)) is None:
            msg = "No Radar observations to perform Lambert IOD"
            return IODSolution(None, False, msg)

        transit_time = self.checkSinglePass(
            final_position,
            previous_observation[-1].julian_date,
            current_julian_date,
        )
        if not transit_time:
            msg = "Observations not from a single pass"
            return IODSolution(None, False, msg)

        # [NOTE]: Circular orbit assumed as first approx.
        transfer_method = determineTransferDirection(initial_position, transit_time)

        # [NOTE] We don't need initial_velocity because we only are improving the current state estimate.
        _, final_velocity = self.orbit_determination_method(
            initial_position,
            final_position,
            transit_time,
            transfer_method,
        )
        msg = "IOD successful"

        return IODSolution(concatenate((final_position, final_velocity)), True, msg)

    def _determineFinalState(self, observations: list[Observation]) -> ndarray | None:
        """Calculate Position vector at the current time given observations.

        Args:
            observations (``list``): :class:`.Observation` objects at the current time

        Returns:
            ``ndarray`` | ``None``: [6x1] ECI state vector at the current time, but only the position is valid
        """
        # [TODO]: put a method that checks for the obs with the smallest residual?
        for observation in observations:
            if observation.range_km:
                return radarObs2eciPosition(observation)

        return None
