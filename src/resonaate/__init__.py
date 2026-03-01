"""Main Module Documentation.

The top-level module is documented below, which mainly serves as a command line entry point for
running large, parallelized SDA scenarios.
"""

from __future__ import annotations

__version__ = "4.1.0"

# Local Imports
from .common.config import EntrypointConfig, RootConfig, putResonaateArgs
from .physics.time.conversions import getTargetJulianDate


def runResonaate(
    entry_config: EntrypointConfig,
) -> None:
    """Run a RESONAATE :class:`~.Scenario`.

    Args:
        entry_config: :class:`.EntrypointConfig` object specifying how to run RESONAATE.
    """
    # Local Imports
    from .scenario import buildScenarioFromConfigFile

    # Build the Scenario application from the JSON init
    app = buildScenarioFromConfigFile(
        entry_config.input_config.init_file,
        internal_db_params=entry_config.output_config,
        importer_db_params=entry_config.input_config.importer_db_params,
    )

    sim_end = app.clock.julian_date_stop
    if entry_config.input_config.sim_duration is not None:
        sim_end = getTargetJulianDate(
            app.clock.julian_date_start, entry_config.input_config.sim_duration_timedelta
        )

    try:
        # Step through simulation
        app.propagateTo(sim_end)
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
    """RESONAATE simulation main entry point."""
    # store cli args to env so child processes can access behavioral config
    putResonaateArgs()
    runResonaate(RootConfig.ENTRY.inst())
