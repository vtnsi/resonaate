"""Submodule defining base classes for use in the ``scenario.config`` module."""
from __future__ import annotations

# Standard Library Imports
from abc import ABC, abstractmethod
from dataclasses import InitVar, dataclass, field, fields
from typing import TYPE_CHECKING, Sequence

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
        raise NotImplementedError()


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
        return f"Error occurred in '{self.config_label}': {self.message}"


class ConfigSettingError(BaseConfigError, ABC):
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
        return f"Setting '{self.config_label}' must be in types {self.requirements}, not {type(self.bad_setting)}"


class ConfigValueError(ConfigSettingError):
    """Exception thrown if configuration setting has a bad value."""

    def __str__(self) -> str:
        """``str``: string representation of this exception."""
        return f"Setting '{self.bad_setting}' for '{self.config_label} is not a valid setting: {self.requirements}"


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
        return f"Missing required '{self.missing}' in '{self.config_label}' config"


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


class ConfigObject(ABC):
    """Class for defining a configuration object."""

    @classmethod
    def getRequiredSections(cls) -> list[str]:
        """``list``: labels of required sections of :class:`.ScenarioConfig`."""
        # [NOTE]: Required fields **are not** in the class attributes before instantiation
        return [section.name for section in fields(cls) if not hasattr(cls, section.name)]

    @classmethod
    def getOptionalSections(cls) -> list[str]:
        """``list``: labels of optional sections of :class:`.ScenarioConfig`."""
        # [NOTE]: Optional fields **are** in the class attributes before instantiation
        return [section.name for section in fields(cls) if hasattr(cls, section.name)]


@dataclass
class ConfigObjectList(ConfigObject, Sequence[ConfigObject]):
    """Class for defining a configuration item that is a list of :class:`.ConfigObject` objects."""

    config_label: str
    """``str``: Label that this configuration item falls under in the raw configuration dictionary."""

    config_type: InitVar[ConfigObject]
    """``type``: type of the objects in this list."""

    _config_objects: list[ConfigObject] = field(default_factory=list)
    """``list``: config objects in this list."""

    default_empty: bool = False
    """``bool``: whether this list is empty by default. If ``False``, this list is required to be populated."""

    def __post_init__(self, config_type: ConfigObject) -> None:
        """Runs after the constructor has finished."""
        # [TODO]: Is this necessary?
        self._validateRawConfig(self._config_objects)
        config_objects = []
        for config_object in self._config_objects:
            if not isinstance(config_object, (config_type, dict)):
                raise ConfigTypeError(self.config_label, config_object, (config_type, dict))

            if isinstance(config_object, dict):
                if not config_object:
                    raise ConfigMissingRequiredError(self.config_label, config_type)
                config_objects.append(config_type(**config_object))
            else:
                config_objects.append(config_object)

        if not config_objects and not self.default_empty:
            # msg = f"At least one {self.config_type} is required, but an empty list was given: {config_objects}"
            raise ConfigMissingRequiredError(self.config_label, config_type)

        self._config_objects = config_objects

    def _validateRawConfig(self, raw_config: list[dict[str, Any]]) -> None:
        """Raise exceptions if types of `raw_config` are wrong.

        Args:
            raw_config (``list``): dictionaries that correspond to :attr:`.obj_type`.

        Raises:
            TypeError: If `raw_config` is not a list, or if the elements of `raw_config` aren't dictionaries.
            ValueError: If `raw_config` is empty, but :attr:`.default_empty` is ``False``.
        """
        if not isinstance(raw_config, list):
            raise ConfigTypeError(self.config_label, raw_config, (list,))

        if not raw_config:
            if not self.default_empty:
                raise ConfigMissingRequiredError("config", self.config_label)
            return

        for config_dict in raw_config:
            if not isinstance(config_dict, dict):
                raise ConfigTypeError(self.config_label, config_dict, (dict,))

    def __iter__(self) -> ConfigObject:
        """:class:`.ConfigObject`: iterates over the stored config objects."""
        for config_object in self.config_objects:
            yield config_object

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
