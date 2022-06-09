"""Submodule defining the 'reward' configuration section.

Todo:
    - Document :attr:`.RewardConfig.metrics`

    - Document :attr:`.RewardConfig.parameters`

"""
# Package
from .base import ConfigSection, ConfigOption, ConfigObject, ConfigObjectList
from ...tasking.rewards import VALID_REWARDS
from ...tasking.metrics import VALID_METRICS


class RewardConfig(ConfigSection):
    """Configuration section defining several reward-based options."""

    CONFIG_LABEL = "reward"
    """str: Key where settings are stored in the configuration dictionary read from file."""

    def __init__(self):
        """Construct an instance of a :class:`.RewardConfig`."""
        self._name = ConfigOption("name", (str, ), valid_settings=VALID_REWARDS)
        self._parameters = ConfigOption("parameters", (dict, ), default=dict())
        self._metrics = ConfigObjectList("metrics", MetricConfigObject)

    @property
    def nested_items(self):
        """list: Return a list of :class:`.ConfigOption`s that this section contains."""
        return [self._name, self._metrics, self._parameters]

    @property
    def name(self):
        """str: Name of this reward function."""
        return self._name.setting

    @property
    def metrics(self):
        """list: List of :class:`.MetricConfigObject`s."""
        return self._metrics.objects

    @property
    def parameters(self):
        """dict: Parameters to use for the reward function specified by :attr:`.name`."""
        return self._parameters.setting


class MetricConfigObject(ConfigObject):
    """:class:`.ConfigObject` to define a metric function."""

    @staticmethod
    def getFields():
        """Return a tuple of defining required :class:`.ConfigOption`s for a :class:`.MetricConfigObject`."""
        return (
            ConfigOption("name", (str, ), valid_settings=VALID_METRICS),
            ConfigOption("parameters", (dict, ), default={})
        )

    @property
    def name(self):
        """str: Name of metric to use."""
        return self._name.setting  # pylint: disable=no-member

    @property
    def parameters(self):
        """dict: Parameters to use for the metric function."""
        return self._parameters.setting  # pylint: disable=no-member
