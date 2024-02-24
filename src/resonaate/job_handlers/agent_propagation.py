""":class:`.Job` handler classes that manage agent propagation logic."""

from __future__ import annotations

# Standard Library Imports
import json
import os.path
import pickle
from collections import defaultdict
from enum import Flag
from typing import TYPE_CHECKING

# Third Party Imports
from mjolnir import Job, KeyValueStore
from numpy import ndarray
from sqlalchemy.orm import Query

# Local Imports
from ..common.behavioral_config import BehavioralConfig
from ..common.exceptions import AgentProcessingError, MissingEphemerisError
from ..common.utilities import getTypeString
from ..data import getDBConnection
from ..data.ephemeris import TruthEphemeris
from ..data.epoch import Epoch
from ..data.events import EventScope, getRelevantEvents
from ..data.importer_database import ImporterDatabase
from ..estimation.sequential.unscented_kalman_filter import UnscentedKalmanFilter
from ..physics.time.stardate import JulianDate, ScenarioTime, julianDateToDatetime
from ..physics.transforms.reductions import getReductionParameters
from .base import CallbackRegistration, JobHandler

if TYPE_CHECKING:
    # Standard Library Imports
    from datetime import datetime

    # Local Imports
    from ..data.events.base import Event
    from ..dynamics.dynamics_base import Dynamics
    from ..dynamics.integration_events.station_keeping import StationKeeper


def asyncPropagate(
    dynamics: Dynamics,
    init_time: ScenarioTime,
    final_time: ScenarioTime,
    initial_state: ndarray,
    station_keeping: list[StationKeeper] | None = None,
    scheduled_events: list[Event] | None = None,
) -> ndarray:
    """Wrap a dynamics propagation method for use with a parallel job submission module.

    Hint:
        The dynamics object needs to have :meth:`~.Dynamics.propagate` implemented.

    Args:
        dynamics (:class:`.Dynamics`): dynamics object to propagate
        init_time (:class:`.ScenarioTime`): initial time to propagate from
        final_time (:class:`.ScenarioTime`): time during the scenario to propagate to
        initial_state (``ndarray``): state of object before propagation
        station_keeping (``list``, optional): :class:`.StationKeeper` objects
        scheduled_events (``list``, optional): :class:`.Event` objects

    Returns:
        ``ndarray``: 6x1 final state vector of the object being propagated
    """
    return dynamics.propagate(
        init_time,
        final_time,
        initial_state,
        station_keeping=station_keeping,
        scheduled_events=scheduled_events,
    )


