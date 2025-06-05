"""Module that consolidates RESONAATE behavioral configuration into a pydantic model."""
from __future__ import annotations

# Standard Library Imports
from argparse import ArgumentParser
from os import environ
from pathlib import Path
from typing import Annotated, Optional

# Third Party Imports
from pydantic import BaseModel, Field

# Local Imports
from ..data import createAlchemyUrl

# ruff: noqa: TCH001, TCH003, UP007


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


class BehavioralConfig(BaseModel):
    """Set of configuration options that specify the behavior of RESONAATE."""

    init_file: Annotated[
        Path,
        Field(
            description="Path to RESONAATE initialization message file.",
        ),
    ]

    db_path: Annotated[
        Optional[str],
        Field(
            description="String specifying the parameters to connect to a database for RESONAATE output.",
            default_factory=createAlchemyUrl,
        ),
        EnvName("DB_PATH"),
        CommandLineOptions("-d", "--db-path"),
    ]

    importer_db_path: Annotated[
        Optional[str],
        Field(
            description="String specifying the parameters to connect to a database for importing into RESONAATE.",
            default=None,
        ),
        EnvName("IMPORTER_DB_PATH"),
        CommandLineOptions("-i", "--importer-db-path"),
    ]


def getCommandLineParser():
    """Build command line argument parser based on :class:`.BehaviroalConfig`."""
    parser = ArgumentParser(description="RESONAATE Command Line Interface")
    for field_name, field_info in BehavioralConfig.model_fields.items():
        if field_info.is_required():
            parser.add_argument(field_name, help=field_info.description)
        else:
            flags = []
            for meta in field_info.metadata:
                if isinstance(meta, CommandLineOptions):
                    flags = meta.options

            if flags:
                parser.add_argument(
                    *flags,
                    required=field_info.is_required(),
                    help=field_info.description,
                    dest=field_name,
                )
    return parser


def buildConfig(cli_args: list[str]) -> BehavioralConfig:
    """Build a complete configuration."""
    config_dict = {}
    # TODO: pull config options from environ
    # TODO: pull config options from 'resonaate.env' file
    arg_parser = getCommandLineParser()
    parsed_args = arg_parser.parse_args(cli_args)
    config_dict.update(vars(parsed_args))

    return BehavioralConfig(**config_dict)
