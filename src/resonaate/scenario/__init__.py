"""Method for building :class:`.Scenario`s from configuration files."""


def buildScenarioFromConfigFile(
    config_file_path, internal_db_path=None, importer_db_path=None, start_workers=True
):
    """Instantiate a :class:`.Scenario` based on the specified `config_file_path`.

    Args:
        config_file_path (str): Path to initialization configuration file.
        internal_db_path (``str``, optional): path to RESONAATE internal database object. Defaults
            to ``None``.
        importer_db_path (``str``, optional): path to external importer database for pre-canned
            data. Defaults to ``None``.
        start_workers (``bool``, optional): Flag indicating whether this :class:`.Scenario` should
            spin up its own :class:`.WorkerManager` instance or not.
    """
    from .config import ScenarioConfig  # pylint: disable=import-outside-toplevel
    # [avoid-circular-import] Import done inside of function to avoid circular imports for other
    #    components of the `scenario` package.

    return buildScenarioFromConfigDict(
        ScenarioConfig.parseConfigFile(config_file_path),
        internal_db_path=internal_db_path,
        importer_db_path=importer_db_path,
        start_workers=start_workers
    )


def buildScenarioFromConfigDict(
    config_dict, internal_db_path=None, importer_db_path=None, start_workers=True
):
    """Instantiate a :class:`.Scenario` based on the specified `config_dict`.

    Args:
        config_dict (dict): Configuration dictionary defining a scenario.
        internal_db_path (``str``, optional): path to RESONAATE internal database object. Defaults
            to ``None``.
        importer_db_path (``str``, optional): path to external importer database for pre-canned
            data. Defaults to ``None``.
        start_workers (``bool``, optional): Flag indicating whether this :class:`.Scenario` should
            spin up its own :class:`.WorkerManager` instance or not.
    """
    from .config import ScenarioConfig  # pylint: disable=import-outside-toplevel
    from .scenario_builder import ScenarioBuilder  # pylint: disable=import-outside-toplevel
    from .scenario import Scenario  # pylint: disable=import-outside-toplevel
    # [avoid-circular-import]

    config = ScenarioConfig()
    config.readConfig(config_dict)
    builder = ScenarioBuilder(config)

    return Scenario(
        builder.config,
        builder.clock,
        builder.target_agents,
        builder.estimate_agents,
        builder.sensor_network,
        builder.tasking_engines,
        internal_db_path=internal_db_path,
        importer_db_path=importer_db_path,
        logger=builder.logger,
        start_workers=start_workers
    )
