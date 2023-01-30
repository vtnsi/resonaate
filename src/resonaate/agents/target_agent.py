"""Defines the :class:`.TargetAgent` class."""
from __future__ import annotations

# Standard Library Imports
from typing import TYPE_CHECKING

# Third Party Imports
from numpy import array, ndarray

# Local Imports
from ..data.ephemeris import TruthEphemeris
from ..dynamics.integration_events.station_keeping import StationKeeper
from ..physics.orbits.elements import ClassicalElements, EquinoctialElements
from ..physics.time.stardate import JulianDate
from ..physics.transforms.methods import ecef2lla, eci2ecef
from . import SPACECRAFT_LABEL
from .agent_base import Agent

# Type checking
if TYPE_CHECKING:
    # Standard Library Imports
    from typing import Any

    # Third Party Imports
    from typing_extensions import Self

    # Local Imports
    from ..data.ephemeris import _EphemerisMixin
    from ..dynamics.dynamics_base import Dynamics
    from ..scenario.clock import ScenarioClock


LEO_DEFAULT_MASS = 295.0
"""``float``: Default mass of LEO RSO (km)  #.  :cite:t:`LEO_RSO_2022_stats`"""
MEO_DEFAULT_MASS = 2861.0
"""``float``: Default mass of MEO RSO (km)  #.  :cite:t:`steigenberger_MEO_RSO_2022_stats`"""
GEO_DEFAULT_MASS = 6200.0
"""``float``: Default mass of GEO RSO (km)  #.  :cite:t:`GEO_RSO_2022_stats`"""

LEO_DEFAULT_VCS = 10.0
"""``float``: Default visual cross section of LEO RSO (m^2)  #.  :cite:t:`LEO_RSO_2022_stats`"""
MEO_DEFAULT_VCS = 37.5
"""``float``: Default visual cross section of MEO RSO (m^2)  #.  :cite:t:`steigenberger_MEO_RSO_2022_stats`"""
GEO_DEFAULT_VCS = 90.0
"""``float``: Default visual cross section of GEO RSO (m^2)  #.  :cite:t:`GEO_RSO_2022_stats`"""


class TargetAgent(Agent):
    """Define the behavior of the **true** target agents in the simulation.

    References:
        #.  :cite:t:`ISS_2022_stats`
        #.  :cite:t:`LEO_RSO_2022_stats`
        #.  :cite:t:`steigenberger_MEO_RSO_2022_stats`
        #.  :cite:t:`GEO_RSO_2022_stats`
    """

    def __init__(
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
    def fromConfig(cls, config: dict) -> Self:
        """Factory to initialize `TargetAgent` objects based on given configuration.

        Args:
            config (``dict``): formatted configuration parameters

        Returns:
            :class:`.TargetAgent`: properly constructed `TargetAgent` object
        """
        ## [TODO]: Make this not coupled to only `Satellite` targets
        tgt = config["target"]

        # Determine the target's initial ECI state
        if tgt.eci_set:
            initial_state = array(tgt.init_eci)
        elif tgt.coe_set:
            orbit = ClassicalElements.fromConfig(tgt.init_coe)
            initial_state = orbit.toECI()
        elif tgt.eqe_set:
            orbit = EquinoctialElements.fromConfig(tgt.init_eqe)
            initial_state = orbit.toECI()
        else:
            raise ValueError(
                f"TargetAgent config doesn't contain initial state information: {tgt}"
            )

        station_keeping = []
        if config["station_keeping"]:
            for config_str in tgt.station_keeping.routines:
                station_keeping.append(
                    StationKeeper.factory(
                        conf_str=config_str,
                        rso_id=tgt.sat_num,
                        initial_eci=initial_state,
                        julian_date_start=config["clock"].julian_date_start,
                    )
                )

        return cls(
            tgt.sat_num,
            tgt.sat_name,
            SPACECRAFT_LABEL,
            initial_state,
            config["clock"],
            config["dynamics"],
            config["realtime"],
            tgt.visual_cross_section,
            tgt.mass,
            tgt.reflectivity,
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
            self.julian_date_start
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
        self._ecef_state = eci2ecef(new_state, self.datetime_epoch)
        self._lla_state = ecef2lla(self._ecef_state)

    @property
    def previous_state(self) -> ndarray:
        """``ndarray``: Returns the 6x1 ECI previous state vector."""
        return self._previous_state

    @property
    def ecef_state(self) -> ndarray:
        """``ndarray``: Returns the 6x1 ECEF current state vector."""
        return self._ecef_state

    @property
    def lla_state(self) -> ndarray:
        """``ndarray``: Returns the 3x1 current position vector in lat, lon, & alt."""
        return self._lla_state
