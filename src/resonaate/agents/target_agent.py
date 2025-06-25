"""Defines the :class:`.TargetAgent` class."""

from __future__ import annotations

# Standard Library Imports
from typing import TYPE_CHECKING

# Third Party Imports
from numpy import array, ndarray

# Local Imports
from ..data.ephemeris import TruthEphemeris
from ..physics.time.stardate import JulianDate
from ..physics.transforms.methods import ecef2lla, eci2ecef
from .agent_base import Agent

# Type checking
if TYPE_CHECKING:
    # Third Party Imports
    from typing_extensions import Self

    # Local Imports
    from ..data.ephemeris import _EphemerisMixin
    from ..dynamics.dynamics_base import Dynamics
    from ..dynamics.integration_events.station_keeping import StationKeeper
    from ..scenario.clock import ScenarioClock
    from ..scenario.config import AgentConfig, PropagationConfig


class TargetAgent(Agent):
    """Define the behavior of the **true** target agents in the simulation.

    References:
        #.  :cite:t:`ISS_2022_stats`
        #.  :cite:t:`LEO_RSO_2022_stats`
        #.  :cite:t:`steigenberger_MEO_RSO_2022_stats`
        #.  :cite:t:`GEO_RSO_2022_stats`
    """

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
        """Construct a TargetAgent object.

        Args:
            _id (``int``): unique identification number
            name (``str``): unique identification name
            agent_type (``str``): name signifying the type of agent `('Spacecraft', 'GroundFacility', )`
            initial_state (``ndarray``): 6x1 ECI initial state vector
            clock (:class:`.ScenarioClock`): clock instance for retrieving proper times
            dynamics (:class:`.Dynamics`): TargetAgent's simulation dynamics
            realtime (``bool``): whether to use :attr:`dynamics` or import data for propagation
            visual_cross_section (``float, int``): constant visual cross-section of the agent
            mass (``float, int``): constant mass of the agent
            reflectivity (``float``): constant reflectivity of the agent
            station_keeping (list, optional): list of :class:`.StationKeeper` objects describing the station keeping to
                be performed

        Raises:
            TypeError: raised on incompatible types for input params
            ShapeError: raised if process noise is not a 6x6 matrix
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
        # Properly initialize the TargetAgent's state types
        self._truth_state = array(initial_state, copy=True)
        self._ecef_state = eci2ecef(self._truth_state, self.datetime_epoch)
        self._lla_state = ecef2lla(self._ecef_state)
        self._previous_state = array(initial_state, copy=True)

    @classmethod
    def fromConfig(
        cls,
        tgt_cfg: AgentConfig,
        clock: ScenarioClock,
        dynamics: Dynamics,
        prop_cfg: PropagationConfig,
    ) -> Self:
        """Factory to initialize `TargetAgent` objects based on given configuration.

        Args:
            tgt_cfg (:class:`.AgentConfig`): config from which to generate a target agent.
            clock (:class:`.ScenarioClock`): common clock object for the simulation.
            dynamics (:class:`.Dynamics`): dynamics that handles state propagation.
            prop_cfg (:class:`.PropagationConfig`): various propagation simulation settings.

        Returns:
            :class:`.TargetAgent`: properly constructed agent object.
        """
        initial_state = tgt_cfg.state.toECI(clock.datetime_epoch)

        station_keeping = cls._createStationKeepers(
            prop_cfg.station_keeping,
            tgt_cfg.id,
            tgt_cfg.platform,
            initial_state,
            clock.julian_date_start,
        )

        return cls(
            tgt_cfg.id,
            tgt_cfg.name,
            tgt_cfg.platform.type,
            initial_state,
            clock,
            dynamics,
            prop_cfg.target_realtime_propagation,
            tgt_cfg.platform.visual_cross_section,
            tgt_cfg.platform.mass,
            tgt_cfg.platform.reflectivity,
            station_keeping=station_keeping,
        )

    def getCurrentEphemeris(self) -> TruthEphemeris:
        """Returns the TargetAgent's current ephemeris information.

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
        """Set the state of this TargetAgent based on a given :class:`.Ephemeris` object.

        Args:
            ephemeris (:class:`._EphemerisMixin`): data object to update this TargetAgent's state with
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
        """Set the TargetAgent's new 6x1 ECI state vector.

        Args:
            new_state (``ndarray``): 6x1 ECI state vector
        """
        self._previous_state = self._truth_state
        self._truth_state = new_state
        self._ecef_state = None
        self._lla_state = None

    @property
    def previous_state(self) -> ndarray:
        """``ndarray``: Returns the 6x1 ECI previous state vector."""
        return self._previous_state

    @property
    def ecef_state(self) -> ndarray:
        """``ndarray``: Returns the 6x1 ECEF current state vector."""
        if self._ecef_state is None:
            self._ecef_state = eci2ecef(self.eci_state, self.datetime_epoch)
        return self._ecef_state

    @property
    def lla_state(self) -> ndarray:
        """``ndarray``: Returns the 3x1 current position vector in lat, lon, & alt."""
        if self._lla_state is None:
            self._lla_state = ecef2lla(self.ecef_state)
        return self._lla_state
