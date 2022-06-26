"""Submodule defining the 'estimation' configuration section."""
# Local Imports
from ...dynamics.constants import SPECIAL_PERTURBATIONS_LABEL, TWO_BODY_LABEL
from ...estimation import (
    VALID_ADAPTIVE_ESTIMATION_LABELS,
    VALID_FILTER_LABELS,
    VALID_MANEUVER_DETECTION_LABELS,
)
from ...estimation.adaptive.initialization import VALID_ORBIT_DETERMINATION_LABELS
from ...estimation.adaptive.mmae_stacking_utils import VALID_STACKING_LABELS
from .base import NO_SETTING, ConfigOption, ConfigSection


class EstimationConfig(ConfigSection):
    """Configuration section defining several estimation-based options."""

    CONFIG_LABEL = "estimation"
    """``str``: Key where settings are stored in the configuration dictionary read from file."""

    def __init__(self):
        """Construct an instance of a :class:`.EstimationConfig`."""
        self._sequential_filter = SequentialFilterConfig()
        self._adaptive_filter = AdaptiveEstimationConfig()

    @property
    def nested_items(self):
        """``list``: Return a list of :class:`.ConfigOption` objects that this section contains."""
        return [self._sequential_filter, self._adaptive_filter]

    @property
    def sequential_filter(self):
        """:class:`.SequentialFilterConfig`: sequential technique as nested item."""
        return self._sequential_filter

    @property
    def adaptive_filter(self):
        """:class:`.AdaptiveEstimationConfig`: adaptive estimation technique as nested item."""
        return self._adaptive_filter


class SequentialFilterConfig(ConfigSection):
    """Configuration section defining several sequential filter-based options."""

    CONFIG_LABEL = "sequential_filter"
    """``str``: Key where settings are stored in the configuration dictionary read from file."""

    def __init__(self):
        """Construct an instance of a :class:`.EstimationConfig`."""
        self._name = ConfigOption("name", (str,), valid_settings=VALID_FILTER_LABELS)
        self._parameters = ConfigOption("parameters", (dict,), default={})
        self._dynamics = ConfigOption(
            "dynamics_model",
            (str,),
            default=SPECIAL_PERTURBATIONS_LABEL,
            valid_settings=(TWO_BODY_LABEL, SPECIAL_PERTURBATIONS_LABEL),
        )
        self._maneuver_detection = ManeuverDetectionConfig()
        self._adaptive_estimation = ConfigOption("adaptive_estimation", (bool,), default=False)

    @property
    def nested_items(self):
        """``list``: Return a list of :class:`.ConfigOption` objects that this section contains."""
        return [
            self._name,
            self._parameters,
            self._dynamics,
            self._maneuver_detection,
            self._adaptive_estimation,
        ]

    @property
    def name(self):
        """``str``: Name of the type of filter to use."""
        return self._name.setting

    @property
    def parameters(self):
        """``dict``: Dictionary of parameters used to further define the filter to use."""
        return self._parameters.setting

    @property
    def dynamics(self):
        """``str``: Name of the dynamics to use in the filter."""
        return self._dynamics.setting

    @property
    def maneuver_detection(self):
        """:class:`.ManeuverDetectionConfig`: maneuver detection technique as nested item."""
        return self._maneuver_detection

    @property
    def adaptive_estimation(self):
        """``bool``: Check if sequential filter should turn on adaptive estimation."""
        return self._adaptive_estimation.setting


class ManeuverDetectionConfig(ConfigSection):
    """Configuration section defining maneuver detection options."""

    CONFIG_LABEL = "maneuver_detection"
    """``str``: Key where settings are stored in the configuration dictionary read from file."""

    def __init__(self):
        """Construct an instance of a :class:`.ManeuverDetectionConfig`."""
        self._name = ConfigOption(
            "name",
            (str,),
            default=NO_SETTING,
            valid_settings=(NO_SETTING,) + VALID_MANEUVER_DETECTION_LABELS,
        )
        self._threshold = ConfigOption("threshold", (float,), default=0.05)
        self._parameters = ConfigOption("parameters", (dict,), default={})

    @property
    def nested_items(self):
        """``list``: Return a list of :class:`.ConfigOption` objects that this section contains."""
        return [self._name, self._threshold, self._parameters]

    @property
    def name(self):
        """``str``: Name of metric to use."""
        return self._name.setting  # pylint: disable=no-member

    @property
    def threshold(self):
        """``float``: lower tail value for maneuver chi^2 threshold."""
        return self._threshold.setting  # pylint: disable=no-member

    @property
    def parameters(self):
        """``dict``: Parameters to use for the metric function."""
        return self._parameters.setting  # pylint: disable=no-member


class AdaptiveEstimationConfig(ConfigSection):
    """Configuration section defining adaptive estimation options."""

    CONFIG_LABEL = "adaptive_filter"
    """str: Key where settings are stored in the configuration dictionary read from file."""

    def __init__(self):
        """Construct an instance of a :class:`.AdaptiveEstimationConfig`.

        Note:
            Most default values come from Nastasi's dissertation
        """
        self._name = ConfigOption(
            "name",
            (str,),
            default=NO_SETTING,
            valid_settings=(NO_SETTING,) + VALID_ADAPTIVE_ESTIMATION_LABELS,
        )
        self._orbit_determination = ConfigOption(
            "orbit_determination",
            (str,),
            default="lambert_universal",
            valid_settings=VALID_ORBIT_DETERMINATION_LABELS,
        )
        self._model_interval = ConfigOption("model_interval", (int,), default=60)
        self._stacking_method = ConfigOption(
            "stacking_method", (str,), default="eci_stack", valid_settings=VALID_STACKING_LABELS
        )
        self._observation_window = ConfigOption("observation_window", (int,), default=3)
        self._prune_threshold = ConfigOption("prune_threshold", (float,), default=1e-20)
        self._prune_percentage = ConfigOption("prune_percentage", (float,), default=0.997)
        self._parameters = ConfigOption("parameters", (dict,), default={})

    @property
    def nested_items(self):
        """``list``: Return a list of :class:`.ConfigOption` that this section contains."""
        return [
            self._name,
            self._orbit_determination,
            self._model_interval,
            self._stacking_method,
            self._observation_window,
            self._prune_threshold,
            self._prune_percentage,
            self._parameters,
        ]

    @property
    def name(self):
        """``str``: Name of adaptive estimation method to use."""
        return self._name.setting

    @property
    def orbit_determination(self):
        """``float``: value for maneuver chi^2 threshold."""
        return self._orbit_determination.setting

    @property
    def model_interval(self):
        """``int``: Timestep between models in seconds."""
        return self._model_interval.setting

    @property
    def stacking_method(self):
        """``str``: name of coordinate system used for stacking models."""
        return self._stacking_method.setting

    @property
    def observation_window(self):
        """``int``: number of previous observations to go back to to start adaptive estimation."""
        return self._observation_window.setting

    @property
    def prune_threshold(self):
        """``float``: likelihood that a model has to be less than to be pruned off."""
        return self._prune_threshold.setting

    @property
    def prune_percentage(self):
        """``float``: percent likelihood a model has to meet to trigger mmae convergence."""
        return self._prune_percentage.setting

    @property
    def parameters(self):
        """``dict``: Parameters to use for the reward function specified by :attr:`.name`."""
        return self._parameters.setting
