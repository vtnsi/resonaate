"""Submodule defining base classes for use in the ``scenario.config`` module."""
# Standard Library Imports
from abc import ABCMeta, abstractmethod
from typing import Tuple


class BaseConfigError(Exception, metaclass=ABCMeta):
    """Base exception for configuration errors."""

    def __init__(self, config_label):
        """Instantiate an exception dealing with a bad configuration setting.

        Args:
            config_label (str): Name of config setting causing error.
        """
        super().__init__(config_label)
        self.config_label = config_label

    @abstractmethod
    def __str__(self):
        """Return a string representation of this exception."""
        raise NotImplementedError()


class ConfigError(BaseConfigError):
    """Generic exception for configuration errors."""

    def __init__(self, config_label, message):
        """Instantiate an exception dealing with a bad configuration setting.

        Args:
            config_label (str): Name of config setting causing error.
            message (str): Message associated with error.
        """
        super().__init__(config_label)
        self.message = message

    def __str__(self):
        """Return a string representation of this exception."""
        return f"Error occurred in '{self.config_label}': {self.message}"


class ConfigSettingError(BaseConfigError, metaclass=ABCMeta):
    """Encapsulate shared functionality of subclasses."""

    def __init__(self, config_label, bad_setting, requirements):
        """Instantiate an exception dealing with a config setting error.

        Args:
            config_label (str): Name of config setting causing error.
            bad_setting (any): Value of setting causing error.
            requirements (any): Correct types or values for the setting causing error.
        """
        super().__init__(config_label)
        self.bad_setting = bad_setting
        self.requirements = requirements


class ConfigTypeError(ConfigSettingError):
    """Exception thrown if configuration setting has a bad type."""

    def __str__(self):
        """Return a string representation of this exception."""
        return f"Setting '{self.config_label}' must be in types {self.requirements}, not {type(self.bad_setting)}"


class ConfigValueError(ConfigSettingError):
    """Exception thrown if configuration setting has a bad value."""

    def __str__(self):
        """Return a string representation of this exception."""
        return f"Setting '{self.bad_setting}' for '{self.config_label} is not a valid setting: {self.requirements}"


class ConfigMissingRequiredError(BaseConfigError):
    """Exception thrown if required configuration setting is missing."""

    def __init__(self, config_label, missing):
        """Instantiate an exception dealing with a missing required configuration setting.

        Args:
            config_label (str): Name of config item causing error.
            missing (str): Name of missing config item.
        """
        super().__init__(config_label)
        self.missing = missing

    def __str__(self):
        """Return a string representation of this exception."""
        return f"Missing required '{self.missing}' in '{self.config_label}' config"


class ConfigItem(metaclass=ABCMeta):
    """Define a common interface for all configuration classes to share."""

    @property
    @abstractmethod
    def config_label(self):
        """str: Label that this configuration item falls under in the raw configuration dictionary."""
        raise NotImplementedError()

    @property
    @abstractmethod
    def nested_items(self):
        """list: List of nested :class:`.ConfigItem` objects."""
        raise NotImplementedError()

    @abstractmethod
    def isRequired(self):
        """Return a boolean indication of whether this :class:`.ConfigItem` is required."""
        raise NotImplementedError()

    def readConfig(self, raw_config):
        """Read the raw configuration to be stored in this :class:`.ConfigItem`.

        Args:
            raw_config (dict, list): Raw configuration settings to be read.
        """
        for item in self.nested_items:
            nested_config = raw_config.get(item.config_label)
            if nested_config is not None:
                try:
                    item.readConfig(nested_config)
                except BaseConfigError as inner_err:
                    raise ConfigError(self.config_label, str(inner_err)) from inner_err

            elif nested_config is None and item.isRequired():
                raise ConfigMissingRequiredError(item.config_label, self.config_label)


class NoSettingType:
    """Type used for options that default to nothing.

    This type is used because ``None`` can't be used as a default (or manual) setting.
    """

    __SINGLETON = None

    @classmethod
    def getSingleton(cls):
        """Return a reference to :attr:`.__SINGLETON`."""
        if cls.__SINGLETON is None:
            cls.__SINGLETON = cls()
        return cls.__SINGLETON

    def __deepcopy__(self, memo):
        """Custom ``deepcopy`` implementation so singleton isn't copied.

        Args:
            memo (dict): Memo dictionary ``deepcopy`` uses to track copied objects.

        Returns:
            NoSettingType: Singleton reference.
        """
        return self.getSingleton()

    def __bool__(self):
        """``bool``: Allows settings to be tested for truthiness."""
        return False

    def __len__(self):
        """``int``: Allows settings to be tested for truthiness."""
        return 0


NO_SETTING = NoSettingType.getSingleton()
"""NoSettingType: Singleton used for options that default to nothing."""


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


