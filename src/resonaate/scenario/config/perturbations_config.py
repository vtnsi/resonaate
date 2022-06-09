"""Submodule defining the 'perturbations' configuration section."""
# Package
from .base import ConfigSection, ConfigOption


class PerturbationsConfig(ConfigSection):
    """Configuration section defining several perturbations options."""

    CONFIG_LABEL = "perturbations"
    """str: Key where settings are stored in the configuration dictionary read from file."""

    def __init__(self):
        """Construct an instance of a :class:`.PerturbationsConfig`."""
        self._third_bodies = ConfigOption("third_bodies", (list, ), default=[])

    @property
    def nested_items(self):
        """list: Return a list of :class:`.ConfigOption`s that this section contains."""
        return [self._third_bodies]

    @property
    def third_bodies(self):
        """list: List of third body objects to use in special perturbations dynamics.

        Currently the objects "sun" and "moon" are supported.
        """
        return self._third_bodies.setting
