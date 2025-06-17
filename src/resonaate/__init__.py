"""Main Module Documentation.

The top-level module is documented below, which mainly serves as a command line entry point for
running large, parallelized SDA scenarios.
"""

from __future__ import annotations

__version__ = "4.1.0"


# Standard Library Imports
import json
import sys
from os import environ

# Local Imports
from .common.config_model import BehavioralConfig


def runResonaate(
    _config: BehavioralConfig,
) -> None:
    """Run a RESONAATE :class:`~.Scenario`.

    Args:
        _config: :class:`.BehavorialConfig` object specifying how to run RESONAATE.
    """
    # Local Imports
    from .scenario import buildScenarioFromConfigFile

    # Build the Scenario application from the JSON init
    app = buildScenarioFromConfigFile(
        _config.init_file,
        internal_db_path=_config.db_path,
        importer_db_path=_config.importer_db_path,
    )

    try:
        # Step through simulation
        app.propagateTo(app.clock.julian_date_stop)
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
    resonaate_args = []
    if len(sys.argv) > 1:
        resonaate_args = sys.argv[1:]
    # store cli args to env so child processes can access behavioral config
    environ[BehavioralConfig.ARGS_ENV_LOC] = json.dumps(resonaate_args)

    _config = BehavioralConfig.getConfig(cli_args=resonaate_args)
    runResonaate(_config)
