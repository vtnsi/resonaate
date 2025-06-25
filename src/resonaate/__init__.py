"""Main Module Documentation.

The top-level module is documented below, which mainly serves as a command line entry point for
running large, parallelized SDA scenarios.
"""

from __future__ import annotations

__version__ = "4.1.0"


def runResonaate(
    init_message: str,
    sim_time_hours: float = 3,
    internal_db_path: str | None = None,
    importer_db_path: str | None = None,
    debug_mode: bool = False,
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
            indefinitely so debugging doesn't fail
    """
    # Standard Library Imports
    from datetime import timedelta

    # Local Imports
    from .common.behavioral_config import BehavioralConfig
    from .physics.time.conversions import getTargetJulianDate
    from .scenario import buildScenarioFromConfigFile

    if debug_mode:
        BehavioralConfig.getConfig().debugging.ParallelDebugMode = True

    # Build the Scenario application from the JSON init
    app = buildScenarioFromConfigFile(
        init_message,
        internal_db_path=internal_db_path,
        importer_db_path=importer_db_path,
    )

    # Determine final time as a Julian date
    elapsed_time = timedelta(hours=sim_time_hours)

    target_date = getTargetJulianDate(app.clock.julian_date_start, elapsed_time)

    try:
        # Step through simulation
        app.propagateTo(target_date)
    except KeyboardInterrupt:
        # Notification simulation stopped via KeyboardInterrupt
        app.logger.warning("Simulation terminated")
    else:
        # Notification simulation stopped gracefully
        app.logger.info("Simulation complete")
    finally:
        # Gracefully shutdown the simulation
        app.shutdown()


def main() -> None:
    """RESONAATE simulation main entry point.

    This is the function that the :command:`resonaate` command points to. See :mod:`.cli` for
    details on what command line options are available.
    """
    # Local Imports
    from .common.cli import getCommandLineParser

    # Parse command line arguments and pass them to runResonaate
    parser = getCommandLineParser()
    cli_args = parser.parse_args()

    runResonaate(
        cli_args.init_msg,
        sim_time_hours=cli_args.sim_time_hours,
        internal_db_path=cli_args.db_path,
        importer_db_path=cli_args.importer_db_path,
        debug_mode=cli_args.debug_mode,
    )
