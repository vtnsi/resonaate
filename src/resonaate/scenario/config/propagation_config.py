"""Submodule defining the 'propagation' configuration section."""
# Package
from ...dynamics.constants import TWO_BODY_LABEL, SPECIAL_PERTURBATIONS_LABEL, RK45_LABEL, DOP853_LABEL
from .base import ConfigSection, ConfigOption


class PropagationConfig(ConfigSection):
    """Configuration section defining several propagation-based options."""

    CONFIG_LABEL = "propagation"
    """str: Key where settings are stored in the configuration dictionary read from file."""

    def __init__(self):
        """Construct an instance of a :class:`.PropagationConfig`."""
        self._propagation_model = ConfigOption(
            "propagation_model",
            (str, ),
            default=SPECIAL_PERTURBATIONS_LABEL,
            valid_settings=(TWO_BODY_LABEL, SPECIAL_PERTURBATIONS_LABEL)
        )
        self._integration_method = ConfigOption(
            "integration_method",
            (str, ),
            default=RK45_LABEL,
            valid_settings=(RK45_LABEL, DOP853_LABEL, )
        )
        self._station_keeping = ConfigOption("station_keeping", (bool, ), default=True)
        self._target_realtime_propagation = ConfigOption("target_realtime_propagation", (bool, ), default=True)
        self._sensor_realtime_propagation = ConfigOption("sensor_realtime_propagation", (bool, ), default=True)
        self._realtime_observation = ConfigOption("realtime_observation", (bool, ), default=True)

    @property
    def nested_items(self):
        """list: Return a list of :class:`.ConfigOption` objects that this section contains."""
        return [
            self._propagation_model, self._integration_method, self._station_keeping,
            self._target_realtime_propagation, self._sensor_realtime_propagation, self._realtime_observation
        ]

    @property
    def propagation_model(self):
        """str: String describing model with which to propagate RSOs."""
        return self._propagation_model.setting

    @property
    def integration_method(self):
        """str: String describing method with which to numerically integrate RSOs."""
        return self._integration_method.setting

    @property
    def station_keeping(self):
        """bool: Whether to use the station keeping for the truth model."""
        return self._station_keeping.setting

    @property
    def target_realtime_propagation(self):
        """bool: Whether to use the internal propgation for the truth model."""
        return self._target_realtime_propagation.setting

    @property
    def sensor_realtime_propagation(self):
        """bool: Whether to use the internal propgation for the truth model."""
        return self._sensor_realtime_propagation.setting

    @property
    def realtime_observation(self):
        """bool: Whether to generate observations during the simulation."""
        return self._realtime_observation.setting