class PropagationJobHandler(JobHandler):
    """Handle parallel propagation jobs during the simulation."""

    def handleProcessedJob(self, job):
        """Handle jobs completed via the :class:`.QueueManager` process.

        Overrides :meth:`.JobHandler.handleProcessedJob` specifically to log bad agents.

        Hint:
            Requires implementation of :meth:`.CallbackRegistration.jobCompleteCallback`.

        Args:
            job (:class:`.Job`): parallel job object to be handled.

        Raises:
            :class:`.AgentProcessingError`: raised if job completed in an error state.
        """
        if job.status == Job.Status.PROCESSED:
            self.job_id_registration_dict[job.id].jobCompleteCallback(job)

        else:
            self._logProblemAgent(job, self.job_id_registration_dict[job.id].registrant)
            raise AgentProcessingError(f"Error occurred in job {job.id}:\n\t{job.error}")

    def generateJobs(self, **kwargs):
        """Generate list of propagation jobs to submit to the :class:`.QueueManager`.

        KeywordArgs:
            epoch_time (:class:`.ScenarioTime`): current simulation epoch.

        Returns:
            ``list``: :class:`.Job` objects that will be submitted
        """
        jobs = []
        epoch_time = kwargs["epoch_time"]
        for registration in self.callback_registry:
            job = registration.jobCreateCallback(new_time=epoch_time)
            self.job_id_registration_dict[job.id] = registration
            jobs.append(job)

        return jobs

    def deregisterCallback(self, callback_id):
        """Remove an agent's :class:`.AgentPropagationRegistration` from this :class:`.PropagationJobHandler`.

        Args:
            callback_id (int): Unique identifier of the agent who's registration is being removed.
        """
        registrant_index = -1
        for index, registration in enumerate(self.callback_registry):
            if registration.registrant.simulation_id == callback_id:
                registrant_index = index
                break
        if registrant_index >= 0:
            self.callback_registry.pop(registrant_index)

    def _logProblemAgent(self, job, registrant):
        """Log information to a file because a :class:`.Job` returned with an error.

        Args:
            job (:class:`.Job`): job object that is in an error state.
            registrant (:class:`~.agent_base.Agent`): registered agent corresponding to the bad job.
        """
        data = self._getProblemAgentInformation(job, registrant)
        directory = os.path.join(BehavioralConfig.getConfig().debugging.OutputDirectory, "agents")
        file_name = os.path.join(directory, f"error_{job.id}_{registrant.simulation_id}.json")

        if not os.path.isdir(directory):
            os.makedirs(directory)

        with open(file_name, "w", encoding="utf-8") as out_file:
            json.dump(data, out_file)

        if job.error[-len("KeyboardInterrupt\n") :] == "KeyboardInterrupt\n":
            # job got interrupted because it took too long
            msg = f"Job hang: {file_name}"
            self.logger.error(msg)

    def _getProblemAgentInformation(self, job, registrant):  # noqa: C901
        """Parse data from a bad :class:`.Job` & :class:`~.agent_base.Agent` pair.

        Args:
            job (:class:`.Job`): error-producing job instance.
            registrant (:class:`~.agent_base.Agent`): registered agent corresponding to the bad job.

        Returns:
            ``dict``: information about problem agent, for debugging purposes.
        """
        data = {"error": job.error}
        if getTypeString(registrant) in ("EstimateAgent", "TargetAgent"):
            data.update(
                {
                    "julian_date": registrant.julian_date_epoch,
                    "calendar_date": registrant.julian_date_epoch.calendar_date,
                    "target_id": registrant.simulation_id,
                    "name": registrant.name,
                    "eci": registrant.eci_state,
                }
            )
        if getTypeString(registrant) == "EstimateAgent":
            target_agents = pickle.loads(KeyValueStore.getValue("target_agents"))
            tgt_agent = None
            for tgt_id, target in target_agents.items():
                if tgt_id == registrant.simulation_id:
                    tgt_agent = target
                    break

            data.update(registrant.nominal_filter.getPredictionResult())
            data.update(
                {
                    "state_estimate": registrant.state_estimate,
                    "error_covariance": registrant.error_covariance,
                    "x_dim": registrant.nominal_filter.x_dim,
                    "source": registrant.nominal_filter.source,
                }
            )
            if isinstance(registrant.nominal_filter, UnscentedKalmanFilter):
                data.update(
                    {
                        "gamma": registrant.nominal_filter.gamma,
                        "num_sigmas": registrant.nominal_filter.num_sigmas,
                    }
                )
            if tgt_agent:
                data.update(
                    {
                        "truth_state": tgt_agent.eci_state,
                        "truth_jd": tgt_agent.julian_date_epoch,
                        "truth_calendar": tgt_agent.julian_date_epoch.calendar_date,
                    }
                )
            else:
                self.logger.error("No matching TargetAgent for problem EstimateAgent!")

        for key, val in data.items():
            if isinstance(val, ndarray):
                data[key] = val.tolist()

            elif isinstance(val, (JulianDate, ScenarioTime)):
                data[key] = float(val)

            elif isinstance(val, Flag):
                data[key] = {
                    "name": val.name,
                    "value": val.value,
                    "repr": repr(val),
                }

        return data


class AgentPropagationRegistration(CallbackRegistration):
    """Registration for :class:`.TargetAgent` & :class:`.SensorAgent` truth propagation jobs."""

    def jobCreateCallback(self, **kwargs):
        """Create a :func:`.asyncPropagate` job & update :attr:`~.Agent.time` appropriately.

        This relies on a common interface for :meth:`.Dynamics.propagate`.

        KeywordArgs:
            new_time (:class:`.ScenarioTime`): payload indicating the current simulation time.

        Returns
            :class:`.Job`: job to be processed by :class:`.QueueManager`.
        """
        new_time = kwargs["new_time"]
        self.registrant.prunePropagateEvents()
        _datetime = julianDateToDatetime(self.registrant.julian_date_epoch)
        reductions = getReductionParameters(_datetime)
        for item in self.registrant.station_keeping:
            item.reductions = reductions

        job = Job(
            asyncPropagate,
            args=[
                self.registrant.dynamics,
                self.registrant.time,
                new_time,
                self.registrant.eci_state,
            ],
            kwargs={
                "station_keeping": self.registrant.station_keeping,
                # [NOTE][parallel-maneuver-event-handling] Step three: pass the event queue to the propagation process.
                "scheduled_events": self.registrant.propagate_event_queue,
            },
        )
        self.registrant.time = new_time

        return job

    def jobCompleteCallback(self, job):
        """Update an agent's :attr:`.Agent.eci_state` with the propagated state vector.

        Args:
            job (:class:`.Job`): job object that's returned when a job completes.
        """
        self.registrant.eci_state = job.retval


