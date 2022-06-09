"""Submodule defining base classes for use in the ``scenario.config`` module."""
from abc import ABCMeta, abstractmethod


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
        """list: List of nested :class:`.ConfigItem`s."""
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
            if nested_config is None and item.isRequired():
                err = "Missing required key '{0}' in '{1}' section of Scenario config".format(
                    item.config_label,
                    self.config_label
                )
                raise KeyError(err)

            elif nested_config is not None:
                item.readConfig(nested_config)


class NoSettingType:
    """Type used for options that default to nothing.

    This type is used because ``None`` can't be used as a default (or manual) setting.
    """

    __SINGLETON = None

    @classmethod
    def getSingleton(cls):
        """Return a reference to :attr:`.__SINGLETON`."""
        if not cls.__SINGLETON:
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


NO_SETTING = NoSettingType.getSingleton()
"""NoSettingType: Singleton used for options that default to nothing."""


def inclusiveRange(*args, step=1):
    """Return a `range` object that includes the last number of the given range."""
    if len(args) == 1:
        start = 0
        stop = args[0] + 1
    elif len(args) == 2:
        start = args[0]
        stop = args[1] + 1
    elif len(args) == 3:
        start = args[0]
        stop = args[1] + 1
        step = args[2]
    else:
        err = "inclusiveRange expected 1-3 arguments, got {0}".format(len(args))
        raise TypeError(err)

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
        self.types = types + (NoSettingType, )
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
        elif self.default is not None:
            return self.default
        # else:
        err = "Required config '{0}' not set.".format(self._config_label)
        raise ValueError(err)

    def _validateSetting(self, new_setting):
        """Raise error if `new_setting` isn't valid.

        Args:
            new_setting (any): Setting to validate.

        Raises:
            TypeError: If `new_setting` doesn't match :attr:`.types`.
            ValueError: If :attr:`.valid_settings` is not ``None`` and `new_setting` isn't in it.
        """
        if not isinstance(new_setting, self.types):
            err = "Setting must be in types {0}, not {1}".format(self.types, type(new_setting))
            raise TypeError(err)

        if self.valid_settings:
            if new_setting not in self.valid_settings:
                err = "Setting '{0}' is not a valid setting: {1}".format(new_setting, self.valid_settings)
                raise ValueError(err)

    def isRequired(self):
        """Return a boolean indication of whether this :class:`.ConfigOption` is required."""
        return self.default is None

    @property
    def config_label(self):
        """str: Label that this configuration item falls under in the raw configuration dictionary."""
        return self._config_label

    @property
    def nested_items(self):
        """list: List of nested :class:`.ConfigItem`s.

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
    def getFields():
        """Returns a tuple of :class:`.ConfigOption`s defining the fields required for this :class:`.ConfigObject`."""
        raise NotImplementedError()

    def __init__(self, object_config):
        """Construct an instance of a :class:`.ConfigObject`.

        Args:
            object_config (dict): Configuration dictionary defining this :class:`.ConfigObject`.

        Raises:
            KeyError: If `object_config` is missing a field present in :attr:`.FIELDS`.
        """
        for field in self.getFields():
            config_setting = object_config.get(field.config_label)
            if config_setting is not None:
                field.readConfig(config_setting)

            if field.isRequired() and config_setting is None:
                err = "Missing required field '{0}' in '{1}' definition".format(
                    field.config_label,
                    self.__class__
                )
                raise KeyError(err)

            private_name = "_" + field.config_label
            setattr(self, private_name, field)


class ConfigObjectList(ConfigItem):
    """Class for defining a configuration item that is a list of :class:`.ConfigObject`s."""

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
        """list: List of nested :class:`.ConfigItem`s.

        The :attr:`.nested_items` attribute is a means to loop over the expected
        :class:`.ConfigItem`s that define the nesting object. Because :class:`.ConfigObjectList`
        doesn't have any inherit nested :class:`.ConfigItems` (just instantiated
        :class:`.ConfigObject`s accessible via :attr:`.objects`), this function returns an empty
        list.
        """
        return []

    def readConfig(self, raw_config):
        """Parse of list of object dictionaries and store them as :class:`.ConfigObject`s.

        Args:
            raw_config (list): List of dictionaries that correspond to :attr:`.obj_type`.
        """
        if not isinstance(raw_config, list):
            err = f"Cannot read config objects from type {type(raw_config)}"
            raise TypeError(err)

        if not raw_config:
            if not self.default_empty:
                err = "'{0}' list cannot be empty.".format(self.config_label)
                raise ValueError(err)
            return

        for config_dict in raw_config:
            if not isinstance(config_dict, dict):
                err = f"Cannot read config object from type {type(config_dict)}"
                raise TypeError(err)

            self._list.append(
                self.obj_type(config_dict)
            )

    @property
    def objects(self):
        """list: List of stored :class:`.ConfigObject`s."""
        if self._list or self.default_empty:
            return self._list
        # else:
        err = "Required config '{0}' not set.".format(self.config_label)
        raise ValueError(err)

    def isRequired(self):
        """Return a boolean indication of whether this :class:`.ConfigList` is required."""
        return not self.default_empty
