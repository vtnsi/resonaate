"""Defines platform config types for describing an agent's host entity and its behavior."""

from __future__ import annotations

# Standard Library Imports
from abc import ABC, abstractmethod
from typing import Annotated, Literal, Optional, Union

# Third Party Imports
from pydantic import BaseModel, Field

# Local Imports
from ...common.labels import PlatformLabel, StationKeepingRoutine
from ...physics.constants import SOLAR_PANEL_REFLECTIVITY
from ...physics.orbits import ResidentStratification, _StratificationSpecification

# ruff: noqa: UP007

class StationKeepingConfig(BaseModel):
    R"""Configuration for station keeping routines."""

    routines: list[StationKeepingRoutine] = Field(default_factory=list)
    R"""``list``: station keeping routines to be used."""


class PlatformConfigBase(BaseModel, ABC):
    R"""Configuration base class defining the platform of an agent."""

    mass: Optional[float] = None
    R"""``float``, optional: total mass, kg. Defaults to a value based on orbital regime."""

    visual_cross_section: Optional[float] = None
    R"""``float``, optional: visual cross-sectional area, m^2. Defaults to a value based on orbital regime."""

    reflectivity: Optional[float] = SOLAR_PANEL_REFLECTIVITY
    R"""``float``, optional: constant reflectivity, unit-less. Defaults to :data:`.SOLAR_PANEL_REFLECTIVITY`."""

    @abstractmethod
    def isAltitudeValid(self, altitude: float) -> bool:
        """Return boolean indication of whether specified `altitude` is valid for this platform configuration."""
        raise NotImplementedError

    def setStratDefaults(self, strat: _StratificationSpecification):
        """Set :attr:`.mass` and :attr:`.visual_cross_section` according to specified `strat`.

        Args:
            strat (_StratificationSpecification): Resident stratification specification of this platform.
        """
        if self.mass is None:
            self.mass = strat.default_mass
        if self.visual_cross_section is None:
            self.visual_cross_section = strat.default_vis_x


class SpacecraftConfig(PlatformConfigBase):
    R"""Configuration defining an agent that is a spacecraft platform."""

    type: Literal[PlatformLabel.SPACECRAFT] = PlatformLabel.SPACECRAFT  # type: ignore
    R"""``str``: type of platform being defined."""

    station_keeping: StationKeepingConfig = Field(default_factory=StationKeepingConfig)
    R""":class:`.StationKeepingConfig`, optional: types of station-keeping to apply during propagation. Defaults to a no station-keeping routines.

    Note:
        The global :attr:`.propagation.station_keeping` must be set to ``True`` for station-keeping
        routines to actually run.
    """

    def isAltitudeValid(self, altitude: float) -> bool:
        """Verify that the altitude is above the surface of the Earth.

        Args:
            altitude (float): The altitude of this platform (in KM).

        Returns:
            bool: Indication that the specified `altitude` is above the surface of the Earth.
        """
        return altitude > ResidentStratification.SURFACE.max_altitude


class GroundFacilityConfig(PlatformConfigBase):
    R"""Configuration defining an agent that is a ground facility platform."""

    type: Literal[PlatformLabel.GROUND_FACILITY] = PlatformLabel.GROUND_FACILITY  # type: ignore
    R"""``str``: type of platform being defined."""

    def isAltitudeValid(self, altitude: float) -> bool:
        """Verify that the altitude is on the surface of the Earth.

        Args:
            altitude (float): The altitude of this platform (in KM).

        Returns:
            bool: Indication that the specified `altitude` is on the surface of the Earth.
        """
        return altitude <= ResidentStratification.SURFACE.max_altitude


PlatformConfig = Annotated[
    Union[SpacecraftConfig, GroundFacilityConfig],
    Field(..., discriminator="type"),
]
"""Annotated[Union]: Discriminated union defining valid platform configurations."""
