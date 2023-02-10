"""The :class:`.Scenario` object is the main "application" used in large RESONAATE simulations."""
from __future__ import annotations


def buildScenarioFromConfigFile(
    config_file_path, internal_db_path=None, importer_db_path=None, start_workers=True
):
    """Instantiate a :class:`.Scenario` based on the specified `config_file_path`.

    Note:
        This function __does__ guarantee the first call to `getSharedInterface()` will use properly
        resolved database path, so subsequent calls don't need to rely on database path variable.
        The only way around the intended behavior now is to improperly call it before this
        function (aka in __main__.py), or bypass this function entirely.

    Args:
        config_file_path (str): Path to initialization configuration file.
        internal_db_path (``str``, optional): path to RESONAATE internal database object. Defaults
            to ``None``.
        importer_db_path (``str``, optional): path to external importer database for pre-canned
            data. Defaults to ``None``.
        start_workers (``bool``, optional): Flag indicating whether this :class:`.Scenario` should
            spin up its own :class:`.WorkerManager` instance or not.
    """
    # pylint: disable=import-outside-toplevel
    # Standard Library Imports
    from pickle import dumps

    # Third Party Imports
    from mjolnir import KeyValueStore

    # Local Imports
    from ..data import createDatabasePath
    from ..data.resonaate_database import ResonaateDatabase
    from .config import ScenarioConfig

    # [NOTE][avoid-circular-import]: Import done inside of function to avoid circular imports for
    #    other components of the `scenario` package.
    # Create output database
    database_path = createDatabasePath(internal_db_path, importer=False)
    # [NOTE][force-db-path]: Guarantees first call to `getSharedInterface()` will use properly
    #    resolved database path, so subsequent calls don't need to rely on database path variable.
    #    The only way around the intended behavior now is to improperly call it before this
    #    function (aka in __main__.py), or bypass this function entirely.
    _ = ResonaateDatabase.getSharedInterface(database_path)
    KeyValueStore.setValue("db_path", dumps(database_path))

    # Load input/external DB
    importer_database_path = None
    if importer_db_path:
        importer_database_path = createDatabasePath(importer_db_path, importer=True)

    return buildScenarioFromConfigDict(
        ScenarioConfig.parseConfigFile(config_file_path),
        internal_db_path=database_path,
        importer_db_path=importer_database_path,
        start_workers=start_workers,
    )


def buildScenarioFromConfigDict(
    config_dict, internal_db_path=None, importer_db_path=None, start_workers=True
):
    """Instantiate a :class:`.Scenario` based on the specified `config_dict`.

    Note:
        This function __does__ __not__ guarantee first call to `getSharedInterface()` will use properly
        resolved database path, so the database path can be improperly setup. Use caution when
        calling this function directly. If you want to use a non-default DB location, please call
        `getSharedInterface()` with the proper DB path __before__ calling this function.

    Args:
        config_dict (dict): Configuration dictionary defining a scenario.
        internal_db_path (``str``, optional): path to RESONAATE internal database object. Defaults
            to ``None``.
        importer_db_path (``str``, optional): path to external importer database for pre-canned
            data. Defaults to ``None``.
        start_workers (``bool``, optional): Flag indicating whether this :class:`.Scenario` should
            spin up its own :class:`.WorkerManager` instance or not.
    """
    # pylint: disable=import-outside-toplevel
    # Local Imports
    from .config import ScenarioConfig
    from .scenario import Scenario
    from .scenario_builder import ScenarioBuilder

    # [NOTE][avoid-circular-import]: Import done inside of function to avoid circular imports for
    #    other components of the `scenario` package.

    config = ScenarioConfig(**config_dict)
    builder = ScenarioBuilder(config, importer_db_path=importer_db_path)

    return Scenario(
        builder.config,
        builder.clock,
        builder.target_agents,
        builder.estimate_agents,
        builder.sensor_agents,
        builder.tasking_engines,
        internal_db_path=internal_db_path,
        importer_db_path=importer_db_path,
        logger=builder.logger,
        start_workers=start_workers,
    )
