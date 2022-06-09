# Standard Library Imports
import pickle
import json
import logging
import os.path
# Pip Package Imports
from numpy import ndarray
from sqlalchemy.orm import Query
# RESONAATE Imports
from .producer import QueueManager
from ..common.behavioral_config import BehavioralConfig
from ..common.utilities import getTypeString, getTimeout
from ..common.exceptions import MissingEphemerisError, JobTimeoutError
from ..data.ephemeris import TruthEphemeris
from ..data.importer_database import ImporterDatabase
from ..data.query_util import addAlmostEqualFilter
from ..parallel import getRedisConnection
from ..physics.time.stardate import JulianDate, ScenarioTime
from ..dynamics.integration_events.event_stack import EventStack


class CallbackRegistration:
    """Abstract a callback that gets registered to :meth:`~.PropagateJobHandler.executeJobs`."""

    VALID_JOB_TYPES = ("asyncPredict", "asyncPropagate", )

    def __init__(self, registrant, callback, job_computation, job_callback, job_dependencies=None):
        """Construct a CallbackRegistration object.

        Args:
            registrant (``object``): reference to the calling object
            callback (``callable``): function to be called on the registrant
            job_computation (``callable``): job that will be created when `callback` is called
            job_callback (``callable``): function to be called when created job completes
            job_dependencies (``iter``): list of modules that `job_computation` depends on
        """
        self.registrant = registrant
        self.callback = callback
        self.job_computation = job_computation
        self.job_callback = job_callback
        self.job_dependencies = job_dependencies

    @property
    def job_key(self):
        """``str``: key to classify the job this CallbackRegistration creates."""
        return str(self.job_computation) + str(self.job_dependencies)


