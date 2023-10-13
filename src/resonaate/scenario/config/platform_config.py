"""Defines platform config types for describing an agent's host entity and its behavior."""
from __future__ import annotations

# Standard Library Imports
from abc import ABC, abstractmethod
from dataclasses import InitVar, dataclass, field
from typing import TYPE_CHECKING, ClassVar

# Third Party Imports
from numpy.linalg import norm

# Local Imports
from ...agents import (
    DEFAULT_MASS,
    DEFAULT_VCS,
    GEO_DEFAULT_MASS,
    GEO_DEFAULT_VCS,
    LEO_DEFAULT_MASS,
    LEO_DEFAULT_VCS,
    MEO_DEFAULT_MASS,
    MEO_DEFAULT_VCS,
    SOLAR_PANEL_REFLECTIVITY,
)
from ...common.labels import OrbitRegimeLabel, PlatformLabel, StateLabel
from ...dynamics.integration_events.station_keeping import VALID_STATION_KEEPING_ROUTINES
from ...physics.bodies.earth import Earth
from ...physics.orbits import GEO_ALTITUDE_LIMIT, LEO_ALTITUDE_LIMIT, MEO_ALTITUDE_LIMIT
from .base import ConfigError, ConfigObject, ConfigValueError

# Type Checking Imports
if TYPE_CHECKING:
    # Standard Library Imports
    from typing import Literal

    # Third Party Imports
    from typing_extensions import Self

    # Local Imports
    from .state_config import StateConfig

# ruff: noqa: A003

MASS_MAP: dict[str, float] = {
    OrbitRegimeLabel.LEO: LEO_DEFAULT_MASS,
    OrbitRegimeLabel.MEO: MEO_DEFAULT_MASS,
    OrbitRegimeLabel.GEO: GEO_DEFAULT_MASS,
}

VCS_MAP: dict[str, float] = {
    OrbitRegimeLabel.LEO: LEO_DEFAULT_VCS,
    OrbitRegimeLabel.MEO: MEO_DEFAULT_VCS,
    OrbitRegimeLabel.GEO: GEO_DEFAULT_VCS,
}


@dataclass
class StationKeepingConfig(ConfigObject):
    R"""Configuration for station keeping routines."""

    CONFIG_LABEL: ClassVar[str] = "station_keeping"
    R"""``str``: Key where settings are stored in the configuration dictionary."""

    routines: list[str] = field(default_factory=list)
    R"""``list``: station keeping routines to be used."""

    def __post_init__(self):
        R"""Runs after the class is initialized."""
        for routine in self.routines:
            if routine not in VALID_STATION_KEEPING_ROUTINES:
                raise ConfigValueError("routine", routine, VALID_STATION_KEEPING_ROUTINES)

    def toJSON(self) -> dict[str, list[str]]:
        R"""Convert station keeping config section to JSON-serializable format."""
        return {"routines": self.routines}


@dataclass
class PlatformConfig(ABC, ConfigObject):
    R"""Configuration base class defining the platform of an agent."""

    VALID_LABELS: ClassVar[list[str]] = [
        PlatformLabel.GROUND_FACILITY,
        PlatformLabel.SPACECRAFT,
    ]

    # Config label class variable - not used by "dataclass"
    CONFIG_LABEL: ClassVar[str] = "platform"
    R"""``str``: Key where settings are stored in the configuration dictionary."""

    type: Literal["spacecraft", "ground_facility"]
    R"""``str``: type of platform being defined."""

    state: InitVar[StateConfig]
    R""":class:`.StateConfig`: defines the location/dynamics of this agent.

    :meta private:
    """

    mass: float | None = None
    R"""``float``, optional: total mass, kg. Defaults to a value based on orbital regime."""

    visual_cross_section: float | None = None
    R"""``float``, optional: visual cross-sectional area, m^2.

    Defaults to :data:`.DEFAULT_VCS` or an orbital-regime if it is a spacecraft.
    """

    reflectivity: float | None = None
    R"""``float``, optional: constant reflectivity, unit-less. Defaults to :data:`.SOLAR_PANEL_REFLECTIVITY`."""

    def __post_init__(self, state: StateConfig):
        R"""Runs after the dataclass is initialized."""
        if self.type not in self.VALID_LABELS:
            raise ConfigValueError("type", self.type, self.VALID_LABELS)

        if not isinstance(self, SpacecraftConfig) and self.mass is None:
            self.mass = DEFAULT_MASS

        if not isinstance(self, SpacecraftConfig) and self.visual_cross_section is None:
            self.visual_cross_section = DEFAULT_VCS

        if self.reflectivity is None:
            self.reflectivity = SOLAR_PANEL_REFLECTIVITY

        if state.type not in self.valid_states:
            raise ConfigValueError(
                f"{self.CONFIG_LABEL} referenced state", state.type, self.valid_states
            )

    @classmethod
    def fromDict(cls, platform_cfg: dict, state: StateConfig) -> Self:
        R"""Construct a platform config instance from a dictionary.

        Args:
            platform_cfg (``dict``): config dictionary

        Raises:
            ConfigValueError: raised if an incorrect type is set
        """
        if platform_cfg["type"] not in PlatformConfig.VALID_LABELS:
            raise ConfigValueError(
                PlatformConfig.CONFIG_LABEL + ".type",
                platform_cfg["type"],
                PlatformConfig.VALID_LABELS,
            )
        return PLATFORM_MAP[platform_cfg["type"]](**platform_cfg, state=state)

    @property
    @abstractmethod
    def valid_states(self) -> list[str]:
        R"""``list``: Returns set of valid state types that can be used to define this platform."""
        raise NotImplementedError


