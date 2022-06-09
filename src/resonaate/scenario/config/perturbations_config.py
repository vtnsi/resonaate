"""Submodule defining the 'perturbations' configuration section."""
# Local Imports
from .base import ConfigOption, ConfigSection


class PerturbationsConfig(ConfigSection):
    """Configuration section defining several perturbations options."""

    CONFIG_LABEL = "perturbations"
    """str: Key where settings are stored in the configuration dictionary read from file."""

    def __init__(self):
        """Construct an instance of a :class:`.PerturbationsConfig`."""
        self._third_bodies = ConfigOption("third_bodies", (list,), default=[])
        self._solar_radiation_pressure = ConfigOption(
            "solar_radiation_pressure", (bool,), default=False
        )
        self._general_relativity = ConfigOption("general_relativity", (bool,), default=False)

    @property
    def nested_items(self):
        """list: Return a list of :class:`.ConfigOption` objects that this section contains."""
        return [self._third_bodies, self._solar_radiation_pressure, self._general_relativity]

    @property
    def third_bodies(self):
        """list: List of third body objects to use in special perturbations dynamics.

        Currently the objects "sun" and "moon" are supported.
        """
        return self._third_bodies.setting

    @property
    def solar_radiation_pressure(self):
        """Bool: Whether or not to account for solar radiation pressure in special perturbations dynamics."""
        return self._solar_radiation_pressure.setting

    @property
    def general_relativity(self):
        """Bool: Whether or not to account for general relativity in special perturbations dynamics."""
        return self._general_relativity.setting