class ConfigOption(ConfigItem):
    """Defines a configuration setting for a single option."""

    def __init__(self, config_label, types, default=None, valid_settings=None):
        """Construct and instance of a :class:`.ConfigOption`.

        Args:
            config_label (str): Name of option as it appears in configuration file.
            types (tuple): Tuple of valid types for this :class:`.ConfigOption`.
            default (any,optional): The default setting for this :class:`.ConfigOption`.
            valid_settings (iterable,optional): List of settings that are valid for this
                :class:`.ConfigOption`.

        Raises:
            TypeError: If `default` doesn't match :attr:`.types`.
            ValueError: If :attr:`.valid_settings` is not ``None`` and `default` isn't in it.
        """
        self._config_label = config_label
        self.types = types + (NoSettingType,)
        self.valid_settings = valid_settings
        if default is not None:
            self._validateSetting(default)
        self.default = default
        self._setting = None

    @property
    def setting(self):
        """any: The current setting for this :class:`.ConfigOption`."""
        if self._setting is not None:
            return self._setting
        if self.default is not None:
            return self.default
        # else:
        raise ConfigMissingRequiredError("config", self.config_label)

    def _validateSetting(self, new_setting):
        """Raise error if `new_setting` isn't valid.

        Args:
            new_setting (any): Setting to validate.

        Raises:
            TypeError: If `new_setting` doesn't match :attr:`.types`.
            ValueError: If :attr:`.valid_settings` is not ``None`` and `new_setting` isn't in it.
        """
        if not isinstance(new_setting, self.types):
            raise ConfigTypeError(self.config_label, new_setting, self.types)

        if self.valid_settings:
            if new_setting not in self.valid_settings:
                raise ConfigValueError(self.config_label, new_setting, self.valid_settings)

    def isRequired(self):
        """Return a boolean indication of whether this :class:`.ConfigOption` is required."""
        return self.default is None

    @property
    def config_label(self):
        """str: Label that this configuration item falls under in the raw configuration dictionary."""
        return self._config_label

    @property
    def nested_items(self):
        """list: List of nested :class:`.ConfigItem` objects.

        A :class:`.ConfigOption` is expected to be a leaf node in the configuration hierarchy, and
        so it cannot have any nested items.
        """
        return []

    def readConfig(self, raw_config):
        """Read the raw configuration to be stored in this :class:`.ConfigItem`.

        Args:
            raw_config (any): Configuration setting to be read.
        """
        self._validateSetting(raw_config)
        self._setting = raw_config


class ConfigSection(ConfigItem, metaclass=ABCMeta):
    """Class that defines a section of a configuration which contains multiple options."""

    CONFIG_LABEL = ""
    """str: Key where settings are stored in the configuration dictionary read from file."""

    @property
    def config_label(self):
        """str: Label that this configuration item falls under in the raw configuration dictionary."""
        return self.CONFIG_LABEL

    def isRequired(self):
        """Return a boolean indication of whether this :class:`.ConfigSection` is required."""
        return any(option.isRequired() for option in self.nested_items)


class ConfigObject(metaclass=ABCMeta):
    """Class for defining a configuration object."""

    @staticmethod
    @abstractmethod
    def getFields() -> Tuple[ConfigItem]:
        """Returns tuple of :class:`.ConfigOption` defining the fields required for this :class:`.ConfigObject`."""
        raise NotImplementedError()

    def __init__(self, object_config: dict):
        """Construct an instance of a :class:`.ConfigObject`.

        Args:
            object_config (dict): Configuration dictionary defining this :class:`.ConfigObject`.

        Raises:
            KeyError: If `object_config` is missing a field present in :attr:`.FIELDS`.
        """
        for field in self.getFields():
            config_setting = object_config.get(field.config_label)
            if config_setting is not None:
                try:
                    field.readConfig(config_setting)
                except BaseConfigError as inner_err:
                    raise ConfigError(self.__class__.__name__, str(inner_err)) from inner_err

            if field.isRequired() and config_setting is None:
                raise ConfigMissingRequiredError(self.__class__.__name__, field.config_label)

            private_name = "_" + field.config_label
            setattr(self, private_name, field)


class ConfigObjectList(ConfigItem):
    """Class for defining a configuration item that is a list of :class:`.ConfigObject` objects."""

    def __init__(self, config_label, obj_type, default_empty=False):
        """Construct and instance of a :class:`.ConfigObjectList`.

        Args:
            config_label (str): Name of option as it appears in configuration file.
            obj_type (ConfigObject): Type of :class:`.ConfigObject` stored in this list.
            default_empty (bool): Flag indicating whether this list should be empty by default. If
                set to ``False``, this :class:`.ConfigObjectList` is required to be set by config.

        Raises:
            TypeError: If `default` doesn't match :attr:`.types`.
            ValueError: If :attr:`.valid_settings` is not ``None`` and `default` isn't in it.
        """
        self._config_label = config_label
        self.obj_type = obj_type
        self.default_empty = default_empty
        self._list = []

    @property
    def config_label(self):
        """str: Label that this configuration item falls under in the raw configuration dictionary."""
        return self._config_label

    @property
    def nested_items(self):
        """list: List of nested :class:`.ConfigItem` objects.

        The :attr:`.nested_items` attribute is a means to loop over the expected
        :class:`.ConfigItem` objects that define the nesting object. Because :class:`.ConfigObjectList`
        doesn't have any inherit nested :class:`.ConfigItem` objects (just instantiated
        :class:`.ConfigObject` objects accessible via :attr:`.objects`), this function returns an empty
        list.
        """
        return []

    def _validateRawConfig(self, raw_config):
        """Raise exceptions if types of `raw_config` are wrong.

        Args:
            raw_config (list): List of dictionaries that correspond to :attr:`.obj_type`.

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

    def readConfig(self, raw_config):
        """Parse of list of object dictionaries and store them as :class:`.ConfigObject` objects.

        Args:
            raw_config (list): List of dictionaries that correspond to :attr:`.obj_type`.
        """
        self._validateRawConfig(raw_config)

        for config_dict in raw_config:
            try:
                read_obj = self.obj_type(config_dict)
            except BaseConfigError as inner_err:
                raise ConfigError(self.config_label, str(inner_err)) from inner_err
            else:
                self._list.append(read_obj)

    @property
    def objects(self):
        """list: List of stored :class:`.ConfigObject` objects."""
        if self._list or self.default_empty:
            return self._list
        # else:
        raise ConfigMissingRequiredError("config", self.config_label)

    def isRequired(self):
        """Return a boolean indication of whether this :class:`.ConfigList` is required."""
        return not self.default_empty
