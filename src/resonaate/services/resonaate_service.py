# Standard Library Imports
from queue import PriorityQueue, Empty
from threading import Thread, Event
from enum import Enum
from json import dumps
from time import sleep, time
from logging import INFO, WARNING
from collections import Counter
from datetime import datetime
from traceback import format_exc
# Pip Package Imports
from sqlalchemy.orm import Query
# Package Imports
from resonaate.common.behavioral_config import BehavioralConfig
from resonaate.common.logger import Logger
from resonaate.data.data_interface import DataInterface, ManualSensorTask
from resonaate.data.ephemeris import EstimateEphemeris
from resonaate.data.observation import Observation
from resonaate.data.query_util import addAlmostEqualFilter
from resonaate.parallel import isMaster, resetMaster, REDIS_QUEUE_LOGGER
from resonaate.parallel.worker import WorkerManager
from resonaate.physics.time.stardate import JulianDate, julianDateToDatetime
from resonaate.scenario.scenario import Scenario
from resonaate.services.output_processing import mungeLostUCTData, determineCurrentLeader


class ServiceMessage:
    """Abstract base class for messages handled by :class:`.ResonaateService` ."""

    PRIORITY = -1
    """int: Priority with which this message type is added to the queue."""

    def __lt__(self, other):
        """Overload comparison operator so messages can be sorted in ``PriorityQueue``."""
        raise NotImplementedError

    def __repr__(self):
        """Return a string representation of this :class:`.ServiceMessage`."""
        raise NotImplementedError


class InitMessage(ServiceMessage):
    """Message used to initialize a Resonaate scenario."""

    PRIORITY = 0
    """int: Priority with which :class:`.InitMessage`s are added to the queue.

    Init messages are enqueued with the highest priority, so that the Resonaate scenario is updated
    before other messages are handled.
    """

    EXPECTED_FIELDS = set(["targetList", "sensorConf", "jDate", "targetEvents", "sensorEvents"])
    """set: Set of fields expected to be present in an initialization message's contents."""

    def __init__(self, contents):
        """Construct an :class:`.InitMessage` object with the given contents.

        Args:
            contents (dict): Dictionary of initialization message values. The format of this
                message is extensively documented in 'docs/markdown/initialization.md'.
        """
        self.contents = contents

    def __lt__(self, other):
        """:class:`.InitMessage`s can be sorted based on their 'jDate' contents."""
        return self.contents['jDate'] < other.contents['jDate']

    def __repr__(self):
        """Give brief description of contents of init message."""
        return "InitMessage(targetList={0} targets, sensorConf={sensorConf}, jDate={jDate}, " + \
               "targetEvents={1} events, sensorEvents={2} events)".format(
                   len(self.contents["targetList"]),
                   len(self.contents["targetEvents"]),
                   len(self.contents["sensorEvents"]),
                   **self.contents
               )


class DiscontinueMessage(ServiceMessage):
    """Message used to update service's state to ``STOPPED`` and/or destroy the Resonaate scenario."""

    PRIORITY = 1
    """int: Priority with which :class:`.DiscontinueMessage`s are added to the queue.

    Discontinue messages need to be prioritized above all but :class:`.InitMessage`s to avoid
    potential excess processing. E.g. the Resonaate scenario should be destroyed before time target
    messages are handled, to avoid the inherent processing.
    """

    def __init__(self, destory_scenario=False):
        """Construct an :class:`.DiscontinueMessage` object.

        Args:
            destroy_scenario (bool): Flag indicating whether to destroy the Resonaate scenario.
        """
        self.destroy_scenario = destory_scenario

        self._created = time()

    def __lt__(self, other):
        """:class:`.DiscontinueMessage`s can be sorted based on when they were created."""
        return self._created < other._created  # pylint: disable=protected-access

    def __repr__(self):
        """Return a string representation of this :class:`.DiscontinueMessage`."""
        return "DiscontinueMessage(destroy_scenario={0}, _created={1})".format(
            self.destroy_scenario,
            self._created
        )


