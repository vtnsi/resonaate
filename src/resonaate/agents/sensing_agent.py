"""Defines the :class:`.SensingAgent` class."""

from __future__ import annotations

# Standard Library Imports
from typing import TYPE_CHECKING

# Third Party Imports
from numpy import array

# Local Imports
from ..data.ephemeris import TruthEphemeris
from ..physics.time.stardate import JulianDate
from ..physics.transforms.methods import ecef2lla, eci2ecef
from ..sensors import sensorFactory
from ..sensors.sensor_base import Sensor
from .agent_base import Agent

# Type checking
if TYPE_CHECKING:
    # Standard Library Imports
    from collections.abc import Collection

    # Third Party Imports
    from numpy import ndarray
    from typing_extensions import Self

    # Local Imports
    from ..data.ephemeris import _EphemerisMixin
    from ..data.events.sensor_time_bias import SensorTimeBiasEvent
    from ..dynamics.dynamics_base import Dynamics
    from ..dynamics.integration_events.station_keeping import StationKeeper
    from ..scenario.clock import ScenarioClock
    from ..scenario.config import PropagationConfig
    from ..scenario.config.agent_config import SensingAgentConfig


class SensingAgent(Agent):
    """Define the behavior of the sensing agents in the simulation."""

    def __init__(  # noqa: PLR0913
        self,
        _id: int,
        name: str,
        agent_type: str,
        initial_state: ndarray,
        clock: ScenarioClock,
        sensors: Sensor,
        dynamics: Dynamics,
        realtime: bool,
        visual_cross_section: float | int,
        mass: float | int,
        reflectivity: float,
        station_keeping: list[StationKeeper] | None = None,
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
        self._ecef_state = eci2ecef(self._truth_state, self.datetime_epoch)
        self._lla_state = ecef2lla(self._ecef_state)

        self.sensor_time_bias_event_queue = []

    @classmethod
    def fromConfig(
        cls,
        sen_cfg: SensingAgentConfig,
        clock: ScenarioClock,
        dynamics: Dynamics,
        prop_cfg: PropagationConfig,
    ) -> Self:
        """Factory to initialize `SensingAgent` objects based on given configuration.

        Args:
            sen_cfg (:class:`.SensingAgentConfig`): config from which to generate a sensing agent.
            clock (:class:`.ScenarioClock`): common clock object for the simulation.
            dynamics (:class:`.Dynamics`): dynamics that handles state propagation.
            prop_cfg (:class:`.PropagationConfig`): various propagation simulation settings.

        Returns:
            :class:`.SensingAgent`: properly constructed agent object.
        """
        initial_state = sen_cfg.state.toECI(clock.datetime_epoch)

        # Build the sensor based on the agent configuration
        sensor = sensorFactory(sen_cfg.sensor)

        station_keeping = cls._createStationKeepers(
            prop_cfg.station_keeping,
            sen_cfg.id,
            sen_cfg.platform,
            initial_state,
            clock.julian_date_start,
        )

        return cls(
            sen_cfg.id,
            sen_cfg.name,
            sen_cfg.platform.type,
            initial_state,
            clock,
            sensor,
            dynamics,
            prop_cfg.sensor_realtime_propagation,
            sen_cfg.platform.visual_cross_section,
            sen_cfg.platform.mass,
            sen_cfg.platform.reflectivity,
            station_keeping=station_keeping,
        )

    def appendTimeBiasEvent(self, time_bias_event: SensorTimeBiasEvent) -> None:
        """Queue up a sensor time bias event to happen on the next tasking.

        Args:
            time_bias_event (:class:`.SensorTimeBiasEvent`): Event that will take place during the next tasking.
        """
        # [NOTE][parallel-time-bias-event-handling] Step two: call this method via the event handler to queue the
        # relevant :class:`.SensorTimeBiasEvent`.
        event_list = [old_event.id for old_event in self.sensor_time_bias_event_queue]

        # Make sure you're not adding the same event over multiple timesteps
        if time_bias_event.id not in event_list:
            self.sensor_time_bias_event_queue.append(time_bias_event)

    def pruneTimeBiasEvents(self) -> None:
        """Remove events from the queue that happened in the past."""
        self.sensor_time_bias_event_queue = [
            event
            for event in self.sensor_time_bias_event_queue
            if (
                self.julian_date_epoch <= event.end_time_jd
                and self.julian_date_epoch >= event.start_time_jd
            )
        ]

    def updateInfo(self, sensor_change):
        """Update the boresight and last time tasked attributes.

        Args:
            sensor_change (dict): values to change in the sensor.
        """
        self.sensors.boresight = sensor_change["boresight"]
        self.sensors.time_last_tasked = sensor_change["time_last_tasked"]

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

    def importState(self, ephemeris: _EphemerisMixin) -> None:
        """Set the state of this SensingAgent based on a given :class:`.Ephemeris` object.

        Args:
            ephemeris (:class:`._EphemerisMixin`): data object to update this SensingAgent's state with
        """
        self.eci_state = array(ephemeris.eci)
        self._time = JulianDate(ephemeris.julian_date).convertToScenarioTime(
            self.julian_date_start,
        )

    @property
    def eci_state(self) -> ndarray:
        """``ndarray``: Returns the 6x1 ECI current state vector."""
        return self._truth_state

    @eci_state.setter
    def eci_state(self, new_state: ndarray) -> None:
        """Set the SensingAgent's new 6x1 ECI state vector.

        Args:
            new_state (``ndarray``): 6x1 ECI state vector
        """
        self._truth_state = new_state
        self._ecef_state = eci2ecef(new_state, self.datetime_epoch)
        self._lla_state = ecef2lla(self._ecef_state)

    @property
    def ecef_state(self) -> ndarray:
        """``ndarray``: Returns the 6x1 ECEF current state vector."""
        return self._ecef_state

    @property
    def lla_state(self) -> ndarray:
        """``ndarray``: Returns the 3x1 current position vector in lat, lon, & alt."""
        return self._lla_state

    @property
    def sensors(self) -> Collection[Sensor]:
        """``collections.abc.Collection``: Returns the collection of sensors associated with this SensingAgent."""
        return self._sensors
