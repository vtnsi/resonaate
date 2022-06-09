# Standard Library Imports
import logging
from datetime import datetime, timedelta
from os import getcwd, mkdir
from os.path import abspath, exists, join, normpath
# Third Party Imports
# RESONAATE Imports
from .common.behavioral_config import BehavioralConfig
from .common.cli import getCommandLineParser
from .data.resonaate_database import ResonaateDatabase
from .parallel import isMaster, resetMaster
from .physics.time.conversions import getTargetJulianDate
from .scenario import buildScenarioFromConfigFile


def main():
    """RESONAATE simulation main entry point."""
    # Parse command line arguments and pass them to runResonaate
    parser = getCommandLineParser()
    cli_args = parser.parse_args()

    runResonaate(
        cli_args.init_msg,
        sim_time_hours=cli_args.sim_time_hours,
        db_save=cli_args.db_save,
        auto_db=cli_args.auto_db,
        internal_db_path=cli_args.db_path,
        importer_db_path=cli_args.importer_db_path,
        debug_mode=cli_args.debug_mode
    )


def runResonaate(
    init_message, sim_time_hours=3, db_save=True, auto_db=False, internal_db_path=None, importer_db_path=None,
    debug_mode=False
):
    """Run an example of the Scenario without using the RESONAATEApplication API.

    Args:
        init_message (``str``): path to the JSON initialization message
        sim_time_hours (``float``, optional): total hours to simulate. Defaults to 3.
        db_save (``bool``, optional): whether to save data to a new database file every
            :class:`.Scenario.output_time_step` seconds. Defaults to ``True``.
        auto_db (``bool``, optional): whether to auto-generate the DB filename, otherwise use the
            given ``internal_db_path`` arg or config value. Defaults to ``False``.
        internal_db_path (``str``, optional): if saving to database, this points
            the :class:`.ResonaateDatabase` to the desired location. Defaults to ``None``,
            which defaults to the config value if ``auto_db != True``.
        importer_db_path (``str``, optional): if using input/external database to load data,
            this points the :class:`.ImporterDatabase` to the desired location. Defaults to
            ``None``, which then auto-generates a timestamped db file in the **db** folder
        debug_mode (``bool``, optional): whether to allow worker jobs to block
            indefintely so debugging doesn't fail
    """
    if debug_mode:
        BehavioralConfig.getConfig().debugging.ParallelDebugMode = True

    # Establish Redis connection
    isMaster()

    # Create database, use in-memory if `db_save` is False
    if db_save is False:
        database_path = ResonaateDatabase.SQLITE_PREFIX
    else:
        database_path = createDatabasePath(internal_db_path, auto=auto_db)

    # Load input/external DB
    importer_database_path = None
    if importer_db_path:
        importer_database_path = createDatabasePath(importer_db_path, importer=True)

    # Build the Scenario application from the JSON/YAML init
    app = buildScenarioFromConfigFile(
        init_message, internal_db_path=database_path, importer_db_path=importer_database_path
    )

    # Log DB location
    if database_path == ResonaateDatabase.SQLITE_PREFIX:
        app.logger.info("Using in-memory database")
    else:
        app.logger.info("Using on-disk database: {0}".format(database_path))

    # Determine final time as a Julian date
    elapsed_time = timedelta(hours=sim_time_hours)

    target_date = getTargetJulianDate(
        app.clock.julian_date_start,
        elapsed_time
    )

    # Step through simulation
    app.propagateTo(target_date)

    # Save in-memory database if `db_save == True`
    if db_save is True and database_path == ResonaateDatabase.SQLITE_PREFIX:
        saveInMemoryDatabase(app)

    # Stop workers gracefully
    app.worker_mgr.stopWorkers()

    # Reset the Redis master key
    resetMaster()

    # Notification simulation stopped gracefully
    app.logger.info("Simulation complete")


def createDatabasePath(path, auto=False, importer=False):
    """Create a valid path for the output database.

    Args:
        path (``str``): path-like string to the desired database file location.
        auto (``bool``): whether to auto-generate the database filepath
        importer (``bool``): whether the db is an importer DB. Throw an error if ``False`` and
            DB path already exists

    Returns:
        ``str``: properly formatted database path. Defaults to timestamped path
            in **db** directory if ``None`` is passed.
    """
    db_path = BehavioralConfig.getConfig().database.DatabaseURL
    if auto is True:
        right_now = datetime.now().isoformat().replace(":", "-").replace(".", "-")
        path = join(getcwd(), "db")
        if not exists(path):
            mkdir(path)
        db_path = "sqlite:///{0}/resonaate_{1}.sqlite3".format(path, right_now)
    elif path:
        db_path = "sqlite:///{0}".format(normpath(abspath(path)))
        if not importer and exists(abspath(path)):
            logging.getLogger("resonaate").error("Cannot overwrite existing database: {0}".format(db_path))
            raise FileExistsError(path)

    return db_path


def saveInMemoryDatabase(app):
    """Save data from an in-memory instance of :class:`.ResonaateDatabase` to disk.

    Args:
        app (:class:`.Scenario`): scenario application
    """
    # Create auto-generated DB path
    db_path = createDatabasePath(None, auto=True)
    app.logger.info("Dumping in-memory database: {0}".format(db_path))

    # Get instance of internal DB. Create a different instance to copy to
    orig_database = ResonaateDatabase.getSharedInterface()
    new_database = ResonaateDatabase(db_url=db_path)

    # Get raw connections
    raw_connection_memory = orig_database.engine.raw_connection()
    raw_connection_file = new_database.engine.raw_connection()

    # Progress print statement for backup function
    def progress(status, remaining, total):  # pylint: disable=unused-argument
        print(f'Copied {total-remaining} of {total} pages...')

    # Perform backup
    raw_connection_memory.backup(raw_connection_file.connection, progress=progress)

    # Close raw connections
    raw_connection_memory.close()
    raw_connection_file.close()


if __name__ == '__main__':
    main()
