# Standard Library Imports
import logging
from json import dump
# Pip Package Imports
from numpy import ndarray
from sqlalchemy.orm import Query
# RESONAATE Imports
from .producer import QueueManager
from ..common.utilities import getTypeString, getTimeout
from ..common.exceptions import MissingEphemerisError, TaskTimeoutError
from ..data.data_interface import DataInterface
from ..data.ephemeris import TruthEphemeris
from ..data.query_util import addAlmostEqualFilter
from ..physics.time.stardate import JulianDate, ScenarioTime


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
    """Handle the tasking of :class:`.Worker` objects during the propagation step of the simulation.

    This handles what agents use imported data, and which use internal propagation.
    """

    def __init__(self):
        """Initialize the job handler class."""
        self.logger = logging.getLogger("resonaate")
        ## Dictionary used to correspond `DispyJob` id's to callback registrations.
        # This dictionary is updated in `self.ticToc` and utilized in `self.handleJobResults` to
        #   make sure the correct callback registrants are being updated when their job completes.
        self.cur_registration_task_ids = {}

        ## Queue manager class instance.
        self.queue_mgr = QueueManager(processed_callback=self.handleProcessedTask)

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

    def registerPropagateCallback(self, registration):
        """Register a :class:`.CallbackRegistration` to be executed during :meth:`~.PropagateJobHandler.executeJobs`.

        Args:
            registration (:class:`.CallbackRegistration`): registration callback to register
        """
        message = "Use `CallbackRegistration` to register job callbacks, not"
        assert(isinstance(registration, CallbackRegistration)), "{0} {1}.".format(message, type(registration))
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

    def handleProcessedTask(self, task):
        """Determines how the :class:`.QueueManager` handles completed tasks.

        Args:
            task (:class:`.Task`): completed task object to handle
        """
        if task.status == 'processed':
            self.cur_registration_task_ids[task.id].job_callback(task)

        else:
            registrant = self.cur_registration_task_ids[task.id].registrant
            self._logProblemAgent(task, registrant)

    def executeJobs(self, clock):
        """Perform main job handling logic during the propagation set of the simulation.

        Import all :class:`.TruthEphemeris` objects with the current :class:`.JulianDate`, then
        call all importer callbacks with these ephemerides. Then pass a :class:`.Task` object for
        each :class:`.CallbackRegistration` in :attr:`propagate_registry` to the
        :class:`.QueueManager`. Finally, wait until the tasks have all been processed.

        Args:
            clock (:class:`.ScenarioClock`): updated clock object with the current time step data

        Raises:
            MissingEphemerisError: raised if the database doesn't have enough ephemerides at this timestep
        """
        # This is the "Bulk Importer" implementation.
        query = Query([TruthEphemeris])
        query = addAlmostEqualFilter(query, TruthEphemeris, 'julian_date', clock.julian_date_epoch)
        shared_interface = DataInterface.getSharedInterface()
        current_ephemerides = shared_interface.getData(query)

        # Ensure we have at least as many ephems as register import callbacks
        if len(current_ephemerides) < len(self.importer_registry):
            self.logger.error(
                "Missing ephemeris data for importer model at time: {0}".format(float(clock.julian_date_epoch))
            )
            raise MissingEphemerisError(clock.julian_date_epoch)

        # Call registered importer callbacks
        for ephem in current_ephemerides:
            try:
                self.importer_registry[ephem.unique_id](ephem)

            # Caught if there are ephems without registered importer callbacks
            except KeyError:
                # Only log if we haven't yet logged this warning
                if self.log_data_missing_imports:
                    # Add to list for logging
                    self.data_missing_import_callbacks.append(ephem.unique_id)

        # Log the missing importer callbacks
        self._logMissingImporterCallbacks()

        for registration in self.propagate_registry:
            # Create a task
            task = registration.callback(clock.time)
            self.cur_registration_task_ids[task.id] = registration

            # Submit the task
            self.queue_mgr.queueTasks(task)

        # Wait for tasks to complete
        try:
            self.queue_mgr.blockUntilProcessed(
                timeout=getTimeout(self.propagate_registry)
            )
        except TaskTimeoutError:
            # tasks took longer to complete than expected
            for task_id in self.queue_mgr.queued_task_ids:
                registration = self.cur_registration_task_ids[task_id]
                msg = "Tasks {0} haven't completed after {1} seconds. Callback '{2}' on Agent '{3}'"
                self.logger.error(
                    msg.format(
                        task_id,
                        5 * len(self.propagate_registry),
                        registration.callback,
                        registration.registrant.name,
                    )
                )

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

    def _logProblemAgent(self, task, registrant):
        """Log information to a file if a :class:`.Task` returned with an error.

        Args:
            task (:class:`.Task`): task object that is in an error state
            registrant (:class:`.Agent`): agent corresponding to the bad task
        """
        data = _getProblemAgentInformation(task, registrant)
        file_name = 'error_{0}.json'.format(task.id)
        with open(file_name, 'w') as out_file:
            dump(data, out_file)
        if task.error[-len("KeyboardInterrupt\n"):] == "KeyboardInterrupt\n":
            # task got interrupted because it took too long
            self.logger.error("Task hang: {0}".format(file_name))
        raise Exception(
            "Error occurred in task {0.id}:\n\t{0.error}".format(task)
        )


def _getProblemAgentInformation(task, registrant):
    """Parse data from a bad :class:`.Task` & :class:`.Agent` pair."""
    data = {}
    data["error"] = task.error
    if getTypeString(registrant) in ("EstimateAgent", "TargetAgent"):
        data.update({
            "julian_date": "self._clock.julian_date_epoch",
            "calendar_date": "self._clock.julian_date_epoch.calendar_date",
            "target_id": registrant.name,
            "name": registrant.simulation_id,
        })
    if getTypeString(registrant) == "EstimateAgent":
        data.update(registrant.nominal_filter.getPredictionResult())
        data.update({
            "state_estimate": registrant.state_estimate,
            "error_covariance": registrant.error_covariance,
            "num_sigmas": registrant.nominal_filter.num_sigmas,
            "x_dim": registrant.nominal_filter.x_dim,
            "gamma": registrant.nominal_filter.gamma,
        })

    for key, val in data.items():
        if isinstance(val, ndarray):
            data[key] = val.tolist()

        elif isinstance(val, (JulianDate, ScenarioTime)):
            data[key] = float(val)

    return data
