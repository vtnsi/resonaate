"""Submodule defining the 'decision' configuration section."""
# Package
from .base import ConfigSection, ConfigOption
from ...tasking.decisions import VALID_DECISIONS


class DecisionConfig(ConfigSection):
    """Configuration section defining several decision-based options."""

    CONFIG_LABEL = "decision"
    """str: Key where settings are stored in the configuration dictionary read from file."""

    def __init__(self):
        """Construct an instance of a :class:`.DecisionConfig`."""
        self._name = ConfigOption(
            "name",
            (str, ),
            valid_settings=VALID_DECISIONS
        )
        self._parameters = ConfigOption("parameters", (dict, ), default=dict())

    @property
    def nested_items(self):
        """list: Return a list of :class:`.ConfigOption` objects that this section contains."""
        return [self._name, self._parameters]

    @property
    def name(self):
        """str: Name of this decision function."""
        return self._name.setting

    @property
    def parameters(self):
        """dict: Parameters for the decision function."""
        return self._parameters.setting
