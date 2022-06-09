"""Submodule defining the 'event' configuration objects.

Todo:
    - Make "IMPULSE" a string constant defined somewhere sensible

"""
# Package
from .base import ConfigOption, ConfigObject


class TargetEventConfigObject(ConfigObject):
    """Defines the structure for an object defined in the 'target_events' configuration section."""

    @staticmethod
    def getFields():
        """Return a tuple of defining required :class:`.ConfigOption`s for a :class:`.TargetEventConfigObject`."""
        return (
            ConfigOption("affected_targets", (list, )),
            ConfigOption("event_type", (str, ), valid_settings=("IMPULSE", )),
            ConfigOption("delta_v", (list, ), default=None),
            ConfigOption("julian_date", (float, ))
        )

    def __init__(self, object_config):
        """Construct an instance of a :class:`.TargetEventConfigObject`."""
        super(TargetEventConfigObject, self).__init__(object_config)

        vector_size = len(self.delta_v)
        if vector_size != 3:
            err = "Delta vector defining an impulsive maneuver should be 3 dimensional, not {0}".format(vector_size)
            raise ValueError(err)

    @property
    def affected_targets(self):
        """list: List of target IDs that are affected by this event."""
        return self._affected_targets.setting  # pylint: disable=no-member

    @property
    def event_type(self):
        """str: Type of event this :class:`.TargetEventConfigObject` represents."""
        return self._event_type.setting  # pylint: disable=no-member

    @property
    def delta_v(self):
        """numpy.ndarray: Three-element vector defining an impulsive maneuver."""
        return self._delta_v.setting  # pylint: disable=no-member

    @property
    def julian_date(self):
        """float: Time that this event is supposed to take place during the scenario."""
        return self._julian_date.setting  # pylint: disable=no-member


class SensorEventConfigObject(ConfigObject):
    """Defines the structure for an object defined in the 'sensor_events' configuration section."""

    @staticmethod
    def getFields():
        """Return a tuple of defining required :class:`.ConfigOption`s for a :class:`.SensorEventConfigObject`."""
        raise NotImplementedError("Sensor events have not been implemented yet.")