class TimeTargetMessage(ServiceMessage):
    """Message used to propagate a Resonaate scenario forward in time."""

    PRIORITY = 3
    """int: Priority with which :class:`.TimeTargetMessage`s are added to the queue.

    Time target messages should be handled last with respect to the other types of messages.
    """

    def __init__(self, time_target):
        """Construct an :class:`.TimeTargetMessage` object with the given time target.

        Args:
            time_target (JulianDate): Julian date to propagate the Resonaate scenario to.
        """
        self.time_target = time_target
        if not isinstance(self.time_target, JulianDate):
            err = "Time target must be a JulianDate not '{0}'".format(type(self.time_target))
            raise TypeError(err)

    def __lt__(self, other):
        """:class:`.TimeTargetMessage`s can be sorted based on their corresponding time target."""
        return self.time_target < other.time_target

    def __repr__(self):
        """Return a string representation of this :class:`.TimeTargetMessage`."""
        date_time = julianDateToDatetime(self.time_target)

        return "TimeTargetMessage(time_target=JulianDate({0})|ISO({1}))".format(
            float(self.time_target),
            date_time.isoformat()
        )


class ManualSensorTaskMessage(ServiceMessage):
    """Message used to manually set tasking priorities for Resonaate scenario's sensor network."""

    PRIORITY = 2
    """int: Priority with which :class:`.ManualSensorTaskMessage`s are added to the queue.

    Observation priority messages should be handled before time target messages so that the
    priority is applied during all applicable scenario propagation.
    """

    OBS_PRIORITY_MAPPING = {
        1: 1.0,  # "low"
        2: 1.5,  # "med"
        3: 2.00,  # "high"
    }
    """dict: Dictionary mapping values from an operator interface to tasking strategy multipliers.

    [TODO] These mappings need to be tuned, especially if the way they are used internally changes
        from the current 'row multiplication' implementation.
    """

    def __init__(self, target_id, obs_priority, start_time, end_time, message_id):
        """Construct a :class:`.ManualSensorTask` object with given parameters.

        Args:
            unique_id (int): Satellite number for target.
            obs_priority (float): Scalar that indicates how important it is that this target be observed.
            start_time (JulianDate): :class:`.JulianDate` for when this prioritization should start.
            end_time (JulianDate): :class:`.JulianDate` for when this prioritization should end.
            message_id (str): Unique identifier for message.
        """
        self.unique_id = target_id
        if not isinstance(self.unique_id, int):
            err = "Target ID must be an integer, not '{0}'".format(type(self.unique_id))
            raise TypeError(err)

        self.obs_priority = obs_priority
        if not isinstance(self.obs_priority, float):
            err = "Observation priority must be a float, not '{0}'".format(type(self.obs_priority))
            raise TypeError(err)

        self.start_time = start_time
        if not isinstance(self.start_time, JulianDate):
            err = "Start time must be a JulianDate, not '{0}'".format(type(self.start_time))
            raise TypeError(err)

        self.end_time = end_time
        if not isinstance(self.end_time, JulianDate):
            err = "Start time must be a JulianDate, not '{0}'".format(type(self.end_time))
            raise TypeError(err)

        self.message_id = message_id
        if not isinstance(self.message_id, str):
            err = "Message ID must be a string, not '{0}'".format(type(self.message_id))
            raise TypeError(err)

    def __lt__(self, other):
        """:class:`.ManualSensorTaskMessage`s can be sorted based on their ``start_time`` attribute."""
        return self.start_time < other.start_time

    def __repr__(self):
        """Return a string representation of this :class:`.ManualSensorTaskMessage`."""
        start_date_time = julianDateToDatetime(self.start_time)
        end_date_time = julianDateToDatetime(self.end_time)
        return "ManualSensorTaskMessage(unique_id={0}, obs_priority={1}, start_time={2}|{3}, end_time={4}|{5})".format(
            self.unique_id,
            self.obs_priority,
            "JulianDate({0})".format(float(self.start_time)),
            "ISO({0})".format(start_date_time.isoformat()),
            "JulianDate({0})".format(float(self.end_time)),
            "ISO({0})".format(end_date_time.isoformat())
        )


