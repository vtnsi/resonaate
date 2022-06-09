"""Main entry point for RESONAATE command line tool."""
# Standard Library Imports
from datetime import timedelta
from typing import Optional
# Third Party Imports
# RESONAATE Imports
from .common.behavioral_config import BehavioralConfig
from .common.cli import getCommandLineParser
from .parallel import isMaster, resetMaster
from .physics.time.conversions import getTargetJulianDate
from .scenario import buildScenarioFromConfigFile


def main() -> None:
    """RESONAATE simulation main entry point.

    This is the function that the :command:`resonaate` command points to. See :mod:`.cli` for
    details on what command line options are available.
    """
    # Parse command line arguments and pass them to runResonaate
    parser = getCommandLineParser()
    cli_args = parser.parse_args()

    runResonaate(
        cli_args.init_msg,
        sim_time_hours=cli_args.sim_time_hours,
        internal_db_path=cli_args.db_path,
        importer_db_path=cli_args.importer_db_path,
        debug_mode=cli_args.debug_mode
    )


def runResonaate(
    init_message: str, sim_time_hours: Optional[float] = 3,
    internal_db_path: Optional[str] = None, importer_db_path: Optional[str] = None,
    debug_mode: bool = False
) -> None:
    """Run a RESONAATE :class:`~.Scenario`.

    Args:
        init_message (``str``): path to the JSON initialization message
        sim_time_hours (``float``, optional): total hours to simulate. Defaults to 3.
        internal_db_path (``str``, optional): if saving to database, this points
            the :class:`.ResonaateDatabase` to the desired location. Defaults to ``None``,
            which defaults to the config value if ``auto_db != True``.
        importer_db_path (``str``, optional): if using input/external database to load data,
            this points the :class:`.ImporterDatabase` to the desired location. Defaults to
            ``None``, which then auto-generates a timestamped db file in the **db/** folder
        debug_mode (``bool``, optional): whether to allow worker jobs to block
            indefintely so debugging doesn't fail
    """
    if debug_mode:
        BehavioralConfig.getConfig().debugging.ParallelDebugMode = True

    # Establish Redis connection
    isMaster()

    # Build the Scenario application from the JSON/YAML init
    app = buildScenarioFromConfigFile(
        init_message, internal_db_path=internal_db_path, importer_db_path=importer_db_path
    )

    # Determine final time as a Julian date
    elapsed_time = timedelta(hours=sim_time_hours)

    target_date = getTargetJulianDate(
        app.clock.julian_date_start,
        elapsed_time
    )

    # Step through simulation
    app.propagateTo(target_date)

    # Stop workers gracefully
    app.worker_mgr.stopWorkers()

    # Reset the Redis master key
    resetMaster()

    # Notification simulation stopped gracefully
    app.logger.info("Simulation complete")


if __name__ == '__main__':
    main()
