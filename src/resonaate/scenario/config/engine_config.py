"""Submodule defining the objects listed in the 'engines' configuration section."""
# Package
from ...sensors import ADV_RADAR_LABEL
from .base import ConfigObjectList, ConfigObject, ConfigError, ConfigOption
from .reward_config import RewardConfig
from .decision_config import DecisionConfig
from .agent_configs import TargetConfigObject, SensorConfigObject


class EngineConfigObject(ConfigObject):
    """Defines the structure for an object defined in the 'engines' configuration section."""

    @staticmethod
    def getFields():
        """Return a tuple of defining required :class:`.ConfigOption` objects for a :class:`.EngineConfigObject`."""
        return (
            ConfigOption("unique_id", (int, )),
            RewardConfig(),
            DecisionConfig(),
            ConfigObjectList("targets", TargetConfigObject),
            ConfigObjectList("sensors", SensorConfigObject)
        )

    def __init__(self, object_config):
        """Construct an instance of a :class:`.EngineConfigObject`.

        Args:
            object_config (dict): Configuration dictionary defining this
                :class:`.EngineConfigObject`.

        Raises:
            TypeError: If decision function being used is "AllVisibleDecision" and not all sensors
                defined in :attr:`.sensors` are advanced radars.
        """
        super().__init__(object_config)
        if self.decision.name == 'AllVisibleDecision':
            for sensor in self.sensors:
                if sensor.sensor_type != ADV_RADAR_LABEL:
                    err = "Only AdvRadar sensors can use the AllVisibleDecision"
                    err += f": sensor {sensor.id} is {sensor.sensor_type}"
                    raise ConfigError(self.__class__.__name__, err)

    @property
    def unique_id(self):
        """int: Unique ID for the defined engine."""
        return self._unique_id.setting  # pylint: disable=no-member

    @property
    def reward(self):
        """RewardConfig: Reward configuration section for the defined engine."""
        return self._reward  # pylint: disable=no-member

    @property
    def decision(self):
        """DecisionConfig: Decision configuration section for the defined engine."""
        return self._decision  # pylint: disable=no-member

    @property
    def targets(self):
        """list: List of :class:`.TargetConfigObject` objects that this engine can task."""
        return self._targets.objects  # pylint: disable=no-member

    @property
    def sensors(self):
        """list: List of :class:`.SensorConfigObject` objects that this engine can task."""
        return self._sensors.objects  # pylint: disable=no-member
