"""Define shared infrastructure for specifying configuration metadata."""

# Standard Library Imports
import logging
from argparse import ArgumentParser
from enum import Enum
from types import NoneType
from typing import NewType, Optional, Union, get_args

# Third Party Imports
from pydantic import BaseModel
from pydantic.fields import FieldInfo

_NotSet = NewType("_NotSet", NoneType)
"""Special type to specify a field was not set in a provided configuration.

Useful if a field can specifically be set to `None` by a user.
"""

NotSet = _NotSet(None)
"""Singleton access to :class:`._NotSet` instance."""

class EnvName:
    """Metadata annotation indicating how a field is expected to appear as an environment variable."""

    def __init__(self, env_name: str):
        """Specify the name of the environment variable that can be used to configure a field.

        Args:
            env_name: The name of the environment variable that can be used to configure a field.
        """
        self._env_name = env_name

    @property
    def name(self) -> str:
        """Name of the environment variable that can be used to configure a field."""
        return self._env_name


class CommandLineOptions:
    """Metadata annotation indicating how a field can be configured via command line arguments."""

    def __init__(self, *options: str):
        """Specify set of `options` that can be used to configure a field via command line arguments.

        Args:
            options: Set of command line arguemtns provided in the same manner as `ArgumentParser.add_argument()`.
        """
        self._options = []
        for each in options:
            if not each.startswith("-"):
                err = f"CommandLineOption must start with dash: {each}"
                raise ValueError(err)
            self._options.append(each)

    @property
    def options(self) -> list[str]:
        """List of command line options to access the configuration item being decorated."""
        return self._options


class LoggingLevel(str, Enum):
    """String enumeration of each valid logging level defined by the ``logging`` module."""

    DEBUG: str = "DEBUG"
    """Detailed information, typically only of interest to a developer trying to diagnose a problem."""

    INFO: str = "INFO"
    """Confirmation that things are working as expected."""

    WARNING: str = "WARNING"
    """An indication that something unexpected happened, but the software is still working as expected."""

    ERROR: str = "ERROR"
    """Due to a more serious problem, the software has not been able to perform some function."""

    CRITICAL: str = "CRITICAL"
    """A serious error, indicating that the program itself may be unable to continue running."""

    def level(self, _mapping={  # noqa: B006
        DEBUG: logging.DEBUG,
        INFO: logging.INFO,
        WARNING: logging.WARNING,
        ERROR: logging.ERROR,
        CRITICAL: logging.CRITICAL,
    }):
        """Helper method to map string enumerations to logging level definitons in ``logging`` modeul."""
        return _mapping[self]


class UserFieldInfo:
    """Specify the parameters of a user configuration field."""

    def __init__(self, field_name: str, field_info: FieldInfo):
        self._field_name = field_name
        self._field_info = field_info
        self._type_args = get_args(self._field_info.annotation)

        self._env_name = None
        self._cli_options = None
        for meta in self._field_info.metadata:
            if isinstance(meta, CommandLineOptions):
                self._cli_options = meta
            if isinstance(meta, EnvName):
                self._env_name = meta

    @property
    def field_name(self) -> str:
        """The name of this user configuration field."""
        return self._field_name

    @property
    def type_args(self) -> list[type]:
        """The types this user configuration field can be set with."""
        return self._type_args

    @property
    def env_name(self) -> Optional[EnvName]:
        """Environment variable name used to set this user configuration field."""
        return self._env_name

    @property
    def cli_options(self) -> Optional[CommandLineOptions]:
        """Command line options used to set this user configuration field."""
        return self._cli_options

    @property
    def description(self) -> str:
        """Pass thru to underlying ``FieldInfo.descrition``."""
        return self._field_info.description

    def is_required(self) -> bool:
        return self._field_info.is_required()

    def addToArgParser(self, arg_parser: ArgumentParser) -> bool:
        """If possible, add this user configuration to the specified `arg_parser`.

        Args:
            arg_parser: The :class:`.ArgumentParser` to add this user configuration to.

        Returns:
            Boolean indication of whether this user configuration was successfully added to the
                specified `arg_parser`.
        """
        if self.is_required():
            arg_parser.add_argument(self._field_name, help=self.description)
        else:
            if not self.cli_options:
                return False
            help_str = self.description
            default_str = f" Defaults to {self._field_info.get_default(call_default_factory=False)}."
            if self._field_info.default_factory:
                default_str = f" Defaults to value generated by '{self._field_info.default_factory.__name__}'."
            help_str += default_str
            if self.env_name:
                help_str += f"\n\nThis option can also be set via environment variable: {self.env_name.name}."

            kwargs = {
                "required": self.is_required(),
                "help": help_str,
                "dest": self.field_name,
            }

            for type_arg in self.type_args:
                if issubclass(type_arg, Enum):
                    kwargs["choices"] = [it.value for it in type_arg]

            arg_parser.add_argument(
                *self.cli_options.options,
                **kwargs,
            )
        return True


class UserSpec:

    def __init__(self, title: Optional[str] = None):
        self._title = title
        self._fields: dict[str, Union[UserFieldInfo, UserSpec]] = {}

    def addField(self, field_name: str, _spec):
        self._fields[field_name] = _spec

    def addToArgParser(self, arg_parser: ArgumentParser):
        if self._title is not None:
            arg_parser = arg_parser.add_argument_group(title=self._title)
        for user_info in self._fields.values():
            user_info.addToArgParser(arg_parser)


class UserConfig(BaseModel):

    @classmethod
    def buildUserSpec(cls, title: Optional[str] = None) -> UserSpec:
        user_spec = UserSpec(title)
        for field_name, field_info in cls.model_fields.items():
            try:
                _spec = field_info.annotation.buildUserSpec(title=field_name)
            except AttributeError:  # noqa: PERF203
                _spec = UserFieldInfo(field_name, field_info)
            user_spec.addField(field_name, _spec)
        return user_spec