class ManualSensorTaskResponse:
    """Message used to indicate the success of a :class:`.ManualSensorTaskMessage` ."""

    def __init__(self, task_message, error_message=""):
        """Construct a :class:`.ManualSensorTask` object with given parameters.

        Args:
            task_message (ManualSensorTaskMessage): Processed :class:`.ManualSensorTaskMessage`
                that this is a response to.
            error_message (str): String describing an error that occurred while trying to process
                ``task_message`` .
        """
        self.task_message = task_message
        if not isinstance(self.task_message, ManualSensorTaskMessage):
            err = "Task message must be a ManualSensorTaskMessage, not '{0}'".format(type(self.task_message))
            raise TypeError(err)

        self.error_message = error_message
        if not isinstance(self.error_message, str):
            err = "Error message must be a string, not '{0}'".format(type(self.error_message))
            raise TypeError(err)

    def jsonify(self):
        """Return a valid JSON analyze-rso-reply message."""
        return dumps({
            "createdAt": datetime.utcnow().isoformat() + "+00:00",
            "createdBy": "resonaate",
            "replyToUuid": self.reply_to_id,
            "details": self.details,
            "label": self.label,
            "primaryId": self.primary_id,
            "secondaryIds": "",
            "status": self.status,
            "version": "1.9"
        })

    @property
    def primary_id(self):
        """str: Satellite number for target RSO."""
        return str(self.task_message.unique_id)

    @property
    def status(self):
        """str: String indicating the status of the sensor tasking."""
        if self.error_message:
            return "Failed"
        # else
        return "Complete"

    @property
    def label(self):
        """str: Label for this response."""
        return "Resonaate Observation Request for {0}: {1}".format(self.primary_id, self.status)

    @property
    def details(self):
        """str: Details of sensor tasking."""
        if self.error_message:
            return "Could not apply observation request: {0}".format(self.error_message)
        # else
        return "Applied observation priority of {0} to RSO {1}".format(
            self.task_message.obs_priority,
            self.primary_id
        )

    @property
    def reply_to_id(self):
        """str: Unique identifier for sensor tasking."""
        return self.task_message.message_id


