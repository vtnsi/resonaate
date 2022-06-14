"""Defines the :class:`.SensingAgent` class."""
from __future__ import annotations

# Standard Library Imports
from typing import TYPE_CHECKING

# Third Party Imports
from numpy import array

# Local Imports
from ..common.logger import resonaateLogError
from ..data.ephemeris import EstimateEphemeris, TruthEphemeris
from ..dynamics.integration_events.station_keeping import StationKeeper
from ..dynamics.terrestrial import Terrestrial
from ..physics.orbits.elements import ClassicalElements, EquinoctialElements
from ..physics.time.stardate import JulianDate
from ..physics.transforms.methods import ecef2eci, ecef2lla, eci2ecef, lla2ecef
from ..sensors import sensorFactory
from ..sensors.sensor_base import Sensor
from .agent_base import Agent

# Type checking
if TYPE_CHECKING:
    # Standard Library Imports
    from collections.abc import Collection
    from typing import Union

    # Third Party Imports
    from numpy import ndarray

    # Local Imports
    from ..data.events.sensor_time_bias import SensorTimeBiasEvent
    from ..dynamics.dynamics_base import Dynamics
    from ..scenario.clock import ScenarioClock


GROUND_FACILITY_LABEL = "GroundFacility"
"""str: Constant string used to describe ground facility sensors."""

SPACECRAFT_LABEL = "Spacecraft"
"""str: Constant string used to describe spacecraft-based sensors."""


