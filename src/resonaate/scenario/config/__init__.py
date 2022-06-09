"""Submodule defining how a :class:`.Scenario` can be configured."""
# Standard Library Imports
from logging import getLogger
import os
# Package
from ...common.utilities import loadJSONFile, loadYAMLFile
from .base import ConfigObjectList
from .geopotential_config import GeopotentialConfig
from .noise_config import NoiseConfig
from .propagation_config import PropagationConfig
from .time_config import TimeConfig
from .perturbations_config import PerturbationsConfig
from .event_configs import TargetEventConfigObject, SensorEventConfigObject
from .engine_config import EngineConfigObject
from .filter_config import FilterConfig


class ScenarioConfig:
    """Configuration class for creating valid :class:`.Scenario`s.

    This allows the extra logic for properly checking all configs to be abstracted from the
    factory methods and the :class:`.Scenario`'s constructor.
    """

    def __init__(self):
        """Instantiate a :class:`.ScenarioConfig` object from a dictionary."""
        self.time = TimeConfig()
        self.noise = NoiseConfig()
        self.propagation = PropagationConfig()
        self.geopotential = GeopotentialConfig()
        self.engines = ConfigObjectList("engines", EngineConfigObject)
        self.perturbations = PerturbationsConfig()
        self.filter = FilterConfig()
        self.target_events = ConfigObjectList("target_events", TargetEventConfigObject, default_empty=True)
        self.sensor_events = ConfigObjectList("sensor_events", SensorEventConfigObject, default_empty=True)

        self.sections = (
            self.time, self.noise, self.propagation, self.geopotential, self.engines,
            self.perturbations, self.target_events, self.sensor_events, self.filter
        )

    @classmethod
    def fromConfigFile(cls, config_file_path):
        """Parse a configuration file and generate a :class:`.ScenarioConfig` from it.

        Args:
            config_file_path (str): Path to initialization configuration file.

        Returns:
            ScenarioConfig: Generated from configuration file.
        """
        config_dict = cls.parseConfigFile(config_file_path)
        config = cls()
        config.readConfig(config_dict)

        return config

    def readConfig(self, config_dict):
        """Read a configuration dictionary into this :class:`.ScenarioConfig`.

        Args:
            config_dict (dict): Config dictionary specifying :class:`.Scenario` attributes.
        """
        logger = getLogger("resonaate")
        for section in self.sections:
            nested_config = config_dict.pop(section.config_label, None)
            if section.isRequired() and not nested_config:
                logger.error("Missing required section '{0}' in the Scenario config".format(
                    section.config_label
                ))
                raise KeyError(section.config_label)

            elif nested_config:
                section.readConfig(nested_config)

        # Log a warning if unused sections were included in the :class:`.Scenario` config
        if config_dict:
            logger.warning(
                "Scenario config included un-implemented sections: {0}".format(config_dict.keys())
            )

    @staticmethod
    def parseConfigFile(path):
        """Parse out configuration from a given filepath.

        Args:
            path (``str``): path to main config file

        Returns:
            ``dict``: config dictionary object with the necessary fields
        """
        if path.endswith("json"):
            file_loader = loadJSONFile
        elif path.endswith("yaml"):
            file_loader = loadYAMLFile
        else:
            raise ValueError(path)

        # Load the main config, and save the path
        config_file_path = os.path.dirname(os.path.abspath(path))
        configuration = file_loader(path)

        # Load target events
        target_events = None
        target_events_file = configuration.pop("target_events_file", None)
        if target_events_file:
            target_events = file_loader(os.path.join(config_file_path, target_events_file))
        configuration["target_events"] = target_events

        # Load sensor events
        sensor_events = None
        sensor_events_file = configuration.pop("sensor_events_file", None)
        if sensor_events_file:
            sensor_events = file_loader(os.path.join(config_file_path, sensor_events_file))
        configuration["sensor_events"] = sensor_events

        # Load the Tasking Engines
        engine_files = configuration.pop("engines_files")
        configuration["engines"] = []
        for engine_file in engine_files:
            engine_config = file_loader(os.path.join(config_file_path, engine_file))

            # Load the RSO target set
            targets = file_loader(os.path.join(config_file_path, engine_config["targets_file"]))

            # Load the sensor set
            sensors = file_loader(os.path.join(config_file_path, engine_config["sensors_file"]))

            configuration["engines"].append({
                "targets": targets,
                "sensors": sensors,
                "reward": engine_config["reward"],
                "decision": engine_config["decision"]
            })

        return configuration

    @property
    def required_sections(self):
        """list: List of labels of required sections of :class:`.ScenarioConfig`."""
        return [section.config_label for section in self.sections if section.isRequired()]

    @property
    def optional_sections(self):
        """list: List of labels of optional sections of :class:`.ScenarioConfig`."""
        return [section.config_label for section in self.sections if not section.isRequired()]
