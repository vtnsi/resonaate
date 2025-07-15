"""The :class:`.Scenario` object is the main "application" used in large RESONAATE simulations."""

# [NOTE][avoid-circular-import]: Import inside of functions to avoid circular imports
from __future__ import annotations

# Standard Library Imports
from typing import TYPE_CHECKING

# Third Party Imports
import ray

if TYPE_CHECKING:
    # Standard Library Imports
    from pathlib import Path

    # Local Imports
    from ..common.config.input_output import AlchemyURLSpec


def buildScenarioFromConfigFile(
    config_file_path: str | Path,
    internal_db_params: AlchemyURLSpec | None = None,
    importer_db_params: AlchemyURLSpec | None = None,
):
    """Instantiate a :class:`.Scenario` based on the specified `config_file_path`.

    Note:
        This function __does__ guarantee that `setDBParams()` is properly called, so
        subsequent calls don't need to rely on database path variable. This should not
        be bypassed as it will cause this to fail.

    Args:
        config_file_path: Path to initialization configuration file.
        internal_db_params: Collection of parameters specifying how to connect to RESONAATE's internal database.
        importer_db_params: Collection of parameters specifying how to connect to an importer database.
    """
    # Local Imports
    from .config import ScenarioConfig

    return buildScenarioFromConfigDict(
        ScenarioConfig.parseConfigFile(config_file_path),
        internal_db_params=internal_db_params,
        importer_db_params=importer_db_params,
    )


def buildScenarioFromConfigDict(
    config_dict,
    internal_db_params: AlchemyURLSpec | None = None,
    importer_db_params: AlchemyURLSpec | None = None,
):
    """Instantiate a :class:`.Scenario` based on the specified `config_dict`.

    Note:
        This function __does__ guarantee that `setDBParams()` is properly called, so
        subsequent calls don't need to rely on database path variable. This should not
        be bypassed as it will cause this to fail.

    Args:
        config_dict (dict): Configuration dictionary defining a scenario.
        internal_db_params: Collection of parameters specifying how to connect to RESONAATE's internal database.
        importer_db_params: Collection of parameters specifying how to connect to an importer database.
    """
    # Local Imports
    from ..common.config import OutputDbUrlSpec, RootConfig
    from ..data import setDBParams
    from .config import ScenarioConfig
    from .scenario import Scenario
    from .scenario_builder import ScenarioBuilder

    # [NOTE][force-db-path]: Only call to `setDBParams()`. Subsequent calls will cause an error to
    #   be thrown!
    if not ray.is_initialized():
        ray.init(num_cpus=RootConfig.LIB.inst().behavioral_config.parallel_worker_count)
    if internal_db_params is None:
        internal_db_params = OutputDbUrlSpec()
    internal_db_params.checkExists()
    setDBParams(internal_db_params)

    config = ScenarioConfig(**config_dict)
    builder = ScenarioBuilder(config, importer_db_params=importer_db_params)

    return Scenario(
        builder.config,
        builder.clock,
        builder.target_agents,
        builder.estimate_agents,
        builder.sensor_agents,
        builder.tasking_engines,
        importer_db_params=importer_db_params,
        logger=builder.logger,
    )
