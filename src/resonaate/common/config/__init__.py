"""Module defining common configuration formats."""
from __future__ import annotations

# Standard Library Imports
import json
import sys
from argparse import ArgumentParser, RawTextHelpFormatter
from functools import cache
from os import environ
from pathlib import Path

# Third Party Imports
from dotenv import dotenv_values
from pydantic import BaseModel

# Local Imports
from .behavioral import BehavioralConfig
from .input_output import IOConfiguration  # noqa: TCH001
from .meta import NotSet, UserSpec, userSpecFactory


class RootConfig(BaseModel):
    """Base configuration specifying how RESONAATE should behave."""

    io_config: IOConfiguration
    """Collection of configuration options pertaining to RESONAATE's inputs and outputs."""

    behavioral_config: BehavioralConfig = BehavioralConfig()
    """Collection of configuration options pertaining to RESONAATE's behavior."""


@cache
def rootConfigSpec() -> UserSpec:
    """Build the :class:`.UserSpec` describing the :class:`.RootConfig` model."""
    return userSpecFactory("RootConfig", RootConfig)


_ARGS_ENV_LOC: str = "RESONAATE_ARGS"
"""Key of environment variable to store CLI args to for child processes to consume."""


def putResonaateArgs(cli_args: list[str] | None, env_loc: str = _ARGS_ENV_LOC):
    """Store CLI args provided to RESONAATE on the environment.

    Args:
        cli_args: List of string command line arguemnts.
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


def getCommandLineParser() -> ArgumentParser:
    """Build command line argument parser based on :class:`.RootConfig`."""
    parser = ArgumentParser(
        description="RESONAATE Command Line Interface",
        argument_default=NotSet,
        formatter_class=RawTextHelpFormatter,
    )
    rootConfigSpec().addToArgParser(parser)
    return parser


def rootConfigFactory(cli_args: list[str] | None, dotenv_path: Path = Path("resonaate.env")):
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
    parsed_args = getCommandLineParser().parse_args(cli_args)

    config_dict = {}
    rootConfigSpec().retrieveUserInput(config_dict, dir(parsed_args), resonaate_dotenv)

    return RootConfig(**config_dict)


@cache
def getConfig() -> RootConfig:
    """Retrieve the (possibly cached) :class:`.RootConfig` object built from default user input."""
    return rootConfigFactory()
