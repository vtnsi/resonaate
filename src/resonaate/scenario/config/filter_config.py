from .base import ConfigSection, ConfigOption
from ...dynamics.constants import TWO_BODY_LABEL, SPECIAL_PERTURBATIONS_LABEL
from ...filters import VALID_FILTER_LABELS


class FilterConfig(ConfigSection):
    """Configuration section defining several filter-based options."""

    CONFIG_LABEL = "filter"
    """str: Key where settings are stored in the configuration dictionary read from file."""

    def __init__(self):
        """Construct an instance of a :class:`.FilterConfig`."""
        self._name = ConfigOption("name", (str, ), valid_settings=VALID_FILTER_LABELS)
        self._parameters = ConfigOption("parameters", (dict, ), default={})
        self._dynamics = ConfigOption(
            "dynamics_model",
            (str, ),
            default=SPECIAL_PERTURBATIONS_LABEL,
            valid_settings=(TWO_BODY_LABEL, SPECIAL_PERTURBATIONS_LABEL)
        )

    @property
    def nested_items(self):
        """list: Return a list of :class:`.ConfigOption`s that this section contains."""
        return [self._name, self._parameters, self._dynamics]

    @property
    def name(self):
        """str: Name of the type of filter to use."""
        return self._name.setting

    @property
    def parameters(self):
        """dict: Dictionary of parameters used to further define the filter to use."""
        return self._parameters.setting

    @property
    def dynamics(self):
        """str: Name of the dynamics to use in the filter."""
        return self._dynamics.setting
