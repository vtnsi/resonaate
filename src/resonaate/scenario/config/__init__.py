"""Subpackage defining how a :class:`.Scenario` can be configured."""
# Standard Library Imports
import os
# Package
from ...common.logger import resonaateLogWarning
from ...common.utilities import loadJSONFile, loadYAMLFile
from .base import ConfigObjectList, ConfigMissingRequiredError
from .geopotential_config import GeopotentialConfig
from .noise_config import NoiseConfig
from .propagation_config import PropagationConfig
from .time_config import TimeConfig
from .perturbations_config import PerturbationsConfig
from .event_configs import EventConfigObjectList
from .engine_config import EngineConfigObject
from .filter_config import FilterConfig


class ScenarioConfig:
    """Configuration class for creating valid :class:`.Scenario` objects.

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
        self.events = EventConfigObjectList()

        self.sections = (
            self.time, self.noise, self.propagation, self.geopotential, self.engines,
            self.perturbations, self.events, self.filter
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
        for section in self.sections:
            nested_config = config_dict.pop(section.config_label, None)
            if nested_config:
                section.readConfig(nested_config)

            elif section.isRequired() and not nested_config:
                raise ConfigMissingRequiredError("Scenario", section.config_label)

        # Log a warning if unused sections were included in the :class:`.Scenario` config
        if config_dict:
            msg = f"Scenario config included un-implemented sections: {config_dict.keys()}"
            resonaateLogWarning(msg)

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

        # Load the Tasking Engines
        engine_files = configuration.pop("engines_files")
        configuration["engines"] = []
        for engine_file in engine_files:
            engine_config = file_loader(os.path.join(config_file_path, engine_file))

            # Load the RSO target set
            targets = file_loader(os.path.join(config_file_path, engine_config["targets_file"]))

            # Load the sensor set
            sensors = file_loader(os.path.join(config_file_path, engine_config["sensors_file"]))

            engine_config.update({
                "targets": targets,
                "sensors": sensors
            })
            configuration["engines"].append(engine_config)

        return configuration

    @property
    def required_sections(self):
        """list: List of labels of required sections of :class:`.ScenarioConfig`."""
        return [section.config_label for section in self.sections if section.isRequired()]

    @property
    def optional_sections(self):
        """list: List of labels of optional sections of :class:`.ScenarioConfig`."""
        return [section.config_label for section in self.sections if not section.isRequired()]
