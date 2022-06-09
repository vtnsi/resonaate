"""Defines a global set of configurations that define how the simulation operates."""
from __future__ import annotations

# Standard Library Imports
from configparser import ConfigParser
from configparser import Error as ConfigError
from importlib import resources
from logging import CRITICAL, DEBUG, ERROR, INFO, NOTSET, WARNING
from pathlib import Path
from typing import TYPE_CHECKING

# Type Checking Imports
if TYPE_CHECKING:
    # Standard Library Imports
    from typing import Any, Callable, Dict, List, Optional, Tuple

    # Third Party Imports
    from typing_extensions import Self


class SubConfig:
    """Class that represents a section in the configuration.

    Enforce improved config convention:
        `BehavioralConfig.section.value` rather than something like `BehavioralConfig["section"]["value"]`.
        While the latter is easier to implement, I believe the former method to be
        more intuitive and less prone to error.
    """

    def __init__(self, section: str):
        """Instantiate a `SubConfig` object.

        Args:
            section (``str``): name of section that this SubConfig object represents
        """
        self.section = section
        assert isinstance(self.section, str)

    def setonce(self, name: str, value: Any):
        """Set the field for this `SubConfig`, but raise an error if the field was already set.

        Args:
            name (``str``): name of field to set
            value (``any``): value to set the field to
        """
        already_set = getattr(self, name, None)
        if already_set is not None:
            raise AttributeError(
                f"SubConfig '{self.section}' already has a value set for '{name}':'{already_set}'"
            )
        setattr(self, name, value)


class CustomConfigParser(ConfigParser):
    """Perform custom parsing operations on our custom config convention."""

    LOGGING_LEVELS: Dict[str, int] = {
        "CRITICAL": CRITICAL,
        "ERROR": ERROR,
        "WARNING": WARNING,
        "INFO": INFO,
        "DEBUG": DEBUG,
        "NOTSET": NOTSET,
    }

    def getlogginglevel(self, section: str, option: str) -> int:
        """Return logging level for this config file."""
        got = self.get(section, option)

        return self.LOGGING_LEVELS.get(got, NOTSET)

    def getlist(self, section: str, option: str) -> List:
        """Return list for this option."""
        got = self.get(section, option)

        return [ii.lstrip() for ii in got.split(",")]

    def getNullInt(self, section: str, option: str) -> Optional[int]:
        """Return an int for this option, allowing for null values."""
        got = self.get(section, option)
        return None if got.lower() in ("null", "none") else int(got)


class BehavioralConfig:
    """Singleton, config settings class."""

    DEFAULT_CONFIG_FILE: str = "default_behavior.config"

    DEFAULT_SECTIONS: Dict[str, Dict[str, Any]] = {
        "logging": {
            "OutputLocation": "stdout",
            "Level": DEBUG,
            "MaxFileSize": 1048576,
            "MaxFileCount": 50,
            "AllowMultipleHandlers": False,
        },
        "database": {
            "DatabasePath": "sqlite://",
        },
        "parallel": {"RedisHostname": "localhost", "RedisPort": 6379, "WorkerCount": None},
        "debugging": {
            "OutputDirectory": "debugging",
            "NearestPD": False,
            "NearestPDDirectory": "cholesky_failure",
            "EstimateErrorInflation": False,
            "EstimateErrorInflationDirectory": "est_error_inflation",
            "ThreeSigmaObs": False,
            "ThreeSigmaObsDirectory": "three_sigma_obs",
            "SaveSpaceSensors": False,
            "SaveSpaceSensorsDirectory": "space_sensor_truth",
            "ParallelDebugMode": False,
        },
    }

    LOGGING_LEVEL_ITEMS: Dict[str, Tuple[str, ...]] = {"logging": ("Level",)}

    STR_ITEMS: Dict[str, Tuple[str, ...]] = {
        "logging": ("OutputLocation",),
        "database": ("DatabasePath",),
        "parallel": ("RedisHostname",),
        "debugging": (
            "OutputDirectory",
            "NearestPDDirectory",
            "EstimateErrorInflationDirectory",
            "ThreeSigmaObsDirectory",
            "SaveSpaceSensorsDirectory",
        ),
    }

    INT_ITEMS: Dict[str, Tuple[str, ...]] = {
        "logging": (
            "MaxFileSize",
            "MaxFileCount",
        ),
        "parallel": ("RedisPort",),
    }

    NULL_INT_ITEMS: Dict[str, Tuple[str, ...]] = {"parallel": ("WorkerCount",)}

    BOOL_ITEMS: Dict[str, Tuple[str, ...]] = {
        "logging": ("AllowMultipleHandlers",),
        "debugging": (
            "NearestPD",
            "EstimateErrorInflation",
            "ThreeSigmaObs",
            "SaveSpaceSensors",
            "ParallelDebugMode",
        ),
    }

    LIST_ITEMS: Dict[str, Tuple[str, ...]] = {}

    __shared_inst: Optional[BehavioralConfig] = None

    def __init__(self, config_file_path: Optional[str] = None):  # noqa: C901
        """Initialize the configuration object."""
        # pylint: disable=too-many-branches
        self._parser = CustomConfigParser()

        if config_file_path is None:
            with resources.path("resonaate.common", self.DEFAULT_CONFIG_FILE) as res_filepath:
                # Read in the config file if it exists, otherwise use the defaults
                with open(res_filepath, "r", encoding="utf-8") as config_file:
                    self._parser.read_file(config_file)

        elif Path(config_file_path).exists():
            # Read in the config file if it exists, otherwise use the defaults
            with open(config_file_path, "r", encoding="utf-8") as config_file:
                self._parser.read_file(config_file)

        for section, section_config in self.DEFAULT_SECTIONS.items():
            sub = SubConfig(section)
            for key, value in section_config.items():
                # Grab the appropriate `getter` object for each key
                getter: Callable[[str, str], Any]
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
                    raise Exception(
                        f"Configuration item '{section}::{key}' lacks a type classification."
                    )

                try:
                    value = getter(section, key)
                except ConfigError:
                    # Use default
                    pass
                finally:
                    sub.setonce(key, value)

            # Set this config object's `SubConfig`
            setattr(self, section, sub)

        BehavioralConfig.__shared_inst = self  # pylint: disable=unused-private-member

    @classmethod
    def getConfig(cls, config_file_path=DEFAULT_CONFIG_FILE) -> BehavioralConfig:
        """Return a reference to the singleton shared config."""
        if cls.__shared_inst is None:
            if not config_file_path:
                cls.__shared_inst = BehavioralConfig()

            else:
                cls.__shared_inst = BehavioralConfig(config_file_path=config_file_path)

        return cls.__shared_inst
