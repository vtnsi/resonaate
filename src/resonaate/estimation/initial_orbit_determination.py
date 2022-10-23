"""Defines class structure for IOD methods that utilize the ``physics.orbit_determination`` module."""
from __future__ import annotations

# Standard Library Imports
import logging
from abc import ABC, abstractmethod
from pickle import loads
from typing import TYPE_CHECKING

# Third Party Imports
from numpy import array
from scipy.linalg import norm
from sqlalchemy import asc
from sqlalchemy.orm import Query

# Local Imports
from ..data.observation import Observation
from ..data.resonaate_database import ResonaateDatabase
from ..parallel import getRedisConnection
from ..physics.constants import DAYS2SEC
from ..physics.orbit_determination import OrbitDeterminationFunction
from ..physics.orbit_determination.lambert import determineTransferDirection
from ..physics.orbits.utils import getPeriod, getSemiMajorAxis, getTrueAnomalyFromRV
from ..physics.time.stardate import JulianDate, ScenarioTime, julianDateToDatetime
from ..physics.transforms.methods import ecef2eci, lla2ecef, razel2sez, sez2ecef
from ..physics.transforms.reductions import updateReductionParameters
from ..sensors.sensor_base import ObservationTuple
from .adaptive.initialization import lambertInitializationFactory

if TYPE_CHECKING:
    # Third Party Imports
    from numpy import ndarray
    from typing_extensions import Self

    # Local Imports
    from ..scenario.config.estimation_config import InitialOrbitDeterminationConfig


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
        self._logger = logging.getLogger("resonaate")

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

    @abstractmethod
    def convertObservationToECI(self, observation: Observation) -> ndarray:
        """Convert Observation to ECI position relative to sensor.

        Args:
            Observation (:class:`.Observation`): observation object.

        Returns:
            ``ndarray``: ECI state of observation
        """
        raise NotImplementedError

    def getPreviousObservations(
        self, database: ResonaateDatabase, start_time: ScenarioTime, end_time: ScenarioTime
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
        self, ob1_eci: ndarray, ob1_jdate: JulianDate, ob2_jdate: JulianDate
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
        obs_tuples: list[ObservationTuple],
        detection_time: ScenarioTime,
        current_time: ScenarioTime,
    ) -> ndarray:
        r"""Determine the state vector of an RSO estimate via IOD.

        Args:
            obs_tuples (``list``): :class:`.ObservationTuple` associated with this timestep
            detection_time (:class:`.ScenarioTime`): Lower Bound for query.
            current_time (:class:`.ScenarioTime`): Upper Bound for query.

        Returns:
            ``ndarray``: Estimate state determined from IOD.
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
        self, database: ResonaateDatabase, start_time: ScenarioTime, end_time: ScenarioTime
    ) -> list[Observation]:
        """Retrieve and RSO's previous observations.

        Args:
            database (:class:`.ResonaateDatabase`): RESONAATE internal database object.
            start_time (:class:`.ScenarioTime`) time of start of the current scenario
            end_time (:class:`.ScenarioTime`) time of the current scenario

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
                Observation.sensor_type != "Optical"  # Only Radar/AdvRadar Obs for Lambert IOD
            )
            .order_by(asc(Observation.julian_date))
        )

        return database.getData(observation_query)

    def convertObservationToECI(self, observation: Observation) -> ndarray:
        """Convert Observation to ECI position relative to sensor.

        Args:
            Observation (:class:`.Observation`): observation object.

        Returns:
            ``ndarray``: ECI state of observation
        """
        updateReductionParameters(julianDateToDatetime(JulianDate(observation.julian_date)))
        observation_sez = razel2sez(
            observation.range_km, observation.elevation_rad, observation.azimuth_rad, 0, 0, 0
        )
        sensor_ecef = lla2ecef(
            array(
                [
                    observation.position_lat_rad,
                    observation.position_long_rad,
                    observation.position_altitude_km,
                ]
            )
        )
        observation_ecef = (
            sez2ecef(observation_sez, observation.position_lat_rad, observation.position_long_rad)
            + sensor_ecef
        )
        return ecef2eci(observation_ecef)

    def determineNewEstimateState(
        self,
        obs_tuples: list[ObservationTuple],
        detection_time: ScenarioTime,
        current_time: ScenarioTime,
    ) -> tuple[ndarray | None, bool]:
        r"""Determine the state vector of an RSO estimate via IOD.

        Args:
            obs_tuples (``list``): :class:`.ObservationTuple` associated with this timestep
            detection_time (:class:`.ScenarioTime`): time that IOD is flagged
            current_time (:class:`.ScenarioTime`): current scenario time

        Returns:
            ``tuple``:

            :``ndarray| None``: Estimate state determined from IOD
            :``bool``: whether or not IOD was successful
        """
        if not obs_tuples:
            msg = "No ObservationTuples for IOD"
            self._logger.warning(msg)
            return None, False

        # load path to on-disk database for the current scenario run
        db_path = loads(getRedisConnection().get("db_path"))
        database = ResonaateDatabase.getSharedInterface(db_path=db_path)

        # Ensure observations are from the same pass
        current_julian_date = ScenarioTime(current_time).convertToJulianDate(
            self.julian_date_start
        )

        # Count the number of unique observation times
        previous_observation = self.getPreviousObservations(database, detection_time, current_time)

        # [NOTE]: the `+1` is here because the observation from the current timestep is not yet in the database
        if len(previous_observation) + 1 < self.min_observations:
            msg = f"Not enough observations to perform IOD {len(previous_observation)}"
            self._logger.warning(msg)
            return None, False

        # Get position from Radar observation between maneuver detection time and now
        initial_state = self.convertObservationToECI(previous_observation[-1])

        # Get position from Radar observation from current timestep
        final_state = self._determineFinalState(obs_tuples)
        if final_state is None:
            msg = "No Radar observations to perform Lambert IOD"
            self._logger.warning(msg)
            return None, False

        transit_time = self.checkSinglePass(
            final_state[:3], previous_observation[-1].julian_date, current_julian_date
        )
        if not transit_time:
            msg = "Observations not from a single pass"
            self._logger.warning(msg)
            return None, False

        transfer_method = determineTransferDirection(
            initial_true_anomaly=getTrueAnomalyFromRV(initial_state),
            final_true_anomaly=getTrueAnomalyFromRV(final_state),
        )

        # [NOTE] We don't need initial_velocity because we only are improving the current state estimate.
        _, final_velocity = self.orbit_determination_method(
            initial_state[:3],
            final_state[:3],
            transit_time,
            transfer_method,
        )

        final_state[3:] = final_velocity
        return final_state, True

    def _determineFinalState(self, obs_tuples: list[ObservationTuple]) -> ndarray | None:
        """Calculate Position vector at the current time given observations.

        Args:
            obs_tuples (``list``): :class:`.ObservationTuple` objects at the current time

        Returns:
            ``ndarray`` | ``None``: [6x1] ECI state vector at the current time, but only the position is valid
        """
        # [TODO]: put a method that checks for the obs_tuple with the smallest residual?
        for obs_tuple in obs_tuples:
            if obs_tuple.observation.range_km:
                return self.convertObservationToECI(obs_tuple.observation)

        return None