@dataclass
class SpacecraftConfig(PlatformConfig):
    R"""Configuration defining an agent that is a spacecraft platform."""

    type: Literal["spacecraft"]
    R"""``str``: type of platform being defined."""

    station_keeping: StationKeepingConfig | dict | None = None
    R""":class:`.StationKeepingConfig`, optional: types of station-keeping to apply during propagation. Defaults to a no station-keeping routines.

    Note:
        The global :attr:`.propagation.station_keeping` must be set to ``True`` for station-keeping
        routines to actually run.
    """

    def __post_init__(self, state: StateConfig):
        R"""Runs after the dataclass is initialized."""
        super().__post_init__(state)

        orbital_regime = self._getOrbitRegimeFromStateConfig(state)

        if self.mass is None:
            self.mass = MASS_MAP[orbital_regime]

        if self.visual_cross_section is None:
            self.visual_cross_section = VCS_MAP[orbital_regime]

        if isinstance(self.station_keeping, dict):
            self.station_keeping = StationKeepingConfig(**self.station_keeping)

        if self.station_keeping is None:
            self.station_keeping = StationKeepingConfig()

    @property
    def valid_states(self) -> list[str]:
        R"""``list``: Returns set of valid state types that can be used to define this platform."""
        return [StateLabel.ECI, StateLabel.COE, StateLabel.EQE]

    @staticmethod
    def _getOrbitRegimeFromStateConfig(state_config: StateConfig) -> str:
        R"""Determine the orbital regime given the state config object.

        Args:
            state_config (:class:`.StateConfig`): state cfg of the agent.

        Raises:
            :exc:.`.ConfigError``: raised if unsupported config is passed, or altitude
                is outside the accepted regimes.

        Returns:
            ``str``: orbital regime label.
        """
        # [NOTE]: Based on position - so current altitude of orbit, not median
        if state_config.type == StateLabel.ECI:
            altitude = norm(state_config.position) - Earth.radius

        # [NOTE]: Based on SMA - so median altitude of orbit, not current
        if state_config.type in (StateLabel.EQE, StateLabel.COE):
            altitude = state_config.semi_major_axis - Earth.radius

        if altitude <= Earth.atmosphere:
            err = f"RSO altitude below 100km: {altitude}"
            raise ConfigError(state_config.__class__.__name__, err)

        if altitude <= LEO_ALTITUDE_LIMIT:
            orbital_regime = OrbitRegimeLabel.LEO
        elif altitude <= MEO_ALTITUDE_LIMIT:
            orbital_regime = OrbitRegimeLabel.MEO
        elif altitude <= GEO_ALTITUDE_LIMIT:
            orbital_regime = OrbitRegimeLabel.GEO
        else:
            err = f"RSO altitude above GEO: {altitude}. unable to set a default mass value"
            raise ConfigError(state_config.__class__.__name__, err)

        return orbital_regime


@dataclass
class GroundFacilityConfig(PlatformConfig):
    R"""Configuration defining an agent that is a ground facility platform."""

    type: Literal["ground_facility"]
    R"""``str``: type of platform being defined."""

    @property
    def valid_states(self) -> list[str]:
        R"""``list``: Returns set of valid state types that can be used to define this platform."""
        return [StateLabel.ECI, StateLabel.LLA]


PLATFORM_MAP: dict[str, PlatformConfig] = {
    PlatformLabel.SPACECRAFT: SpacecraftConfig,
    PlatformLabel.GROUND_FACILITY: GroundFacilityConfig,
}
