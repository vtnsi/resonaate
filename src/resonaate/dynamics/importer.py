"""Module implementing the bulk ephemeris importer paradigm."""

# Standard Library Imports
from datetime import datetime
from logging import getLogger

# Third Party Imports
from sqlalchemy.orm import Query

# Local Imports
from ..agents.agent_base import Agent
from ..common.exceptions import MissingEphemerisError
from ..data.ephemeris import TruthEphemeris
from ..data.epoch import Epoch
from ..data.importer_database import ImporterDatabase


class EphemerisImporter:
    """Class that encapsulates importing ephemeris for :class:`.Agent`'s."""

    def __init__(
        self,
        importer_db_path: str,
    ):
        """Initialize this :class:`.EphemerisImporter`.

        Args:
            importer_db_path: Path to the importer database containing ephemeris data

        Raises:
            ValueError: If `importer_db_path` is not a valid importer database URL.
        """
        self._logger = getLogger("resonaate")
        self._importer_db = ImporterDatabase(importer_db_path, logger=self._logger)
        self._registrants: dict[int, Agent] = {}

    def registerAgent(self, agent: Agent):
        """Register an `agent` for updates from the :class:`.ImporterDatabase`.

        Args:
            agent: The :class:`.Agent` to register.

        Raises:
            RuntimeError: If the specified `agent` is configured for realtime propagation.
        """
        if agent.realtime:
            err = f"Agent {agent.simulation_id} configured for realtime propagation!"
            raise RuntimeError(err)

        self._registrants[agent.simulation_id] = agent

    def importEphemerides(self, datetime_epoch: datetime):
        """Import :class:`.TruthEphemeris` data from :class:`.ImporterDatabase`.

        Args:
            datetime_epoch: The epoch to load ephemeris data for.

        Raises:
            MissingEphemerisError: If ephemeris data can't be found for every registered
                :class:`.Agent` for the specified time step.
        """
        query = (
            Query([TruthEphemeris])
            .join(Epoch)
            .filter(Epoch.timestampISO == datetime_epoch.isoformat(timespec="microseconds"))
        )
        current_ephemerides = self._importer_db.getData(query)

        # Ensure we have at least as many ephems as register import callbacks
        if len(current_ephemerides) < len(self._registrants):
            retrieved_ids = {ephem.agent_id for ephem in current_ephemerides}
            registerd_ids = set(self._registrants.keys())
            missing_ids = registerd_ids - retrieved_ids
            msg = f"Missing ephemeris data for agents {missing_ids} at time {datetime_epoch.isoformat(timespec='microseconds')}"
            self._logger.error(msg)
            raise MissingEphemerisError(msg)

        extra_import_ids = set()
        for ephem in current_ephemerides:
            if ephem.agent_id in self._registrants:
                self._registrants[ephem.agent_id].importState(ephem)
                del self._registrants[ephem.agent_id]
                continue
            extra_import_ids.add(ephem.agent_id)

        if extra_import_ids:
            msg = f"Didn't have agents registered for imported ephemeris data: {extra_import_ids}"
            self._logger.warning(msg)
