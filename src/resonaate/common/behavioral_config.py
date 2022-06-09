# Standard Library Imports
import os.path
from configparser import ConfigParser, Error as ConfigError
from logging import CRITICAL, ERROR, WARNING, INFO, DEBUG, NOTSET
# Third Party Imports
# RESONAATE Imports


class SubConfig:
    """Class that represents a section in the configuration.

    Enforce improved config convention:
        `BehavioralConfig.section.value` rather than something like `BehavioralConfig["section"]["value"]`.
        While the latter is easier to implement, I believe the former method to be
        more intuitive and less prone to error.
    """

    def __init__(self, section):
        """Instantiate a `SubConfig` object.

        @param section \b str -- name of section that this SubConfig object represents
        """
        self.section = section
        assert isinstance(self.section, str)

    def setonce(self, name, value):
        """Set the field for this `SubConfig`, but raise an error if the field was already set.

        @param name \b str -- name of field to set
        @param value \b any -- value to set the field to
        """
        already_set = getattr(self, name, None)
        if already_set is not None:
            raise AttributeError("SubConfig '{0}' already has a value set for '{1}':'{2}'".format(
                self.section,
                name,
                already_set
            ))
        setattr(self, name, value)


class CustomConfigParser(ConfigParser):
    """Perform custom parsing operations on our custom config convention."""

    LOGGING_LEVELS = {
        "CRITICAL": CRITICAL,
        "ERROR": ERROR,
        "WARNING": WARNING,
        "INFO": INFO,
        "DEBUG": DEBUG,
        "NOTSET": NOTSET
    }

    def getlogginglevel(self, section, option):
        """Return logging level for this config file."""
        got = self.get(section, option)

        return self.LOGGING_LEVELS.get(got, NOTSET)

    def getlist(self, section, option):
        """Return list for this option."""
        got = self.get(section, option)

        return [ii.lstrip() for ii in got.split(',')]

    def getNullInt(self, section, option):
        """Return an int for this option, allowing for null values."""
        got = self.get(section, option)
        return None if got.lower() in ('null', 'none') else int(got)


class BehavioralConfig:
    """Singleton, config settings class."""

    DEFAULT_CONFIG_FILE = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "default_behavior.config"
    )

    DEFAULT_SECTIONS = {
        "logging": {
            "OutputLocation": "stdout",
            "Level": DEBUG,
            "MaxFileSize": 1048576,
            "MaxFileCount": 50,
            "AllowMultipleHandlers": False
        },
        "database": {
            "DatabaseURL": "sqlite://",
        },
        "parallel":{
            "RedisHostname": 'localhost',
            "RedisPort": 6379,
            "WorkerCount": None
        },
        "debugging": {
            "OutputDirectory": 'debugging',
            "NearestPD": False,
            "NearestPDDirectory": 'cholesky_failure',
            "EstimateErrorInflation": False,
            "EstimateErrorInflationDirectory": 'est_error_inflation',
            "ThreeSigmaObs": False,
            "ThreeSigmaObsDirectory": 'three_sigma_obs',
            "SaveSpaceSensors": False,
            "SaveSpaceSensorsDirectory": 'space_sensor_truth',
            "SingularMatrix": False,
            "SingularMatrixDirectory": 'singular_matrix',
            "ParallelDebugMode": False,
        }
    }

    LOGGING_LEVEL_ITEMS = {
        "logging": ("Level", )
    }

    STR_ITEMS = {
        "logging": ("OutputLocation", ),
        "database": ("DatabaseURL", ),
        "parallel": ("RedisHostname", ),
        "debugging": (
            "OutputDirectory", "NearestPDDirectory", "EstimateErrorInflationDirectory",
            "ThreeSigmaObsDirectory", "SaveSpaceSensorsDirectory", "SingularMatrixDirectory",
        )
    }

    INT_ITEMS = {
        "logging": ("MaxFileSize", "MaxFileCount", ),
        "parallel": ("RedisPort", )
    }

    NULL_INT_ITEMS = {
        "parallel": ("WorkerCount", )
    }

    BOOL_ITEMS = {
        "logging": ("AllowMultipleHandlers", ),
        "debugging": (
            "NearestPD", "EstimateErrorInflation", "ThreeSigmaObs", "SaveSpaceSensors",
            "SingularMatrix", "ParallelDebugMode"
        )
    }

    __shared_inst = None

    def __init__(self, config_file_path=DEFAULT_CONFIG_FILE):  # noqa: C901
        """Initialize the configuration object."""
        self._parser = CustomConfigParser()

        if os.path.exists(config_file_path):
            # Read in the config file if it exists, otherwise use the defaults
            with open(config_file_path, 'r') as config_file:
                self._parser.read_file(config_file)

        for section, section_config in self.DEFAULT_SECTIONS.items():
            sub = SubConfig(section)
            for key in section_config:
                # Grab the appropriate `getter` object for each key
                if key in self.STR_ITEMS.get(section, tuple()):
                    getter = self._parser.get

                elif key in self.INT_ITEMS.get(section, tuple()):
                    getter = self._parser.getint

                elif key in self.BOOL_ITEMS.get(section, tuple()):
                    getter = self._parser.getboolean

                elif key in self.LOGGING_LEVEL_ITEMS.get(section, tuple()):
                    getter = self._parser.getlogginglevel

                elif key in self.NULL_INT_ITEMS.get(section, tuple()):
                    getter = self._parser.getNullInt

                elif key in self.LIST_ITEMS.get(section, tuple()):
                    getter = self._parser.getlist

                else:
                    raise Exception("Configuration item '{0}::{1}' lacks a type classification.".format(section, key))

                try:
                    value = getter(section, key)
                except ConfigError:
                    value = self.DEFAULT_SECTIONS[section][key]
                finally:
                    sub.setonce(key, value)

            # Set this config object's `SubConfig`
            setattr(self, section, sub)

        BehavioralConfig.__shared_inst = self

    @classmethod
    def getConfig(cls, config_file_path=DEFAULT_CONFIG_FILE):
        """Return a reference to the singleton shared config."""
        if cls.__shared_inst is None:
            if not config_file_path:
                cls.__shared_inst = BehavioralConfig()

            else:
                cls.__shared_inst = BehavioralConfig(config_file_path=config_file_path)

        return cls.__shared_inst
