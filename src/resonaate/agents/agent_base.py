"""Abstract base class that defines a common interface for all `Agent` classes."""

from __future__ import annotations

# Standard Library Imports
import logging
from abc import ABCMeta, abstractmethod
from typing import TYPE_CHECKING

# Third Party Imports
from numpy import ndarray

# Local Imports
from ..common.labels import PlatformLabel
from ..common.utilities import checkTypes
from ..dynamics.dynamics_base import Dynamics
from ..dynamics.integration_events.finite_thrust import (
    ScheduledFiniteBurn,
    ScheduledFiniteManeuver,
)
from ..dynamics.integration_events.station_keeping import StationKeeper
from ..physics.maths import fpe_equals
from ..scenario.clock import ScenarioClock

if TYPE_CHECKING:
    # Standard Library Imports
    from datetime import datetime
    from typing import Any, Final

    # Local Imports
    from ..data.ephemeris import _EphemerisMixin
    from ..data.events import Event
    from ..physics.time.stardate import JulianDate, ScenarioTime
    from ..scenario.config.platform_config import PlatformConfig


class Agent(metaclass=ABCMeta):
    """Abstract base class for a generic Agent object, i.e. an actor in the simulation."""

    TYPES: Final[dict[str, Any]] = {
        "_id": int,
        "name": str,
        "agent_type": str,
        "initial_state": ndarray,
        "clock": ScenarioClock,
        "dynamics": Dynamics,
        "realtime": bool,
        "visual_cross_section": (int, float),
        "mass": (int, float),
        "reflectivity": float,
        "station_keeping": (list, type(None)),
    }

    def __init__(  # noqa: PLR0913
        self,
        _id: int,
        name: str,
        agent_type: str,
        initial_state: ndarray,
        clock: ScenarioClock,
        dynamics: Dynamics,
        realtime: bool,
        visual_cross_section: float | int,
        mass: float | int,
        reflectivity: float,
        station_keeping: list[StationKeeper] | None = None,
    ):
        """Construct an Agent object.

        Args:
            _id (``int``): unique identification number
            name (``str``): unique identification name
            agent_type (``str``): name signifying the type of agent `('Spacecraft', 'GroundFacility', )`
            initial_state (``ndarray``): 6x1 ECI initial state vector
            clock (:class:`.ScenarioClock`): clock instance for retrieving proper times
            dynamics (:class:`.Dynamics`): Agent's simulation dynamics
            realtime (``bool``): whether to use :attr:`.dynamics` or import data for propagation
            visual_cross_section (``float, int``): constant visual cross-section of the agent
            mass (``float, int``): constant mass of the agent
            reflectivity (``float``): constant reflectivity of the agent
            station_keeping (``list``, optional): list of :class:`.StationKeeper` objects describing the station keeping to
                be performed

        Raises:
            TypeError: raised on incompatible types for input params
            ValueError: raised if invalid viz cross section is provided
        """
        # Define a logger for the Agent
        self._logger = logging.getLogger("resonaate")
        checkTypes(locals(), self.TYPES)

        # Agent's integer ID number
        self._id = _id
        # String for the Agent's name.
        self._name = name
        # String for the Agent's type.
        self._type = agent_type
        # ECI initial state vector describing the Agent's position & velocity
        self._initial_state = initial_state.reshape(6)
        # Time associated with the state in the state property (seconds)
        self._time = clock.time
        # delta timestep
        self._dt_step = clock.dt_step
        # Julian date of start time
        self.julian_date_start = clock.julian_date_start
        # Datetime of start time
        self.datetime_start = clock.datetime_start
        # Dynamics class for propagating the Agent's state
        self._dynamics = dynamics
        # Flag for using real-time propagation
        self._realtime = realtime

        if visual_cross_section < 0.0:
            self._logger.error("Invalid value for visual_cross_section param")
            raise ValueError(visual_cross_section)
        # Visible cross sectional area (m^2)
        self._visual_cross_section = visual_cross_section

        if mass <= 0.0:
            self._logger.error("Invalid value for mass param")
            raise ValueError(mass)
        # Mass (kg)
        self._mass = mass

        # Reflectivity (unitless)
        self._reflectivity = reflectivity

        if station_keeping:
            self._station_keeping = station_keeping
        else:
            self._station_keeping = []
        for station_keeper in self._station_keeping:
            if not isinstance(station_keeper, StationKeeper):
                err = f"{station_keeper} is not a valid StationKeeper object."
                raise TypeError(err)

        self.propagate_event_queue = []

    def appendPropagateEvent(self, event: Event) -> None:
        """Queue up a propagation event to happen on the next propagation.

        Args:
            event (:class:`.Event`): Event that will take place during the next propagation.
        """
        # [NOTE][parallel-maneuver-event-handling] Step two: call this method via the event handler to queue the
        # relevant :class:`.DiscreteStateChangeEvent`.
        self.propagate_event_queue.append(event)

    def prunePropagateEvents(self) -> None:
        """Remove events from the queue that happened in the past."""
        relevant_events = []
        for itr_event in self.propagate_event_queue:
            if isinstance(itr_event, (ScheduledFiniteManeuver, ScheduledFiniteBurn)):
                if not self._time < itr_event.end_time or fpe_equals(
                    itr_event.end_time,
                    self._time,
                ):
                    continue
                if itr_event in relevant_events:
                    continue
                relevant_events.append(itr_event)
            elif self._time < itr_event.time or fpe_equals(itr_event.time, self._time):
                relevant_events.append(itr_event)
        self.propagate_event_queue = relevant_events

    @staticmethod
    def _createStationKeepers(
        global_station_keeping: bool,
        agent_id: int,
        platform_cfg: PlatformConfig,
        initial_state: ndarray,
        jd_start: JulianDate,
    ) -> list[StationKeeper]:
        """Create station keeping objects from list of routines in a config.

        Args:
            global_station_keeping (``bool``): whether station-keeping is turned on globally.
            agent_id (``int``): simulation ID of the associated agent.
            platform_cfg (:class:`.PlatformConfig`): platform config of the associated agent.
            initial_state (``ndarray``): initial ECI state vector of the associated agent.
            jd_start (:class:`.JulianDate`): corresponding initial epoch of the initial state.

        Returns:
            ``list``: constructed :class:`.StationKeeper` objects.
        """
        station_keepers = []
        if not global_station_keeping:
            return station_keepers

        if platform_cfg.type != PlatformLabel.SPACECRAFT:
            return station_keepers

        return [
            StationKeeper.factory(
                conf_str=routine,
                rso_id=agent_id,
                initial_eci=initial_state,
                julian_date_start=jd_start,
            )
            for routine in platform_cfg.station_keeping.routines
        ]

    ### Abstract Methods & Properties ###

    @abstractmethod
    def getCurrentEphemeris(self) -> _EphemerisMixin:
        """Retrieve the Agent's current state for publishing to the DB.

        Returns:
            :class:`._EphemerisMixin`: valid data for inserting into the DB
        """
        raise NotImplementedError

    @abstractmethod
    def importState(self, ephemeris: _EphemerisMixin) -> None:
        """Set the state of this Agent based on a given :class:`.Ephemeris` object.

        Args:
            ephemeris (:class:`._EphemerisMixin`): data object to update this Agent's state with
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def eci_state(self) -> ndarray:
        """``ndarray``: Returns the 6x1 ECI current state vector."""
        raise NotImplementedError

    @property
    @abstractmethod
    def ecef_state(self) -> ndarray:
        """``ndarray``: Returns the 6x1 ECEF current state vector."""
        raise NotImplementedError

    @property
    @abstractmethod
    def lla_state(self) -> ndarray:
        """``ndarray``: Returns the 3x1 current position vector in lat, lon, & alt."""
        raise NotImplementedError

    ### Read-Only Instance Properties ###

    @property
    def initial_state(self) -> ndarray:
        """``ndarray``: Returns the 6x1 initial ECI state vector."""
        return self._initial_state

    @property
    def julian_date_epoch(self) -> JulianDate:
        """:class:`.JulianDate`: Returns the current Julian date."""
        return self._time.convertToJulianDate(self.julian_date_start)

    @property
    def datetime_epoch(self) -> datetime:
        """Returns the current epoch as a datetime object.

        Returns:
            datetime: current epoch.
        """
        return self._time.convertToDatetime(self.datetime_start)

    @property
    def name(self) -> str:
        """``str``: Returns an Agent's name."""
        return self._name

    @property
    def agent_type(self) -> str:
        """``str``: Returns an Agent's type."""
        return self._type

    @property
    def dynamics(self) -> Dynamics:
        """:class:`.Dynamics`: Returns an Agent's dynamics class instance."""
        return self._dynamics

    @property
    def realtime(self) -> bool:
        """``bool``: Returns whether this Agent is being propagated in realtime, or if an importer model is used."""
        return self._realtime

    @property
    def simulation_id(self) -> int:
        """``int``: Returns an ID number associated with the Agent.

        - Spacecraft: SATCAT ID
        - Non-Spacecraft: 10000+
        """
        return self._id

    @property
    def time(self) -> ScenarioTime:
        """:class:`.ScenarioTime`: Returns current epoch seconds."""
        return self._time

    @time.setter
    def time(self, new_time: ScenarioTime) -> None:
        """:class:`.ScenarioTime`: Returns current epoch seconds."""
        self._time = new_time

    @property
    def dt_step(self) -> ScenarioTime:
        """:class:`.ScenarioTime`: Returns the delta T of the scenario."""
        return self._dt_step

    @property
    def station_keeping(self) -> list[StationKeeper]:
        """``list``: Returns the station_keeping list."""
        return self._station_keeping

    @property
    def visual_cross_section(self) -> float:
        """``float, int``: Returns the visual cross-sectional area."""
        return self._visual_cross_section

    @property
    def mass(self) -> float:
        """``float, int``: Returns the mass."""
        return self._mass

    @property
    def reflectivity(self) -> float:
        """``float``: Returns the reflectivity."""
        return self._reflectivity