class PropagateJobHandler:
    """Handle the jobs of :class:`.Worker` objects during the propagation step of the simulation.

    This handles what agents use imported data, and which use internal propagation.
    """

    def __init__(self, importer_db_path=None):
        """Initialize the job handler class.

        Args:
            importer_db_path (``str``, optional): path to external importer database for pre-canned
                data. Defaults to ``None``.
        """
        self.logger = logging.getLogger("resonaate")
        ## Dictionary used to correspond `DispyJob` id's to callback registrations.
        # This dictionary is updated in `self.ticToc` and utilized in `self.handleJobResults` to
        #   make sure the correct callback registrants are being updated when their job completes.
        self.cur_registration_job_ids = {}

        ## Queue manager class instance.
        self.queue_mgr = QueueManager(processed_callback=self.handleProcessedJob)

        ## List of `satNum`s that had entries in the database, but didn't have an import callback.
        self.data_missing_import_callbacks = []

        ## Flag used to indicate whether missing import callbacks still need to be logged.
        self.log_data_missing_imports = True

        ## Collection of registrations.
        self.propagate_registry = []

        ## Dictionary of `Agent` callbacks that accept `TruthEphemeris` objects as inputs.
        # The idea here is that during a `::ticToc()` iteration, the `ScenarioClock` will pull a batch of
        #   ephemeris data for the current time for _every_ `Agent` capable of using the "importer"
        #   model to update its state. Each applicable `Agent` will register a callback that will
        #   get called and handed its relevant `TruthEphemeris` object for that that time step as an
        #   argument.
        # This dictionary will be formatted so that the callbacks are organized by `satNum`
        #   attribute as to easily associate the ephemerides to the correct `Agent` class.
        self.importer_registry = {}

        # Input database object for loading `Ephemeris` objects
        self._importer_db = None
        if importer_db_path:
            self._importer_db = ImporterDatabase.getSharedInterface(db_url=importer_db_path)

    def registerPropagateCallback(self, registration):
        """Register a :class:`.CallbackRegistration` to be executed during :meth:`~.PropagateJobHandler.executeJobs`.

        Args:
            registration (:class:`.CallbackRegistration`): registration callback to register
        """
        msg = "Use `CallbackRegistration` to register job callbacks, not"
        assert(isinstance(registration, CallbackRegistration)), "{0} {1}.".format(msg, type(registration))
        self.propagate_registry.append(registration)

    def registerImporterCallback(self, sat_num, callback):
        """Register a callback to be executed during the import data pull in :meth:`~.PropagateJobHandler.executeJobs`.

        Args:
            satNum ``int``: :attr:`unique_id` that associates ephemerides to the registrant
                :class:`.Agent`
            callback ``callable``: method that gets called with the relevant ephemeris as an
                argument
        """
        self.importer_registry[sat_num] = callback

    def handleProcessedJob(self, job):
        """Determines how the :class:`.QueueManager` handles completed jobs.

        Args:
            job (:class:`.Job`): completed job object to handle
        """
        if job.status == 'processed':
            self.cur_registration_job_ids[job.id].job_callback(job)

        else:
            registrant = self.cur_registration_job_ids[job.id].registrant
            self._logProblemAgent(job, registrant)

    def executeJobs(self, clock):
        """Perform main job handling logic during the propagation set of the simulation.

        Import all :class:`.TruthEphemeris` objects with the current :class:`.JulianDate`, then
        call all importer callbacks with these ephemerides. Then pass a :class:`.Job` object for
        each :class:`.CallbackRegistration` in :attr:`propagate_registry` to the
        :class:`.QueueManager`. Finally, wait until the jobs have all been processed.

        Args:
            clock (:class:`.ScenarioClock`): updated clock object with the current time step data

        Raises:
            MissingEphemerisError: raised if the database doesn't have enough ephemerides at this timestep
        """
        # Load imported `Ephemeris` objects from input database
        if self._importer_db:
            self.loadImportedEphemerides(clock.julian_date_epoch)

        # Add propgation jobs to job queue
        jobs = []
        for registration in self.propagate_registry:
            # Create a job
            job = registration.callback(clock.time)
            self.cur_registration_job_ids[job.id] = registration
            jobs.append(job)

        # Submit the job
        self.queue_mgr.queueJobs(*jobs)

        # Wait for jobs to complete
        try:
            self.queue_mgr.blockUntilProcessed(
                timeout=getTimeout(self.propagate_registry)
            )
        except JobTimeoutError:
            # jobs took longer to complete than expected
            for job_id in self.queue_mgr.queued_job_ids:
                registration = self.cur_registration_job_ids[job_id]
                msg = "Jobs {0} haven't completed after {1} seconds. Callback '{2}' on Agent '{3}'"
                self.logger.error(
                    msg.format(
                        job_id,
                        5 * len(self.propagate_registry),
                        registration.callback,
                        registration.registrant.name,
                    )
                )

        EventStack.logAndFlushEvents()

    def loadImportedEphemerides(self, epoch):
        """Import `Ephemeris` data from input database.

        Args:
            epoch (:class:`.JulianDate`): jd epoch to query DB for data

        Raises:
            MissingEphemerisError: raised if the amount of `Ephemeris` objects
                returned from the DB do not match the amount of objects
                assigned to the Importer Registry.
        """
        # This is the "Bulk Importer" implementation.
        query = Query([TruthEphemeris])
        query = addAlmostEqualFilter(query, TruthEphemeris, 'julian_date', epoch)
        current_ephemerides = self._importer_db.getData(query)

        # Ensure we have at least as many ephems as register import callbacks
        if len(current_ephemerides) < len(self.importer_registry):
            self.logger.error(
                "Missing ephemeris data for importer model at time: {0}".format(float(epoch))
            )
            self.logger.error(
                "Importer registry: {0}".format(self.importer_registry)
            )
            self.logger.error(
                "Retrieved ephemerides: {0}".format(current_ephemerides)
            )
            raise MissingEphemerisError(epoch)

        # Call registered importer callbacks
        for ephem in current_ephemerides:
            try:
                self.importer_registry[ephem.agent_id](ephem)

            # Caught if there are ephems without registered importer callbacks
            except KeyError:
                # Only log if we haven't yet logged this warning
                if self.log_data_missing_imports:
                    # Add to list for logging
                    self.data_missing_import_callbacks.append(ephem.agent_id)

        # Log the missing importer callbacks
        self._logMissingImporterCallbacks()

    def _logMissingImporterCallbacks(self):
        """Log when imported ephemerides don't have the corresponding target registered in :attr:`importer_registry`.

        This means we are using real-time propagation only, but their are target or sensing
        agent ephemerides for this timestep in the database.
        """
        # Logs if we found imported ephemerides for targets that didn't register
        #   using the `importer_registry`
        if self.log_data_missing_imports:
            if self.data_missing_import_callbacks:
                message = "Didn't have importer callbacks registered for satellite numbers"
                self.logger.warning("{0} '{1}'".format(message, self.data_missing_import_callbacks))
            self.log_data_missing_imports = False

    def _logProblemAgent(self, job, registrant):
        """Log information to a file if a :class:`.Job` returned with an error.

        Args:
            job (:class:`.Job`): job object that is in an error state
            registrant (:class:`.Agent`): agent corresponding to the bad job
        """
        data = self._getProblemAgentInformation(job, registrant)
        file_name = os.path.join(
            BehavioralConfig.getConfig().debugging.OutputDirectory,
            'Agents',
            "error_{job.id}_{registrant.simulation_id}.json"
        )
        with open(file_name, 'w') as out_file:
            json.dump(data, out_file)
        if job.error[-len("KeyboardInterrupt\n"):] == "KeyboardInterrupt\n":
            # job got interrupted because it took too long
            self.logger.error("Job hang: {0}".format(file_name))
        raise Exception(
            "Error occurred in job {0.id}:\n\t{0.error}".format(job)
        )

    def _getProblemAgentInformation(self, job, registrant):
        """Parse data from a bad :class:`.Job` & :class:`.Agent` pair."""
        data = {}
        data["error"] = job.error
        if getTypeString(registrant) in ("EstimateAgent", "TargetAgent"):
            data.update({
                "julian_date": registrant.julian_date_epoch,
                "calendar_date": registrant.julian_date_epoch.calendar_date,
                "target_id": registrant.simulation_id,
                "name": registrant.name,
                "eci": registrant.eci_state,
            })
        if getTypeString(registrant) == "EstimateAgent":
            target_agents = pickle.loads(getRedisConnection().get('target_agents'))
            tgt_agent = None
            for tgt_id, target in target_agents.items():
                if tgt_id == registrant.simulation_id:
                    tgt_agent = target
                    break

            data.update(registrant.nominal_filter.getPredictionResult())
            data.update({
                "state_estimate": registrant.state_estimate,
                "error_covariance": registrant.error_covariance,
                "num_sigmas": registrant.nominal_filter.num_sigmas,
                "x_dim": registrant.nominal_filter.x_dim,
                "gamma": registrant.nominal_filter.gamma,
                "source": registrant.nominal_filter.source,
            })
            if tgt_agent:
                data.update({
                    "truth_state": tgt_agent.eci_state,
                    "truth_jd": tgt_agent.julian_date_epoch,
                    "truth_calendar": tgt_agent.julian_date_epoch.calendar_date,
                })
            else:
                self.logger.error("No matching TargetAgent for problem EstimateAgent!")

        for key, val in data.items():
            if isinstance(val, ndarray):
                data[key] = val.tolist()

            elif isinstance(val, (JulianDate, ScenarioTime)):
                data[key] = float(val)

        return data
