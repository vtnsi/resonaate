"""Submodule defining the 'time' configuration section."""
# Standard Library
from datetime import datetime
# Package
from .base import ConfigSection, ConfigOption


class TimeConfig(ConfigSection):
    """Configuration section defining several time-based options."""

    CONFIG_LABEL = "time"
    """str: Key where settings are stored in the configuration dictionary read from file."""

    def __init__(self):
        """Construct an instance of a :class:`.TimeConfig`."""
        self._start_timestamp = ConfigOption("start_timestamp", (str, datetime, ))
        self._physics_step_sec = ConfigOption("physics_step_sec", (int, ), default=60)
        self._output_step_sec = ConfigOption("output_step_sec", (int, ), default=60)
        self._stop_timestamp = ConfigOption("stop_timestamp", (str, datetime, ))

    @property
    def nested_items(self):
        """list: Return a list of :class:`.ConfigOption`s that this section contains."""
        return [self._start_timestamp, self._physics_step_sec, self._output_step_sec, self._stop_timestamp]

    @property
    def start_timestamp(self):
        """datetime: Time for the scenario to start."""
        if isinstance(self._start_timestamp.setting, str):
            self._start_timestamp.readConfig(datetime.strptime(
                self._start_timestamp.setting,
                "%Y-%m-%dT%H:%M:%S.%fZ"
            ))
        return self._start_timestamp.setting

    @property
    def physics_step_sec(self):
        """int: Timestep used for propagation. Defaults to 60 seconds."""
        return self._physics_step_sec.setting

    @property
    def output_step_sec(self):
        """int: Timestep used for outputting data. Defaults to 60 seconds."""
        return self._physics_step_sec.setting

    @property
    def stop_timestamp(self):
        """datetime: Time for the scenario to stop."""
        if isinstance(self._stop_timestamp.setting, str):
            self._stop_timestamp.readConfig(datetime.strptime(
                self._stop_timestamp.setting,
                "%Y-%m-%dT%H:%M:%S.%fZ"
            ))
        return self._stop_timestamp.setting
