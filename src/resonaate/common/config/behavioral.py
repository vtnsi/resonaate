"""Define configuration parameters pertaining to the inherent behavior of RESONAATE."""
from __future__ import annotations

# Standard Library Imports
from textwrap import dedent
from typing import Annotated, Optional

# Third Party Imports
from pydantic import BaseModel, Field

# Local Imports
from ..labels import EOPLoaderLabel
from .meta import CommandLineOptions, EnvName, LoggingLevel

# ruff: noqa: TCH001, TCH003, UP007

class BehavioralConfig(BaseModel):
    """Set of configuration options that specify the behavior of RESONAATE."""

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
