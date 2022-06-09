"""Submodule defining the 'filter' configuration section."""
from .base import ConfigSection, ConfigOption, NO_SETTING
from ...dynamics.constants import TWO_BODY_LABEL, SPECIAL_PERTURBATIONS_LABEL
from ...filters import VALID_FILTER_LABELS, VALID_MANEUVER_DETECTION_LABELS


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
        self._maneuver_detection_method = ManeuverDetectionConfig()

    @property
    def nested_items(self):
        """list: Return a list of :class:`.ConfigOption` objects that this section contains."""
        return [self._name, self._parameters, self._dynamics, self._maneuver_detection_method]

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

    @property
    def maneuver_detection_method(self):
        """Class: maneuver detection method nested item."""
        return self._maneuver_detection_method


class ManeuverDetectionConfig(ConfigSection):
    """Configuration section defining maneuver detection options."""

    CONFIG_LABEL = "maneuver_detection_method"
    """str: Key where settings are stored in the configuration dictionary read from file."""

    def __init__(self):
        """Construct an instance of a :class:`.ManeuverDetectionConfig`."""
        self._name = ConfigOption(
            "name",
            (str, ),
            default=NO_SETTING,
            valid_settings=(NO_SETTING, ) + VALID_MANEUVER_DETECTION_LABELS
        )
        self._maneuver_gate_val = ConfigOption("maneuver_gate_val", (float, ), default=0.05)
        self._parameters = ConfigOption("parameters", (dict, ), default=dict())

    @property
    def nested_items(self):
        """list: Return a list of :class:`.ConfigOption` objects that this section contains."""
        return [self._name, self._maneuver_gate_val, self._parameters]

    @property
    def name(self):
        """str: Name of metric to use."""
        return self._name.setting  # pylint: disable=no-member

    @property
    def maneuver_gate_val(self):
        """float: value for maneuver chi^2 threshold."""
        return self._maneuver_gate_val.setting  # pylint: disable=no-member

    @property
    def parameters(self):
        """dict: Parameters to use for the metric function."""
        return self._parameters.setting  # pylint: disable=no-member
