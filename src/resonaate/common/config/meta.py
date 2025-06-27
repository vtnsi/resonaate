"""Define shared infrastructure for specifying configuration metadata."""

from __future__ import annotations

# Standard Library Imports
import logging
from abc import ABC, abstractmethod
from contextlib import suppress
from enum import Enum
from os import environ
from types import NoneType
from typing import TYPE_CHECKING, Annotated, NewType, get_args

# Third Party Imports
from pydantic import BaseModel, Field, create_model

if TYPE_CHECKING:
    # Standard Library Imports
    from argparse import ArgumentParser

    # Third Party Imports
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


class UserSpec(ABC):
    """Encapsulate metadata associated with configuration items that can be set by the user."""

    def __init__(self, spec_title: str, spec_info: FieldInfo):
        """Initialize a :class:`.UserSpec`.

        Args:
            spec_title: String that labels this :class:`.UserSpec`.
            spec_info: The details of the specification.
        """
        self._title = spec_title
        self._info = spec_info

    @property
    def title(self) -> str:
        """The name corresponding to this :class:`.UserSpec`."""
        return self._title

    @property
    def description(self) -> str:
        """String describing the usage of this :class:`.UserSpec`."""
        return self._info.description

    def is_required(self) -> bool:
        """Return a boolean indication of whether this :class:`.UserSpec` is required."""
        return self._info.is_required()

    @abstractmethod
    def addToArgParser(self, arg_parser: ArgumentParser) -> bool:
        """If possible, add this :class:`.UserSpec` to the specified `arg_parser`.

        Args:
            arg_parser: The :class:`.ArgumentParser` to add this :class:`.UserSpec` to.

        Returns:
            Boolean indication of whether this :class:`.UserSpec` was successfully added to the
                specified `arg_parser`.
        """
        raise NotImplementedError

    @abstractmethod
    def retrieveUserInput(self, user_input: dict, parsed_args: dict, dotenv_vals: dict):
        """Retrieve user input for this configuration specification.

        Args:
            user_input: Mapping on which to store provided user input.
            parsed_args: Mapping of arguments parsed from the command line.
            dotenv_vals: Mapping of user input specified in a dotenv file.
        """
        raise NotImplementedError


class UserFieldInfo(UserSpec):
    """Specify the parameters of a user configuration field."""

    def __init__(self, field_name: str, field_info: FieldInfo):
        """Initialize a :class:`.UserFieldInfo`."""
        super().__init__(field_name, field_info)
        self._type_args = get_args(self._info.annotation)

        self._env_name = None
        self._cli_options = None
        for meta in self._info.metadata:
            if isinstance(meta, CommandLineOptions):
                self._cli_options = meta
            if isinstance(meta, EnvName):
                self._env_name = meta

    @property
    def type_args(self) -> list[type]:
        """The types this user configuration field can be set with."""
        return self._type_args

    @property
    def env_name(self) -> EnvName | None:
        """Environment variable name used to set this user configuration field."""
        return self._env_name

    @property
    def cli_options(self) -> CommandLineOptions | None:
        """Command line options used to set this user configuration field."""
        return self._cli_options

    def addToArgParser(self, arg_parser: ArgumentParser) -> bool:
        """If possible, add this user configuration to the specified `arg_parser`.

        Args:
            arg_parser: The :class:`.ArgumentParser` to add this user configuration to.

        Returns:
            Boolean indication of whether this user configuration was successfully added to the
                specified `arg_parser`.
        """
        if self.is_required():
            arg_parser.add_argument(self.title, help=self.description)
        else:
            if not self.cli_options:
                return False
            help_str = self.description
            default_str = f" Defaults to {self._info.get_default(call_default_factory=False)}."
            if self._info.default_factory:
                default_str = f" Defaults to value generated by '{self._info.default_factory.__name__}'."
            help_str += default_str
            if self.env_name:
                help_str += f"\n\nThis option can also be set via environment variable: {self.env_name.name}."

            kwargs = {
                "required": self.is_required(),
                "help": help_str,
                "dest": self.title,
            }

            for type_arg in self.type_args:
                if issubclass(type_arg, Enum):
                    kwargs["choices"] = [it.value for it in type_arg]

            arg_parser.add_argument(
                *self.cli_options.options,
                **kwargs,
            )
        return True

    def retrieveUserInput(self, user_input: dict, parsed_args: dict, dotenv_vals: dict):
        """Retrieve user input for this configuration specification.

        Input will be retrieved from the followng user input sources, with each subsequent source
        taking precedence over the previous if there are option conflicts:
         - Environment variables.
         - Variables set in dotenv file specified by `dotenv_vals`.
         - Variables specified as command line arguments.

        Args:
            user_input: Mapping on which to store provided user input.
            parsed_args: Mapping of arguments parsed from the command line.
            dotenv_vals: Mapping of user input specified in a dotenv file.
        """
        this_user_input = parsed_args.get(self.title, _NotSet)

        if self.env_name is not None and user_input is _NotSet:
            this_user_input = environ.get(self.env_name, _NotSet)
            this_user_input = dotenv_vals.get(self.env_name, _NotSet)

        if this_user_input is not _NotSet:
            user_input[self.title] = this_user_input


