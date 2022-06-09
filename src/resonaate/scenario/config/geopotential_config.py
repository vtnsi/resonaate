"""Submodule defining the 'geopotential' configuration section.

To Do:
    - add range of valid values for 'degree' and 'order'

"""
# Local Imports
from .base import ConfigOption, ConfigSection, inclusiveRange


class GeopotentialConfig(ConfigSection):
    """Configuration section defining several geopotential-based options."""

    CONFIG_LABEL = "geopotential"
    """str: Key where settings are stored in the configuration dictionary read from file."""

    def __init__(self):
        """Construct an instance of a :class:`.GeopotentialConfig`."""
        self._model = ConfigOption("model", (str,), default="egm96.txt")
        self._degree = ConfigOption("degree", (int,), default=4, valid_settings=inclusiveRange(80))
        self._order = ConfigOption("order", (int,), default=4, valid_settings=inclusiveRange(80))

    @property
    def nested_items(self):
        """list: Return a list of :class:`.ConfigOption` objects that this section contains."""
        return [self._model, self._degree, self._order]

    @property
    def model(self):
        """str: Model file used to define the Earth's gravity model."""
        return self._model.setting

    @property
    def degree(self):
        """int: Degree of the Earth's gravity model."""
        return self._degree.setting

    @property
    def order(self):
        """int: Order of the Earth's gravity model."""
        return self._order.setting
