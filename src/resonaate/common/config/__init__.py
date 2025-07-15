"""Module defining common configuration formats."""
from __future__ import annotations

# Standard Library Imports
import json
import sys
from argparse import ArgumentParser, RawTextHelpFormatter
from enum import Enum
from functools import cache
from os import environ
from pathlib import Path

# Third Party Imports
from dotenv import dotenv_values

# Local Imports
from .behavioral import BehavioralConfig
from .input_output import InputConfig, OutputDbUrlSpec
from .meta import NotSet, UserBaseModel, UserSpec, userSpecFactory


class EntrypointConfig(UserBaseModel):
    """Configuration that must be provided for RESONAATE when run from the command line."""

    input_config: InputConfig
    """Collection of configuration options pertaining to RESONAATE's inputs."""

    output_config: OutputDbUrlSpec = OutputDbUrlSpec()
    """Collection of configuration options pertaining to RESONAATE's outputs."""

    behavioral_config: BehavioralConfig = BehavioralConfig()
    """Collection of configuration options pertaining to RESONAATE's behavior."""


class LibraryConfig(UserBaseModel):
    """Configuration available when RESONAATE is utilized as a library."""

    output_config: OutputDbUrlSpec = OutputDbUrlSpec()
    """Collection of configuration options pertaining to RESONAATE's outputs."""

    behavioral_config: BehavioralConfig = BehavioralConfig()
    """Collection of configuration options pertaining to RESONAATE's behavior."""


_ARGS_ENV_LOC: str = "RESONAATE_ARGS"
"""Key of environment variable to store CLI args to for child processes to consume."""


def putResonaateArgs(cli_args: list[str] | None = None, env_loc: str = _ARGS_ENV_LOC):
    """Store CLI args provided to RESONAATE on the environment.

    Args:
        cli_args: List of string command line arguments.
        env_loc: Environment variable specifying where to store the command line arguments.
    """
    if cli_args is None:
        cli_args = sys.argv[1:]
    environ[env_loc] = json.dumps(cli_args)


def getResonaateArgs(env_loc: str = _ARGS_ENV_LOC) -> list[str]:
    """Retrieve the CLI arguments stored on the environment by RESONAATE entrypoint.

    Args:
        env_loc: Environment variable specifying where the command line arguments are stored.
    """
    no_args = "[]"
    return json.loads(environ.get(env_loc, default=no_args))


@cache
def rootConfigSpec(root_config: EntrypointConfig | LibraryConfig) -> UserSpec:
    """Build the :class:`.UserSpec` describing a :class:`.RootConfig` model."""
    return userSpecFactory(root_config.__name__, root_config)


@cache
def getConfig(root_config: RootConfig) -> EntrypointConfig | LibraryConfig:
    """Retrieve the (possibly cached) :class:`.RootConfig` object built from default user input."""
    return root_config.factory()


class RootConfig(Enum):
    """Enumeration of root configuration structures."""

    ENTRY = EntrypointConfig
    """Configuration that must be provided for RESONAATE when run from the command line."""

    LIB = LibraryConfig
    """Configuration available when RESONAATE is utilized as a library."""

    def getSpec(self):
        """Build the :class:`.UserSpec` describing this :class:`.RootConfig` model."""
        return rootConfigSpec(self.value)

    def getCommandLineParser(self) -> ArgumentParser:
        """Build command line argument parser based on this :class:`.RootConfig`."""
        parser = ArgumentParser(
            description="RESONAATE Command Line Interface",
            argument_default=NotSet,
            formatter_class=RawTextHelpFormatter,
        )
        self.getSpec().addToArgParser(parser)
        return parser

    def factory(self, cli_args: list[str] | None = None, dotenv_path: Path = Path("resonaate.env")):
        """Instantiate a :class:`.RootConfig` object based on user input.

        The resultant :class:`.RootConfig` object will be built from the followng user input sources,
        with each subsequent source taking precedence over the previous if there are option conflicts:
        - Environment variables.
        - Variables set in dotenv file specified by `dotenv_path`.
        - Variables specified as command line arguments.

        Args:
            cli_args: Command line arguments specifying user input.
            dotenv_path: Path to dotenv file specifying user intput.
        """
        resonaate_dotenv = dotenv_values(dotenv_path)
        if cli_args is None:
            cli_args = getResonaateArgs()
        parsed_args = self.getCommandLineParser().parse_args(cli_args)

        config_dict = {}
        self.getSpec().retrieveUserInput(config_dict, vars(parsed_args), resonaate_dotenv)
        if self.value.__name__ in config_dict:
            config_dict = config_dict[self.value.__name__]  # need nested dict to match models

        return self.value(**config_dict)

    def inst(self) -> EntrypointConfig | LibraryConfig:
        """Retrieve the (possibly cached) :class:`.RootConfig` object built from default user input."""
        return getConfig(self)
