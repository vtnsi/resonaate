"""Submodule defining base classes for use in the ``scenario.config`` module."""
from __future__ import annotations

# Standard Library Imports
from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import MISSING, InitVar, dataclass, field, fields
from typing import TYPE_CHECKING

# Type Checking Imports
if TYPE_CHECKING:
    # Standard Library Imports
    from typing import Any


class BaseConfigError(Exception, ABC):
    """Base exception for configuration errors."""

    def __init__(self, config_label: str) -> None:
        """Instantiate an exception dealing with a bad configuration setting.

        Args:
            config_label (``str``): Name of config setting causing error.
        """
        super().__init__(config_label)
        self.config_label = config_label

    @abstractmethod
    def __str__(self) -> str:
        """``str``: string representation of this exception."""
        raise NotImplementedError


class ConfigError(BaseConfigError):
    """Generic exception for configuration errors."""

    def __init__(self, config_label: str, message: str) -> None:
        """Instantiate an exception dealing with a bad configuration setting.

        Args:
            config_label (``str``): Name of config setting causing error.
            message (``str``): Message associated with error.
        """
        super().__init__(config_label)
        self.message = message

    def __str__(self) -> str:
        """``str``: string representation of this exception."""
        return f"Error occurred in {self.config_label!r}: {self.message}"


class ConfigSettingError(BaseConfigError):
    """Encapsulate shared functionality of subclasses."""

    def __init__(self, config_label: str, bad_setting: Any, requirements: tuple) -> None:
        """Instantiate an exception dealing with a config setting error.

        Args:
            config_label (``str``): Name of config setting causing error.
            bad_setting (``Any``): Value of setting causing error.
            requirements (``tuple``): Correct types or values for the setting causing error.
        """
        super().__init__(config_label)
        self.bad_setting = bad_setting
        self.requirements = requirements


class ConfigTypeError(ConfigSettingError):
    """Exception thrown if configuration setting has a bad type."""

    def __str__(self) -> str:
        """``str``: string representation of this exception."""
        return f"Setting {self.config_label!r} must be in types {self.requirements}, not {type(self.bad_setting)}"


class ConfigValueError(ConfigSettingError):
    """Exception thrown if configuration setting has a bad value."""

    def __str__(self) -> str:
        """``str``: string representation of this exception."""
        return f"Setting {self.bad_setting!r} for {self.config_label!r} is not a valid setting: {self.requirements}"


class ConfigMissingRequiredError(BaseConfigError):
    """Exception thrown if required configuration setting is missing."""

    def __init__(self, config_label: str, missing: str) -> None:
        """Instantiate an exception dealing with a missing required configuration setting.

        Args:
            config_label (``str``): Name of config item causing error.
            missing (``str``): Name of missing config item.
        """
        super().__init__(config_label)
        self.missing = missing

    def __str__(self) -> str:
        """``str``: string representation of this exception."""
        return f"Missing required {self.missing!r} in {self.config_label!r} config"


def inclusiveRange(*args):
    """Return a `range` object that includes the last number of the given range."""
    if len(args) not in (1, 2, 3):
        err = f"inclusiveRange expected 1-3 arguments, got {len(args)}"
        raise TypeError(err)
    step = 1 if len(args) < 3 else args[2]
    start = 0 if len(args) < 2 else args[0]
    stop = args[0] if len(args) < 2 else args[1]
    stop += 1

    return range(start, stop, step)


class ConfigObject:
    """Class for defining a configuration object."""

    @classmethod
    def getRequiredFields(cls) -> list[str]:
        """``list``: labels of required fields of a config object."""
        # [NOTE]: Required fields define neither a `default` nor a `default_factory` attribute
        #   This is the most robust way to determine this.
        return [
            section.name
            for section in fields(cls)
            if section.default == MISSING and section.default_factory == MISSING
        ]

    @classmethod
    def getOptionalFields(cls) -> list[str]:
        """``list``: labels of optional fields of a config object."""
        # [NOTE]: Optional fields define either a `default` or `default_factory` attribute
        #   This is the most robust way to determine this.
        return [
            section.name
            for section in fields(cls)
            if section.default != MISSING or section.default_factory != MISSING
        ]


@dataclass
class ConfigObjectList(ConfigObject, Sequence[ConfigObject]):
    """Class for defining a configuration item that is a list of :class:`.ConfigObject` objects."""

    config_label: str
    """``str``: Label that this configuration item falls under in the raw configuration dictionary."""

    config_type: InitVar[type[ConfigObject]]
    """``type``: type of the objects in this list.

    :meta private:
    """

    _config_objects: list[ConfigObject] = field(default_factory=list)
    """``list``: config objects in this list."""

    default_empty: bool = False
    """``bool``: whether this list is empty by default. If ``False``, this list is required to be populated."""

    def __post_init__(self, config_type: type[ConfigObject]) -> None:
        """Runs after the constructor has finished.

        Args:
            config_type (``type(ConfigObject)``): a reference to the contained :class:`.ConfigObject` class type.
        """
        self._validateRawConfig(self._config_objects, config_type)
        config_objects = []
        for config_object in self._config_objects:
            if isinstance(config_object, dict):
                config_objects.append(config_type(**config_object))
            else:
                config_objects.append(config_object)

        self._config_objects = config_objects

    def _validateRawConfig(
        self, raw_config: list[dict[str, Any]], config_type: type[ConfigObject]
    ) -> None:
        """Raise exceptions if types of `raw_config` are wrong.

        Args:
            raw_config (``list``): dictionaries that correspond to :attr:`.obj_type`.
            config_type (``type(ConfigObject)``): a reference to the contained :class:`.ConfigObject` class type.

        Raises:
            TypeError: If `raw_config` is not a list, or if the elements of `raw_config` aren't dictionaries.
            ValueError: If `raw_config` is empty, but :attr:`.default_empty` is ``False``.
        """
        # Must be a input list
        if not isinstance(raw_config, list):
            raise ConfigTypeError(self.config_label, raw_config, (list,))

        if not raw_config:
            # Empty, but default_empty = False
            if not self.default_empty:
                raise ConfigMissingRequiredError("config", self.config_label)
            return

        for config in raw_config:
            # Not an object or a dict
            if not isinstance(config, (config_type, dict)):
                raise ConfigTypeError(self.config_label, config, (config_type, dict))

            # An empty dictionary in the list
            if isinstance(config, dict) and not config:
                raise ConfigMissingRequiredError(self.config_label, config_type)

    def __iter__(self) -> ConfigObject:
        """:class:`.ConfigObject`: iterates over the stored config objects."""
        yield from self.config_objects

    def __getitem__(self, index: int) -> ConfigObject:
        """:class:`.ConfigObject`: returns the config object at the given index."""
        return self.config_objects[index]

    def __len__(self) -> int:
        """``int``: number of config objects in this list."""
        return len(self.config_objects)

    @property
    def config_objects(self) -> list[ConfigObject]:
        """``list``: stored config objects."""
        if self._config_objects or self.default_empty:
            return self._config_objects
        # else:
        raise ConfigMissingRequiredError("config", self.config_label)

    @property
    def required(self) -> bool:
        """``bool``: whether this config object list is required."""
        return not self.default_empty