class SensingAgent(Agent):
    """Define the behavior of the sensing agents in the simulation."""

    def __init__(
        self,
        _id: int,
        name: str,
        agent_type: str,
        initial_state: ndarray,
        clock: ScenarioClock,
        sensors: Sensor,
        dynamics: Dynamics,
        realtime: bool,
        visual_cross_section: Union[float, int],
        mass: Union[float, int],
        reflectivity: float,
        station_keeping: list[StationKeeper] = None,
    ):
        """Construct a SensingAgent object.

        Args:
            _id (``int``): unique identification number
            name (``str``): unique identification name
            agent_type (``str``): name signifying the type of agent `('Spacecraft', 'GroundFacility', )`
            initial_state (``numpy.ndarray``): 6x1 ECI initial state vector
            clock (:class:`.ScenarioClock`): clock instance for retrieving proper times
            sensors (:class:`.Sensor`): sensor object associated this SensingAgent object
            dynamics (:class:`.Dynamics`): SensingAgent's simulation dynamics
            realtime (``bool``): whether to use :attr:`dynamics` or import data for propagation
            visual_cross_section (``float, int``): constant visual cross-section of the agent
            mass (``float, int``): constant mass of the agent
            reflectivity (``float``): constant reflectivity of the agent
            station_keeping (list, optional): list of :class:`.StationKeeper` objects describing the station
                keeping to be performed

        Raises:
            TypeError: raised on incompatible types for input params
        """

        super().__init__(
            _id=_id,
            name=name,
            agent_type=agent_type,
            initial_state=initial_state,
            clock=clock,
            dynamics=dynamics,
            realtime=realtime,
            visual_cross_section=visual_cross_section,
            mass=mass,
            reflectivity=reflectivity,
            station_keeping=station_keeping,
        )
        # [TODO]: Make sensors attribute a collection, so we can attach multiple sensors to an agent
        # if not isinstance(sensors, Collection):
        #     self._logger.error("Incorrect type for sensors param")
        #     raise TypeError(type(sensors))
        # for sensor in sensors:
        if not isinstance(sensors, Sensor):
            self._logger.error("Item in sensors param is not a `Sensor` object")
            raise TypeError(type(sensors))
        self._sensors = sensors
        self._sensors.host = self

        # Properly initialize the SensingAgent's state types
        self._truth_state = array(initial_state, copy=True)
        self._ecef_state = eci2ecef(self._truth_state)
        self._lla_state = ecef2lla(self._ecef_state)

        self.sensor_time_bias_event_queue = []

    def appendTimeBiasEvent(
        self,
        time_bias_event: SensorTimeBiasEvent,
    ) -> None:
        """Queue up a sensor time bias event to happen on the next tasking.

        Args:
            time_bias_event (SensorTimeBiasEvent): Event that will take place during the next tasking.
        """
        # [NOTE][parallel-time-bias-event-handling] Step two: call this method via the event handler to queue the
        # relevant :class:`.SensorTimeBiasEvent`.
        event_list = []
        for old_event in self.sensor_time_bias_event_queue:
            event_list.append(old_event.id)
        # Make sure you're not adding the same event over multiple timesteps
        if time_bias_event.id not in event_list:
            self.sensor_time_bias_event_queue.append(time_bias_event)

    def pruneTimeBiasEvents(self) -> None:
        """Remove events from the queue that happened in the past."""
        relevant_events = []
        for itr_event in self.sensor_time_bias_event_queue:
            if (
                self.julian_date_epoch <= itr_event.end_time_jd
                and self.julian_date_epoch >= itr_event.start_time_jd
            ):
                relevant_events.append(itr_event)
        self.sensor_time_bias_event_queue = relevant_events

    def getCurrentEphemeris(self) -> TruthEphemeris:
        """Returns the SensingAgent's current ephemeris information.

        This is used for bulk-updating the output database with state information.

        Returns:
            :class:`.TruthEphemeris`: valid data object for insertion into output database.
        """
        return TruthEphemeris.fromECIVector(
            agent_id=self.simulation_id,
            julian_date=self.julian_date_epoch,
            eci=self.eci_state.tolist(),
        )

    def importState(
        self,
        ephemeris: Union[TruthEphemeris, EstimateEphemeris],
    ) -> None:
        """Set the state of this SensingAgent based on a given :class:`.Ephemeris` object.

        Args:
            ephemeris (:class:`.Ephemeris`): data object to update this SensingAgent's state with
        """
        self.eci_state = array(ephemeris.eci)
        self._time = JulianDate(ephemeris.julian_date).convertToScenarioTime(
            self.julian_date_start
        )

    @classmethod
    def fromConfig(
        cls,
        config: dict,
        events: dict,
    ) -> SensingAgent:
        """Factory to initialize `SensingAgent` objects based on given configuration.

        Args:
            config (``dict``): formatted configuration parameters
            events (``dict``): corresponding formatted events

        Returns:
            :class:`.SensingAgent`: properly constructed `SensingAgent` object
        """
        agent = config["agent"]

        # Build the sensor based on the agent configuration
        sensor = sensorFactory(agent, config["field_of_view_calculation"])

        station_keeping = []
        use_realtime = config["realtime"]
        if agent.lla_set:
            lla_orig = array([agent.lat, agent.lon, agent.alt])  # radians, radians, km
            initial_state = ecef2eci(lla2ecef(lla_orig))
        elif agent.eci_set:
            initial_state = array(agent.init_eci)
        elif agent.coe_set:
            orbit = ClassicalElements.fromConfig(agent.init_coe)
            initial_state = orbit.toECI()
        elif agent.eqe_set:
            orbit = EquinoctialElements.fromConfig(agent.init_eqe)
            initial_state = orbit.toECI()
        else:
            raise ValueError(
                f"SensorAgent config doesn't contain initial state information: {agent}"
            )

        if agent.host_type == GROUND_FACILITY_LABEL:
            dynamics = Terrestrial(config["clock"].julian_date_start, eci2ecef(initial_state))
        elif agent.host_type == SPACECRAFT_LABEL:
            # [TODO]: Find a way to pass down dynamics config?
            dynamics = config["satellite_dynamics"]
            for config_str in agent.station_keeping.routines:
                station_keeping.append(
                    StationKeeper.factory(
                        conf_str=config_str,
                        rso_id=agent.id,
                        initial_eci=initial_state,
                        julian_date_start=config["clock"].julian_date_start,
                    )
                )
        else:
            msg = f'Invalid value for `host_type` key for sensor agent `{agent["name"]}`'
            resonaateLogError(msg)
            raise ValueError(agent.host_type)

        return cls(
            agent.id,
            agent.name,
            agent.host_type,
            initial_state,
            config["clock"],
            sensor,
            dynamics,
            use_realtime,
            agent.visual_cross_section,
            agent.mass,
            agent.reflectivity,
            station_keeping,
        )

    @property
    def eci_state(self) -> ndarray:
        """``numpy.ndarray``: Returns the 6x1 ECI current state vector."""
        return self._truth_state

    @eci_state.setter
    def eci_state(
        self,
        new_state: ndarray,
    ) -> None:
        """Set the SensingAgent's new 6x1 ECI state vector.

        Args:
            new_state (``numpy.ndarray``): 6x1 ECI state vector
        """
        self._truth_state = new_state
        self._ecef_state = eci2ecef(new_state)
        self._lla_state = ecef2lla(self._ecef_state)

    @property
    def ecef_state(self) -> ndarray:
        """``numpy.ndarray``: Returns the 6x1 ECEF current state vector."""
        return self._ecef_state

    @property
    def lla_state(self) -> ndarray:
        """``numpy.ndarray``: Returns the 3x1 current position vector in lat, lon, & alt."""
        return self._lla_state

    @property
    def sensors(self) -> Collection:
        """``collections.abc.Collection``: Returns the collection of sensors associated with this SensingAgent."""
        return self._sensors
