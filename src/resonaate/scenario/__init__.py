"""The :class:`.Scenario` object is the main "application" used in large RESONAATE simulations."""
# pylint: disable=import-outside-toplevel
# [NOTE][avoid-circular-import]: Import inside of functions to avoid circular imports
from __future__ import annotations


def buildScenarioFromConfigFile(
    config_file_path, internal_db_path=None, importer_db_path=None, start_workers=True
):
    """Instantiate a :class:`.Scenario` based on the specified `config_file_path`.

    Note:
        This function __does__ guarantee that `setDBPath()` is properly called, so
        subsequent calls don't need to rely on database path variable. This should not
        be bypassed as it will cause this to fail.

    Args:
        config_file_path (str): Path to initialization configuration file.
        internal_db_path (``str``, optional): path to RESONAATE internal database object. Defaults
            to ``None``.
        importer_db_path (``str``, optional): path to external importer database for pre-canned
            data. Defaults to ``None``.
        start_workers (``bool``, optional): Flag indicating whether this :class:`.Scenario` should
            spin up its own :class:`.WorkerManager` instance or not.
    """
    # Local Imports
    from ..data import createDatabasePath
    from .config import ScenarioConfig

    # Load input/external DB
    importer_database_path = None
    if importer_db_path:
        importer_database_path = createDatabasePath(importer_db_path, importer=True)

    return buildScenarioFromConfigDict(
        ScenarioConfig.parseConfigFile(config_file_path),
        internal_db_path=internal_db_path,
        importer_db_path=importer_database_path,
        start_workers=start_workers,
    )


def buildScenarioFromConfigDict(
    config_dict, internal_db_path=None, importer_db_path=None, start_workers=True
):
    """Instantiate a :class:`.Scenario` based on the specified `config_dict`.

    Note:
        This function __does__ guarantee that `setDBPath()` is properly called, so
        subsequent calls don't need to rely on database path variable. This should not
        be bypassed as it will cause this to fail.

    Args:
        config_dict (dict): Configuration dictionary defining a scenario.
        internal_db_path (``str``, optional): path to RESONAATE internal database object. Defaults
        importer_db_path (``str``, optional): path to external importer database for pre-canned
            data. Defaults to ``None``.
        start_workers (``bool``, optional): Flag indicating whether this :class:`.Scenario` should
            spin up its own :class:`.WorkerManager` instance or not.
    """
    # Local Imports
    from ..data import createDatabasePath, setDBPath
    from .config import ScenarioConfig
    from .scenario import Scenario
    from .scenario_builder import ScenarioBuilder

    # [NOTE][force-db-path]: Only call to `setDBPath()`. Subsequent calls will cause an error to
    #   be thrown!
    database_path = createDatabasePath(internal_db_path, importer=False)
    setDBPath(path=database_path)

    config = ScenarioConfig(**config_dict)
    builder = ScenarioBuilder(config, importer_db_path=importer_db_path)

    return Scenario(
        builder.config,
        builder.clock,
        builder.target_agents,
        builder.estimate_agents,
        builder.sensor_agents,
        builder.tasking_engines,
        importer_db_path=importer_db_path,
        logger=builder.logger,
        start_workers=start_workers,
    )