class ResonaateService:
    """Base class implementing a service layer for Resonaate."""

    MESSAGE_WAIT = 3
    """int: Number of seconds to wait between checking for stop signal."""

    LOG_DROPPED_INTERVAL = 10
    """int: Number of seconds between logging all dropped messages."""

    class State(Enum):
        """Possible states for the :class:`.ResonaateService` to be in."""

        UNINITIALIZED = 0
        """Enum: No Resonaate scenario is initialized."""

        RUNNING = 1
        """Enum: Time target messages will result in processing of Resonaate scenario and output generation."""

        STOPPED = 2
        """Enum: Resonaate scenario initialized, but time target messages will be ignored."""

    def __init__(self):
        """Construct a :class:`.ResonaateService` object with supporting infrastructure."""
        self.logger = Logger('resonaate', path=BehavioralConfig.getConfig().logging.OutputLocation)
        self._master = None
        self._scenario = None
        self._state = self.State.UNINITIALIZED

        self._message_handlers = {
            InitMessage: self._handleInitMessage,
            TimeTargetMessage: self._handleTimeTargetMessage,
            DiscontinueMessage: self._handleDiscontinueMessage,
            ManualSensorTaskMessage: self._handleManualSensorTaskMessage,
        }
        self._stop_message_handling = Event()
        self._message_queue = None
        self._message_handling_thread = None
        self._dropped_messages = None
        self._dropped_logging_thread = None

        if self.is_master:
            self.logger.info("Initializing master instance of Resonaate.")
            self._removeOldSensorTasks()
            self.startMessageHandling()
            REDIS_QUEUE_LOGGER.setLevel(WARNING)
            self._worker_manager = WorkerManager(daemonic=True)

        else:  # slave instance of resonaate
            self.logger.info("Initializing slave instance of Resonaate.")
            REDIS_QUEUE_LOGGER.setLevel(INFO)
            self._worker_manager = WorkerManager(daemonic=True)
            self._updateState(self.State.RUNNING)

        self._worker_manager.startWorkers()
        self.logger.debug("Started workers.")

    def enqueueMessage(self, message):
        """Put a message on the queue to be handled.

        Args:
            message (ServiceMessage): Message to enqueue.
        """
        if not isinstance(message, ServiceMessage):
            err = "Can't enqueue message of type '{0}'".format(type(message))
            raise ValueError(err)

        if self._message_queue is None:
            err = "Can't enqueue message: internal queue doesn't exist."
            raise RuntimeError(err)

        self._message_queue.put((message.PRIORITY, message))

    def startMessageHandling(self):
        """Initialize internal message queue and start message handling thread."""
        self._stop_message_handling.clear()
        self._message_queue = PriorityQueue()
        self._message_handling_thread = Thread(target=self._messageHandler)
        self._message_handling_thread.start()
        self._dropped_messages = PriorityQueue()
        self._dropped_logging_thread = Thread(target=self._logDroppedMessages)
        self._dropped_logging_thread.start()
        self.logger.debug("Started internal message handling.")

    def stopMessageHandling(self, join_queue=True):
        """Terminate the message handling thread.

        Depending on service state and the messages that are currently queued, this method can
        take a significant amount of time to return if ``join_queue`` is ``True`` .

        Args:
            join_queue (bool,optional): Boolean indicating whether to wait for queued messages to
                be processed before terminating the message handling thread. If this flag is not
                set to ``True`` , then all messages currently on the queue are dropped.
        """
        if join_queue:
            self._message_queue.join()

        self._stop_message_handling.set()
        self._message_handling_thread.join()
        self._message_queue = None
        self._message_handling_thread = None
        self._dropped_logging_thread.join()
        self._dropped_messages = None
        self._dropped_logging_thread = None
        self.logger.debug("Stopped internal message handling.")

    def handleEstimateOutput(self, estimate):
        """Handle outputting a single estimate message.

        Note:
            This method should be overwritten by child classes to handle output in a specific way.
            By default, this method just logs the message.

        Args:
            estimate (dict): EstimateAgent data dictionary to output.
        """
        self.logger.info("Output estimate: {0}".format(estimate))

    def handleObservationOutput(self, observation):
        """Handle outputting a single observation message.

        Note:
            This method should be overwritten by child classes to handle output in a specific way.
            By default, this method just logs the message.

        Args:
            observation (dict): Observation data dictionary to output.
        """
        self.logger.info("Output observation: {0}".format(observation))

    def handleManualSensorTaskResponse(self, task_response):
        """Handle response generated by processing a :class:`.ManualSensorTaskMessage` .

        Note:
            This method should be overwritten by child classes to handle output in a specific way.
            By default, this method just logs the details of the message processing.

        Args:
            task_response (ManualSensorTaskResponse): Response containing details of the message
                processing.
        """
        self.logger.info(task_response.details)

    def waitForHandler(self, timeout=None):
        """Wait for all currently queued messages to be handled.

        Args:
            timeout (float, optional): Number of seconds to wait for messages to be handled before
                returning False.
        Returns:
            bool: ``True`` if all messages have been handled, ``False`` if ``timeout`` was met.
        """
        if timeout:
            timeout = float(timeout)
            while not self.all_messages_handled and timeout > 0:
                sleep(0.25)
                timeout -= 0.25

        else:
            while not self.all_messages_handled:
                sleep(0.25)

        return self.all_messages_handled

    @property
    def all_messages_handled(self):
        """bool: indication of whether all queued messages have been handled."""
        return self._message_queue.unfinished_tasks == 0

    @property
    def state(self):
        """ResonaateService.State: current state of the :class:`.ResonaateService` object."""
        return self._state

    @property
    def is_master(self):
        """bool: Indication of whether this :class:`.ResonaateService` instance is master."""
        if self._master is None:
            self._master = isMaster()

        return self._master

    def _removeOldSensorTasks(self):
        """Remove old dynamic sensor tasks from the database."""
        query = Query([ManualSensorTask]).filter(ManualSensorTask.is_dynamic == True)  # noqa: E712
        shared_interface = DataInterface.getSharedInterface()
        removed_count = shared_interface.deleteData(query)
        self.logger.debug("Removed {0} dynamic sensor tasks from the database.".format(removed_count))

    def _dropMessage(self, dropped_message):
        """Drop a message so that it can be logged later.

        Args:
            dropped_message (ServiceMessage): Message being dropped.
        """
        if self._dropped_messages is None:
            err = "Can't drop message: internal queue doesn't exist."
            raise RuntimeError(err)

        self._dropped_messages.put((dropped_message.PRIORITY, dropped_message))

    def _logDroppedMessages(self):
        """Log all messages that have been dropped on an interval."""
        while not self._stop_message_handling.is_set():
            sleep(self.LOG_DROPPED_INTERVAL)

            dropped_count = Counter()
            most_recent = {}
            while not self._dropped_messages.empty():
                priority, dropped_message = self._dropped_messages.get()
                dropped_count[priority] += 1
                most_recent[priority] = dropped_message

            for priority in most_recent.keys():
                self.logger.info("Dropped {0} messages of priority '{1}' in past {2} seconds. Most recent: {3}".format(
                    dropped_count[priority],
                    priority,
                    self.LOG_DROPPED_INTERVAL,
                    most_recent[priority]
                ))

    def _updateState(self, state):
        """Update the state of the Resonaate service and log the transition.

        Args:
            state (State): State to transition to.
        """
        if isinstance(state, self.State):
            self._state = state

            if self._scenario is None:
                self.logger.info("Set service state to '{0}'.".format(self._state))

            else:
                self.logger.info("Set service state to '{0}'. Current scenario clock: {1}".format(
                    self._state,
                    self._scenario.clock.julian_date_epoch
                ))

        else:
            err = "Invalid state update: {0}".format(state)
            raise ValueError(err)

    def _messageHandler(self):
        """Loop over message queue, handling messages as they're enqueued."""
        while not self._stop_message_handling.is_set():
            handler = None
            try:
                _, message = self._message_queue.get(timeout=self.MESSAGE_WAIT)

            except Empty:
                pass

            else:
                handler = self._message_handlers[type(message)]

            if handler:
                try:
                    handler(message)

                except Exception as err:
                    self.logger.error(format_exc())
                    raise RuntimeError from err

                else:
                    self._message_queue.task_done()

    def _handleInitMessage(self, message):
        """Construct the scenario specified in the init message and update the service state.

        Args:
            message (InitMessage): Initialization message specifying the new Resonaate scenario.
        """
        self.logger.debug("Loading scenario...")
        self._scenario = Scenario.fromConfig(message.contents, start_workers=False)
        self.logger.debug("Loaded.")

        self.logger.debug("Updating state...")
        if self._state != self.State.RUNNING:
            self._updateState(self.State.RUNNING)

    def _handleTimeTargetMessage(self, message):
        """If service is in running state, propagate the scenario forward to the given time target.

        Args:
            message (TimeTargetMessage): Time target message specifying the time to propagate to.
        """
        if self._state == self.State.RUNNING:
            message_delta_seconds = float(message.time_target - self._scenario.clock.julian_date_epoch) * 24 * 60 * 60

            # Occurs if we fast-forward with new init, old TimeTarget mesages will be in the past
            if message.time_target < self._scenario.clock.julian_date_epoch:
                self._dropMessage(message)

            elif message_delta_seconds > self._scenario.clock.dt_step:
                # Break this processing up into smaller chunks so that the service remains
                # responsive to other messages.
                segments = int(round(message_delta_seconds / self._scenario.clock.dt_step))
                for step in range(segments):
                    segment_time_target = (self._scenario.clock.dt_step * (step + 1)).convertToJulianDate(
                        self._scenario.clock.julian_date_epoch
                    )
                    self.enqueueMessage(TimeTargetMessage(segment_time_target))

            else:
                # Propagate scenario forward in time
                self._scenario.propagateTo(message.time_target)

                # Get `DataInterface` for querying for data
                shared_interface = DataInterface.getSharedInterface()

                # Grab estimate data from db
                query = Query([EstimateEphemeris])
                query = addAlmostEqualFilter(
                    query,
                    EstimateEphemeris,
                    'julian_date',
                    self._scenario.clock.julian_date_epoch
                )
                current_ephemerides = shared_interface.getData(query)

                # Grab observation data from db
                query = Query([Observation])
                query = addAlmostEqualFilter(
                    query,
                    Observation,
                    'julian_date',
                    self._scenario.clock.julian_date_epoch
                )
                observation_data = shared_interface.getData(query)
                for estimate in current_ephemerides:
                    leader_id = determineCurrentLeader(estimate.unique_id, estimate.julian_date)
                    if leader_id != estimate.unique_id:
                        # Get datetime format of Julian date
                        date_time = julianDateToDatetime(estimate.julian_date)
                        # Grab leader estimate data from db
                        query = Query([EstimateEphemeris]).filter(
                            EstimateEphemeris.unique_id == leader_id
                        )
                        query = addAlmostEqualFilter(
                            query,
                            EstimateEphemeris,
                            'julian_date',
                            self._scenario.clock.julian_date_epoch
                        )
                        leader_est = shared_interface.getData(query)

                        # Overwrite follower estimate/covariance with that of the leader's
                        estimate = EstimateEphemeris.fromCovarianceMatrix(
                            unique_id=estimate.unique_id,
                            name=estimate.name,
                            julian_date=estimate.julian_date,
                            timestampISO=date_time.isoformat() + '.000Z',
                            source=estimate.source,
                            eci=leader_est.eci,
                            covariance=leader_est.covariance
                        )

                    estimate = mungeLostUCTData(estimate)
                    if estimate is not None:
                        self.handleEstimateOutput(estimate)

                    for observation in observation_data:
                        # There shouldn't need to be any processing regarding merges for
                        # observations since even if there are observations of follower RSOs (and
                        # there shouldn't be), they'll be generated based off of truth, which is
                        # identical for followers/leaders.

                        observation = mungeLostUCTData(observation)
                        if observation is not None:
                            self.handleObservationOutput(observation)

        else:
            self._dropMessage(message)

    def _handleDiscontinueMessage(self, message):
        """Update the service state and optionally destroy the current REsonaate scenario.

        Args:
            message (DiscontinueMessage): Discontinue message.
        """
        if message.destroy_scenario:
            self._scenario = None
            self._updateState(self.State.UNINITIALIZED)

        else:
            self._updateState(self.State.STOPPED)

    def _handleManualSensorTaskMessage(self, message):
        """Insert corresponding :class:`.ManualSensorTask` object into the database.

        Args:
            message (ManualSensorTaskMessage): Manual sensor tasking message.
        """
        self.logger.info("Received sensor tasking: {0}".format(message))
        try:
            db_task = ManualSensorTask(
                unique_id=message.unique_id,
                priority=message.obs_priority,
                start_time=float(message.start_time),
                end_time=float(message.end_time),
                is_dynamic=True
            )
            shared_interface = DataInterface.getSharedInterface()
            shared_interface.insertData(db_task)

        except Exception:  # pylint: disable=broad-except
            self.handleManualSensorTaskResponse(ManualSensorTaskResponse(
                message,
                error_message=format_exc()
            ))

        else:
            self.handleManualSensorTaskResponse(ManualSensorTaskResponse(message))

    def __del__(self):
        """Make sure Redis 'master' variable gets reset and workers are shut down."""
        self.stopMessageHandling(join_queue=False)
        self._worker_manager.stopWorkers(no_wait=True)
        resetMaster()
