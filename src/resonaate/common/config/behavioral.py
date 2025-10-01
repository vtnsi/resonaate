"""Define configuration parameters pertaining to the inherent behavior of RESONAATE."""

from __future__ import annotations

# Standard Library Imports
from pathlib import Path
from typing import Annotated, Optional

# Third Party Imports
from pydantic import Field

# Local Imports
from ..labels import EOPLoaderLabel
from .meta import CommandLineOptions, EnvName, LoggingLevel, UserBaseModel

# ruff: noqa: TCH001, TCH002, TCH003, UP007


class BehavioralConfig(UserBaseModel):
    """Set of configuration options that specify the behavior of RESONAATE."""

    logging_output_location: Annotated[
        Optional[str],
        Field(default="stdout"),
        EnvName("LOGGING_OUTPUT_LOCATION"),
        CommandLineOptions("--logging-output-location"),
    ]
    """Specifies where the logging module outputs logs."""

    logging_level: Annotated[
        Optional[LoggingLevel],
        Field(default=LoggingLevel.DEBUG),
        EnvName("LOGGING_LEVEL"),
        CommandLineOptions("--logging-level"),
    ]
    """Logging level that gets output to the logs."""

    logging_max_file_size: Annotated[
        Optional[int],
        Field(default=1048576),
        EnvName("LOGGING_MAX_FILE_SIZE"),
        CommandLineOptions("--logging-max-file-size"),
    ]
    """Maximum file size before the file rolls over.

    Only applies when *not* using 'stdout' for "logging_output_location". Unit is bytes.
    """

    logging_max_file_count: Annotated[
        Optional[int],
        Field(default=50),
        EnvName("LOGGING_MAX_FILE_COUNT"),
        CommandLineOptions("--logging-max-file-count"),
    ]
    """Maximum number of files that stay saved during runtime.

    Once this limit is reached, the oldest files will be overwritten in the order that they
    were written. Only applies when *not* using 'stdout' for "logging_output_location".
    """

    parallel_worker_count: Annotated[
        Optional[int],
        Field(default=None),
        EnvName("PARALLEL_WORKER_COUNT"),
        CommandLineOptions("--parallel-worker-count"),
    ]
    """How many worker threads to spin up.

    If left unspecified, ray will spin up as many workers as there are cores available to Resonaate.
    """

    debugging_output_directory: Annotated[
        Optional[Path],
        Field(default="debugging"),
        EnvName("DEBUGGING_OUTPUT_DIRECTORY"),
        CommandLineOptions("--debugging-output-dir"),
    ]
    """Relative directory that debugging output files are saved to."""

    debugging_nearest_pd: Annotated[
        Optional[bool],
        Field(default=False),
        EnvName("DEBUGGING_NEAREST_PD"),
        CommandLineOptions("--debugging-nearest-pd"),
    ]
    """Indication of whether to use `physics.mat.nearestPD()` if Cholesky decomposition fails.

    When using an sequential filter that relies on Cholesky decomposition, if the covariance becomes non
    positive definite, Cholesy decomposition can raise an uncaught exception resulting in a simulation hault.
    Setting this flag indicates that `physics.math.nearestPD()` should be used to find the nearest positive
    definite matrix to attempt to circumvent the error.
    """

    filter_reinitialize: Annotated[
        Optional[bool],
        Field(default=False),
        EnvName("FILTER_REINITIALIZE"),
        CommandLineOptions("--filter-reinitialize"),
    ]
    """Indication of whether or not to completely reset the a filter if cholesky decomposition fails.

    If `debugging_nearest_pd` is set to True, the filter will only reinitialize if a nearest PD matrix cannot
    be located. Otherwise, the filter will completely reset with the initial covariance that it had at the start
    of the scenario."""

    debugging_estimate_error_inflation: Annotated[
        Optional[bool],
        Field(default=False),
        EnvName("DEBUGGING_ESTIMATE_ERROR_INFLATION"),
        CommandLineOptions("--debugging-est-err-inflation"),
    ]
    """Output info when a 'filter update' takes place that results in greater error of the state estimate."""

    debugging_three_sigma_obs: Annotated[
        Optional[bool],
        Field(default=False),
        EnvName("DEBUGGING_THREE_SIGMA_OBS"),
        CommandLineOptions("--debugging-three-sigma-obs"),
    ]
    """Output info when an observation's absolute error is greater than the sensor's three-sigma variance."""

    eop_loader_name: Annotated[
        Optional[EOPLoaderLabel],
        Field(default=EOPLoaderLabel.MODULE_DOT_DAT),
        EnvName("EOP_LOADER_NAME"),
        CommandLineOptions("--eop-loader-name"),
    ]
    """Name of the concrete `EOPLoader` implementation to use."""

    eop_loader_location: Annotated[
        Optional[str],
        Field(default="EOPdata.dat"),
        EnvName("EOP_LOADER_LOCATION"),
        CommandLineOptions("--eop-loader-location"),
    ]
    """Location that the specified `EOPLoader` will load EOP data from."""