class AgentPropagationJobHandler(PropagationJobHandler):
    """Handle parallel jobs during :class:`.TargetAgent` & :class:`.SensorAgent` truth propagation.

    This determines what agents use imported data, and which use internal propagation.
    """

    callback_class = AgentPropagationRegistration

    def __init__(self, importer_db_path=None):
        """Initialize the job handler class to include imported observation data.

        Args:
            importer_db_path (``str``, optional): path to external importer database for pre-canned
                data. Defaults to ``None``.
        """
        super().__init__()

        self.data_missing_import_callbacks = []
        """"``list``: IDs of agents in the database that don't have a registered import callback."""

        self.log_data_missing_imports = True
        """``bool``: whether missing import callbacks needs to be logged."""

        self.importer_registry = {}
        """``dict``: registered agent importer callbacks.

        The idea here is that during :meth:`.executeJobs`, a batch of ephemeris data is pulled for
        the current time for _every_ :class:`~.agent_base.Agent` capable of using the "importer"
        model to update its state. Each applicable :class:`~.agent_base.Agent` will register a
        callback that will get called and handed its relevant :class:`.TruthEphemeris` for that
        that time step as an argument. This dictionary will be formatted so that the callbacks are
        organized by ID as to easily associate the ephemerides to the correct agent.
        """

        self._importer_db = None
        """:class:`.ImporterDatabase`: Input database object for loading :class:`.TruthEphemeris` objects."""
        if importer_db_path:
            self._importer_db = ImporterDatabase(db_path=importer_db_path)

    def registerCallback(self, registrant):
        """Register callback object that is used in parallel job creation and post-processing.

        The callback is specifically used by :meth:`~.TruthPropagationJobHandler.executeJobs` and
        :meth:`~.TruthPropagationJobHandler.handleProcessedJob`.

        Args:
            registrant (``object``): reference to the registration's calling object.

        Note:
            #. If the :attr:`~.Agent.realtime` is ``True``, use :func:`.asyncPropagate`.
            #. If neither are true query the database for :class:`.Ephemeris` items.
            #. If a valid :class:`.Ephemeris` returns, use :meth:`~.Agent.importState`.
            #. Otherwise, fall back to :func:`.asyncPropagate`.

        Raises:
            `ValueError`: when :attr:`~.Agent.realtime` is ``False``, but no
                :class:`.ImporterDatabase` was created.
        """
        if registrant.realtime is True:
            # Realtime propagation is on, so use `::asyncPropagate()`
            super().registerCallback(registrant)

        elif self._importer_db:
            # Realtime propagation is off, attempt to query database for valid `Ephemeris` objects
            query = Query(TruthEphemeris).filter(
                TruthEphemeris.agent_id == registrant.simulation_id
            )

            # If minimal truth data exists in the database, use importer model, otherwise default to
            # realtime propagation (and print warning that this happened).
            if self._importer_db.getData(query, multi=False) is None:
                msg = f"Could not find importer truth for {registrant.simulation_id}. "
                msg += "Defaulting to realtime propagation!"
                self.logger.warning(msg)
                super().registerCallback(registrant)
            else:
                self._registerImporterCallback(registrant.simulation_id, registrant.importState)

        else:
            msg = f"A valid ImporterDatabase was not established: {self._importer_db}"
            self.logger.error(msg)
            raise ValueError(msg)

    def _registerImporterCallback(self, agent_id, callback):
        """Register callback object that is used to update agents' states via imported data.

        The callback is specifically used by :meth:`~.TruthPropagationJobHandler.handleProcessedJob`.

        Args:
            agent_id (``int``): :attr:`Agent.simulation_id` that associates ephemerides to the
                registered :class:`~.agent_base.Agent`.
            callback (``callable``): method that gets called with the relevant ephemeris as an
                argument.
        """
        self.importer_registry[agent_id] = callback

    def generateJobs(self, **kwargs):
        """Generate list of propagation jobs to submit to the :class:`.QueueManager`.

        KeywordArgs:
            epoch_time (:class:`.ScenarioTime`): current simulation epoch.
            julian_date (:class:`.JulianDate`): current simulation Julian Date
            prior_julian_date (:class:`.JulianDate`): Julian Date at beginning of timestep

        Returns:
            ``list``: :class:`.Job` objects that will be submitted
        """
        # [NOTE][parallel-maneuver-event-handling] Step one: query for events and "handle" them.
        julian_date = kwargs["julian_date"]
        prior_julian_date = kwargs["prior_julian_date"]
        agent_propagation_events = defaultdict(list)
        relevant_events = getRelevantEvents(
            getDBConnection(),
            EventScope.AGENT_PROPAGATION,
            prior_julian_date,
            julian_date,
        )
        for event in relevant_events:
            agent_propagation_events[event.scope_instance_id].append(event)

        jobs = []
        epoch_time = kwargs["epoch_time"]
        for registration in self.callback_registry:
            registrant_events = agent_propagation_events[registration.registrant.simulation_id]
            for event in registrant_events:
                event.handleEvent(registration.registrant)

            job = registration.jobCreateCallback(new_time=epoch_time)
            self.job_id_registration_dict[job.id] = registration
            jobs.append(job)

        return jobs

    def deregisterCallback(self, callback_id):
        """Remove an agent's :class:`.AgentPropagationRegistration` from this :class:`.PropagationJobHandler`.

        Args:
            callback_id (int): Unique identifier of the agent who's registration is being removed.
        """
        super().deregisterCallback(callback_id)
        if callback_id in self.importer_registry:
            del self.importer_registry[callback_id]

    def executeJobs(self, **kwargs):
        """Import ephemerides, queue parallel truth propagation jobs, and wait for completion.

        Overrides :meth:`.JobHandler.executeJobs` to import external ephemerides.

        KeywordArgs:
            datetime_epoch (datetime): current simulation epoch.
        """
        if self._importer_db:
            self._importEphemerides(kwargs["datetime_epoch"])

        super().executeJobs(**kwargs)

    def _importEphemerides(self, datetime_epoch: datetime):
        """Import :class:`.TruthEphemeris` data from :class:`.ImporterDatabase`.

        Args:
            datetime_epoch (datetime): current simulation epoch.

        Raises:
            :class:`.MissingEphemerisError`: raised if the amount of :class:`.TruthEphemeris`
                returned from the DB do not match the amount of objects assigned to
                :attr:`.importer_registry`.
        """
        # This is the "Bulk Importer" implementation.
        query = (
            Query([TruthEphemeris])
            .join(Epoch)
            .filter(Epoch.timestampISO == datetime_epoch.isoformat(timespec="microseconds"))
        )
        current_ephemerides = self._importer_db.getData(query)

        # Ensure we have at least as many ephems as register import callbacks
        if len(current_ephemerides) < len(self.importer_registry):
            msg = f"Missing ephemeris data for importer model at time: {datetime_epoch.isoformat(timespec='microseconds')}"
            self.logger.error(msg)
            msg1 = f"Importer registry: {self.importer_registry}"
            self.logger.error(msg1)
            msg2 = f"Retrieved ephemerides: {current_ephemerides}"
            self.logger.error(msg2)
            raise MissingEphemerisError(datetime_epoch.isoformat(timespec="microseconds"))

        # Call registered importer callbacks
        for ephem in current_ephemerides:
            try:
                self.importer_registry[ephem.agent_id](ephem)

            # Caught if there are ephems without registered importer callbacks
            except KeyError:  # noqa: PERF203
                # Only log if we haven't yet logged this warning
                if self.log_data_missing_imports:
                    # Add to list for logging
                    self.data_missing_import_callbacks.append(ephem.agent_id)

        # Log the missing importer callbacks
        self._logMissingImporterCallbacks()

    def _logMissingImporterCallbacks(self):
        """Log agents that don't have the corresponding target registered in :attr:`importer_registry`.

        This means we are using real-time propagation only, but there are agent ephemerides for
        this timestep in the database.
        """
        # Logs if we found imported ephemerides for targets that didn't register
        #   using the `importer_registry`
        if self.log_data_missing_imports:
            if self.data_missing_import_callbacks:
                msg = f"Didn't have importer callbacks registered for agents: {self.data_missing_import_callbacks}"
                self.logger.warning(msg)
            self.log_data_missing_imports = False