class UserFieldCollection(UserSpec):
    """Collection of :class:`.UserSpec` instances delineated by field names."""

    def __init__(self, spec_title, spec_info):
        """Initialize a :class:`.UserFieldCollection`."""
        super().__init__(spec_title, spec_info)
        self._field_collection: dict[str, UserSpec] = {}

    def addSpec(self, spec_title: str, spec_: UserSpec):
        """Add a :class:`.UserSpec` instance to this collection.

        Args:
            spec_title: How to delineate the :class:`.UserSpec` in this collection.
            spec_: The :class:`.UserSpec` being added.
        """
        self._field_collection[spec_title] = spec_

    def getSpec(self, spec_title: str) -> UserSpec:
        """Retrieve the specified :class:`.UserSpec` instance from this collection.

        Args:
            spec_title: Title that the desired :class:`.UserSpec` is mapped to.

        Returns:
            The :class:`.UserSpec` instance mapped to `spec_title`.

        Raises:
            AttributeError: If `spec_title` is not a valid mapping within this :class:`.UserFieldCollection`.
        """
        _got = self._field_collection.get(spec_title)
        if not _got:
            raise AttributeError
        return _got

    def addToArgParser(self, arg_parser: ArgumentParser) -> bool:
        """If possible, add this :class:`.UserFieldCollection` to the specified `arg_parser`.

        Args:
            arg_parser: The :class:`.ArgumentParser` to add this :class:`.UserFieldCollection` to.

        Returns:
            Boolean indication of whether this :class:`.UserFieldCollection` was successfully added to the
                specified `arg_parser`.
        """
        # [TODO]: Find a way to group arguments?
        for field in self._field_collection.values():
            field.addToArgParser(arg_parser)
        return True

    def retrieveUserInput(self, user_input: dict, parsed_args: dict, dotenv_vals: dict):
        """Recursively retrieve user input for each field in this collection.

        Args:
            user_input: Mapping on which to store provided user input.
            parsed_args: Mapping of arguments parsed from the command line.
            dotenv_vals: Mapping of user input specified in a dotenv file.
        """
        this_user_input = {}
        for spec in self._field_collection.values():
            spec.retrieveUserInput(this_user_input, parsed_args, dotenv_vals)
        if this_user_input:
            user_input[self.title] = this_user_input


def userSpecFactory(spec_title: str, spec_info: FieldInfo | BaseModel) -> UserSpec:
    """Recursively build a :class:`.UserSpec`.

    Args:
        spec_title: The title of the root specification to build from.
        spec_info: The root specification to build from.

    Returns:
        A fully populated :class:`.UserSpec` object.
    """
    is_pydantic_model = False
    with suppress(TypeError):
        is_pydantic_model = issubclass(spec_info, BaseModel)
    if is_pydantic_model:
        _wrapper = create_model(f"{spec_info.__name__}_wrapper", wrapped=Annotated[spec_info, Field()])
        wrapped_field_info = next(iter(_wrapper.model_fields.values()))
        return userSpecFactory(spec_info.__name__, wrapped_field_info)

    is_annotated_model = False
    with suppress(TypeError, AttributeError):
        is_annotated_model = issubclass(spec_info.annotation, BaseModel)
    if is_annotated_model:
        collection = UserFieldCollection(spec_title, spec_info)
        for field_name, field_info in spec_info.annotation.model_fields.items():
            collection.addSpec(field_name, userSpecFactory(field_name, field_info))
        return collection

    # else:
    return UserFieldInfo(spec_title, spec_info)
