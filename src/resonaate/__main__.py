# Standard Library Imports
import logging
from datetime import datetime, timedelta
from os.path import abspath, dirname, exists, join, normpath
# Third Party Imports
# RESONAATE Imports
from .common.behavioral_config import BehavioralConfig
from .common.utilities import parseCommandLineArguments
from .data.data_interface import DataInterface
from .parallel import isMaster, resetMaster
from .physics.time.conversions import getTargetJulianDate
from .scenario.scenario import Scenario


def main():
    """RESONAATE simulation main entry point."""
    # Parse command line arguments and pass them to runResonaate
    cli_args = parseCommandLineArguments()

    runResonaate(
        cli_args.init_msg,
        sim_time_hours=cli_args.sim_time_hours,
        db_save=cli_args.output_db,
        output_db_path=cli_args.output_db_path,
        debug_mode=cli_args.debug_mode
    )


def runResonaate(init_message, sim_time_hours=3, db_save=True, output_db_path=None, debug_mode=False):
    """Run an example of the Scenario without using the RESONAATEApplication API.

    Args:
        init_message (``str``): path to the JSON initialization message
        sim_time_hours (``float``, optional): total hours to simulate. Defaults to 3.
        db_save (``bool``, optional): whether to save data to a new database every
            :class:`.Scenario.output_time_step` seconds. Defaults to ``True``.
        output_db_path (``str``, optional): if saving to output database, this points
            the :class:`.DataInterface` to the desired location. Defaults to ``None``,
            which then auto-generates a timestamped db file in the **output** folder
        debug_mode (``bool``, optional): whether to allow worker tasks to block
            indefintely so debugging doesn't fail
    """
    if debug_mode:
        BehavioralConfig.getConfig().debugging.ParallelDebugMode = True

    # Establish Redis connection
    isMaster()

    # Build the Scenario application from the JSON/YAML init
    app = Scenario.fromConfigFile(init_message)

    # Determine final time as a Julian date
    elapsed_time = timedelta(hours=sim_time_hours)

    target_date = getTargetJulianDate(
        app.clock.julian_date_start,
        elapsed_time
    )

    # Create output database
    if db_save is True:
        db_path = createOutputDatabasePath(output_db_path)
        app.logger.info("Output simulation data to: {0}".format(db_path))
        output_database = DataInterface(db_path)
    else:
        output_database = None

    # Step through simulation
    app.propagateTo(target_date, output_database)

    # Reset the Redis master key
    resetMaster()


def createOutputDatabasePath(path):
    """Create a valid path for the output database.

    Args:
        path (``str``): path-like string to the desired database file location.

    Returns:
        ``str``: properly formatted database path. Defaults to timestamped path
            in **output** directory if ``None`` is passed.
    """
    if path is None:
        right_now = datetime.now().isoformat().replace(":", "-").replace(".", "-")
        path = normpath(join(abspath(dirname(__file__)), "../../"))
        db_path = "sqlite:///{0}/output/output_{1}.db".format(path, right_now)
    else:
        db_path = "sqlite:///{0}".format(normpath(abspath(path)))
        if exists(abspath(path)):
            logging.getLogger("resonaate").info("Overwriting output database: {0}".format(db_path))

    return db_path


if __name__ == '__main__':
    main()
