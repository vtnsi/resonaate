"""Module that consolidates RESONAATE behavioral configuration into a pydantic model."""
from __future__ import annotations

# Standard Library Imports
import json
import logging
from argparse import ArgumentParser, RawTextHelpFormatter
from enum import Enum
from os import environ
from pathlib import Path
from textwrap import dedent
from types import NoneType
from typing import Annotated, ClassVar, NewType, Optional, get_args

# Third Party Imports
from dotenv import dotenv_values
from pydantic import BaseModel, Field

# Local Imports
from ..data import createAlchemyUrl
from .labels import EOPLoaderLabel

# ruff: noqa: TCH001, TCH003, UP007


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

    logging_output_location: Annotated[
        Optional[str],
        Field(
            description="Specifies where the logging module outputs logs.",
            default="stdout",
        ),
        EnvName("LOGGING_OUTPUT_LOCATION"),
        CommandLineOptions("--logging-output-location"),
    ]

    logging_level: Annotated[
        Optional[LoggingLevel],
        Field(
            description="Logging level that gets output to the logs.",
            default=LoggingLevel.DEBUG,
        ),
        EnvName("LOGGING_LEVEL"),
        CommandLineOptions("--logging-level"),
    ]

    logging_max_file_size: Annotated[
        Optional[int],
        Field(
            description=dedent("""\
            Maximum file size before the file rolls over.

            Only applies when *not* using 'stdout' for "logging_output_location". Unit is bytes."""),
            default=1048576,
        ),
        EnvName("LOGGING_MAX_FILE_SIZE"),
        CommandLineOptions("--logging-max-file-size"),
    ]

    logging_max_file_count: Annotated[
        Optional[int],
        Field(
            description=dedent("""\
            Maximum number of files that stay saved during runtime.

            Once this limit is reached, the oldest files will be overwritten in the order that they
            were written. Only applies when *not* using 'stdout' for "logging_output_location"."""),
            default=50,
        ),
        EnvName("LOGGING_MAX_FILE_COUNT"),
        CommandLineOptions("--logging-max-file-count"),
    ]

    parallel_worker_count: Annotated[
        Optional[int],
        Field(
            description=dedent("""\
            How many worker threads to spin up.

            If left unspecified, ray will spin up as many workers as there are cores available to
            Resonaate."""),
            default=None,
        ),
        EnvName("PARALLEL_WORKER_COUNT"),
        CommandLineOptions("--parallel-worker-count"),
    ]

    debugging_output_directory: Annotated[
        Optional[str],
        Field(
            description="Relative directory that debugging output files are saved to.",
            default="debugging",
        ),
        EnvName("DEBUGGING_OUTPUT_DIRECTORY"),
        CommandLineOptions("--debugging-output-dir"),
    ]

    debugging_nearest_pd: Annotated[
        Optional[bool],
        Field(
            description=dedent("""\
            When using an sequential filter that relies on Cholesky decomposition, if the
            covariance becomes non positive definite, use `physics.math.nearestPD()` to find the
            nearest positive definite matrix.

            Cholesy decomposition can raise an uncaught exception if this value is left false,
            resulting in a simulation hault."""),
            default=False,
        ),
        EnvName("DEBUGGING_NEAREST_PD"),
        CommandLineOptions("--debugging-nearest-pd"),
    ]

    debugging_estimate_error_inflation: Annotated[
        Optional[bool],
        Field(
            description=dedent("""\
            Output Filter information when an 'update' step takes place that results in greater
            absolute error of the state estimate."""),
            default=False,
        ),
        EnvName("DEBUGGING_ESTIMATE_ERROR_INFLATION"),
        CommandLineOptions("--debugging-est-err-inflation"),
    ]

    debugging_three_sigma_obs: Annotated[
        Optional[bool],
        Field(
            description=dedent("""\
            Output observation information when an observation's absolute error is greater than the
            sensor's three-sigma variance."""),
            default=False,
        ),
        EnvName("DEBUGGING_THREE_SIGMA_OBS"),
        CommandLineOptions("--debugging-three-sigma-obs"),
    ]

    eop_loader_name: Annotated[
        Optional[EOPLoaderLabel],
        Field(
            description="Name of the concrete `EOPLoader` implementation to use.",
            default=EOPLoaderLabel.MODULE_DOT_DAT,
        ),
        EnvName("EOP_LOADER_NAME"),
        CommandLineOptions("--eop-loader-name"),
    ]

    eop_loader_location: Annotated[
        Optional[str],
        Field(
            description="Location that the specified `EOPLoader` will load EOP data from.",
            default="EOPdata.dat",
        ),
        EnvName("EOP_LOADER_LOCATION"),
        CommandLineOptions("--eop-loader-location"),
    ]

    @classmethod
    def getCommandLineParser(cls) -> ArgumentParser:
        """Build command line argument parser based on :class:`.BehaviroalConfig`."""
        parser = ArgumentParser(
            description="RESONAATE Command Line Interface",
            argument_default=NotSet,
            formatter_class=RawTextHelpFormatter,
        )
        for field_name, field_info in cls.model_fields.items():
            if field_info.is_required():
                parser.add_argument(field_name, help=field_info.description)
            else:
                flags = []
                env_name = ""
                for meta in field_info.metadata:
                    if isinstance(meta, CommandLineOptions):
                        flags = meta.options

                    if isinstance(meta, EnvName):
                        env_name = f"\n\nThis option can also be set via environment variable: {meta.name}."

                if flags:
                    default_str = f" Defaults to {field_info.get_default(call_default_factory=False)}."
                    if field_info.default_factory:
                        default_str = f" Defaults to value generated by '{field_info.default_factory.__name__}'."

                    kwargs = {
                        "required": field_info.is_required(),
                        "help": field_info.description + default_str + env_name,
                        "dest": field_name,
                    }

                    type_args = get_args(field_info.annotation)
                    for type_arg in type_args:
                        if issubclass(type_arg, Enum):
                            kwargs["choices"] = [it.value for it in type_arg]

                    parser.add_argument(
                        *flags,
                        **kwargs,
                    )
        return parser

    __instance: ClassVar[BehavioralConfig] = None
    """Singleton."""

    @classmethod
    def getConfig(
        cls,
        cli_args: Optional[list[str]] = None,
        dotenv_path: Path = Path("resonaate.env"),
    ) -> BehavioralConfig:
        """Return a reference to the singleton shared config.

        Args:
            cli_args: Command line arguments that can be parsed into a :class:`.BehavioralConfig`.
            dotenv_path: Path to dotenv file specifying RESONAATE configuration options.

        Note:
            Arguments will be ignored once singleton instance is established.

        Returns:
            Behavioral configuration parsed from specified locations.
        """
        if cls.__instance is None:
            if cli_args is None:
                cli_args = json.loads(environ.get("RESONAATE_ARGS"))
            config_dict = {}
            resonaate_dotenv = dotenv_values(dotenv_path)
            for field_name, field_info in cls.model_fields.items():
                env_name: str = ""
                for meta in field_info.metadata:
                    if isinstance(meta, EnvName):
                        env_name = meta.name
                        break
                val = NotSet
                if env_name:
                    if env_name in environ:
                        val = environ[env_name]
                    if env_name in resonaate_dotenv:
                        val = resonaate_dotenv[env_name]
                if val is not NotSet:
                    config_dict[field_name] = val

            arg_parser = cls.getCommandLineParser()
            parsed_args = arg_parser.parse_args(cli_args)
            for field_name, arg in vars(parsed_args).items():
                if arg is not NotSet:
                    config_dict[field_name] = arg  # noqa: PERF403

            cls.__instance = cls(**config_dict)
        return cls.__instance
