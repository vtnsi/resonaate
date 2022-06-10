"""Submodule defining the 'observation' configuration section."""
# Local Imports
from .base import ConfigOption, ConfigSection


class ObservationConfig(ConfigSection):
    """Configuration section defining several observation-based options."""

    CONFIG_LABEL = "observation"
    """str: Key where settings are stored in the configuration dictionary read from file."""

    def __init__(self):
        """Construct an instance of a :class:`.ObservationConfig`."""
        self._field_of_view = ConfigOption("field_of_view", (bool,), default=True)

    @property
    def nested_items(self):
        """list: Return a list of :class:`.ConfigOption` objects that this section contains."""
        return [self._field_of_view]

    @property
    def field_of_view(self):
        """bool: whether or not to do field of view calculations."""
        return self._field_of_view.setting
