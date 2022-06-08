# Standard Library Imports
from copy import deepcopy
from json import loads, dumps
from datetime import datetime
from threading import Thread, Lock
from collections import Counter
from time import sleep
# Third Party Imports
from numpy import asarray
# Package Imports
from .requests import getCovarianceLineChart, getObservationBarChart, getRSODistanceLineChart
from ..physics.constants import DEG2RAD
from ..physics.time.stardate import datetimeToJulianDate
from ..common.logger import Logger
from ..common.behavioral_config import BehavioralConfig


class JSONBaseMessage:
    """Class used to house messages with JSON bases."""

    REQUIRED_FIELDS = tuple()
    """tuple(str): Tuple of fields required in the JSON base message.

    Note:
        This attribute should be overridden by child classes.
    """

    def __init__(self, contents):
        """Construct a :class:`.JSONBaseMessage` object with given parameters.

        Args:
            contents (dict): Dictionary representing decoded JSON message.
        """
        self._contents = contents
        if not isinstance(self._contents, dict):
            err = "Message contents must be a dictionary, not '{0}'".format(type(self._contents))
            raise TypeError(err)

        for field in self.REQUIRED_FIELDS:
            if not self._contents.get(field):
                err = "Message contents missing '{0}' field: {1}".format(
                    field,
                    self._contents
                )
                raise ValueError(err)

    @classmethod
    def fromJSON(cls, json_str):
        """Construct a :class:`.JSONBaseMessage` object from a JSON formatted string.

        Args:
            json_str (str): JSON formatted string containing contents of message.
        """
        return cls(loads(json_str))

    @property
    def contents(self):
        """dict: Dictionary representing decoded analyze RSO JSON message."""
        return deepcopy(self._contents)

    def jsonify(self):
        """Return a JSON string representing this message."""
        return dumps(self._contents)


class CacheableData(JSONBaseMessage):
    """Abstract base class for data :class:`.ResponseService` will be caching."""

    @property
    def julian_date(self):
        """float: Julian date that this data is relevant for."""
        raise NotImplementedError

    @property
    def entity_id(self):
        """int: Unique identifier for entity data is relevant for."""
        raise NotImplementedError


class EstimateMessage(CacheableData):
    """Class to abstract some helpful functionality from an estimate message."""

    REQUIRED_FIELDS = (
        "julian_date", "satNum", "satNum", "position", "velocity",
        "covariance", "source"
    )
    """tuple(str): Required fields in the contents of an estimate message."""

    @property
    def julian_date(self):
        """float: Julian date that this estimate is valid for."""
        return self._contents["julian_date"]

    @property
    def entity_id(self):
        """int: Satellite number of RSO being estimated."""
        return self._contents["satNum"]


class ObservationMessage(CacheableData):
    """Class to abstract some helpful functionality from an observation message.

    Note:
        At the current time, this is more-or-less a copy of the :class:`.EstimateMessage` class,
        but the observation message format on the testbed(s) has changed to be more verbose and
        the ``Observation::makeDictionary()`` method will need to be updated before EE4. These
        changes will result in differences in how properties are retrieved, thus a reason for
        different classes. Additionally, having different classes will help to differentiate
        between data types without adding extra information.
    """

    REQUIRED_FIELDS = (
        "julian_date", "satNum", "observer", "sensorType", "timestampISO",
        "satName", "sensorId", "position"
    )
    """tuple(str): Required fields in the contents of an observation message."""

    @property
    def julian_date(self):
        """float: Julian date that this observation was made."""
        return self._contents["julian_date"]

    @property
    def entity_id(self):
        """int: Satellite number of RSO being observed."""
        return self._contents["satNum"]

    @classmethod
    def fromExternalFormat(cls, external_obs):
        """Create an :class:`.ObservationMessage` object from an external observation dict.

        Args:
            external_obs (dict): incoming observation in form of a `dict`

        Returns:
            :class:`.ObservationMessage`: valid observation message object
        """
        obs = {
            "observer": external_obs["observer_name"],
            "sensorType": external_obs["observer_type"],
            "timestampISO": external_obs["observation_time"],
            "sensorId": external_obs["observer_id"],
            "satNum": external_obs["observed_object_id"],
            "satName": external_obs["observed_object_name"],
            "azimuth": external_obs["los_az_degrees"] * DEG2RAD,
            "elevation": external_obs["los_el_degrees"] * DEG2RAD,
            "range": external_obs["range_km"],
            "rangeRate": external_obs["range_rate_m_per_second"] / 1000,
            "position": [
                external_obs["observer_location_latitude_degrees"] * DEG2RAD,
                external_obs["observer_location_longitude_degrees"] * DEG2RAD,
                external_obs["observer_location_elevation_km"]
            ]
        }
        date_time = datetime.strptime(
            external_obs["observation_time"],
            "%Y-%m-%dT%H:%M:%S.%fZ"
        )
        obs["julian_date"] = datetimeToJulianDate(date_time)
        return cls(obs)


class AnalyzeRSOMessage(JSONBaseMessage):
    """Class to abstract some helpful functionality from a SOLAR analyze RSO message."""

    REQUIRED_FIELDS = ("requestUuid", "primaryId", "scenarioTime", "createdAt")
    """tuple(str): Required fields in the contents of an analyze RSO message."""

    @property
    def request_id(self):
        """str: Unique identifier for this instance of :class:`.AnalyzeRSOMessage` ."""
        return self._contents["requestUuid"]

    @property
    def rso_id(self):
        """int: Satellite number of RSO being analyzed."""
        return int(self._contents["primaryId"])

    @property
    def secondary_rso_ids(self):
        """list(int): Satellite numbers of secondary RSOs being analyzed."""
        if self._contents.get("secondaryIds"):
            return [int(rso) for rso in self._contents["secondaryIds"].split(',')]
        # else
        return []

    @property
    def julian_date(self):
        """float: Julian date that this analyze RSO message is for."""
        date_time = datetime.strptime(
            self._contents["scenarioTime"],
            "%Y-%m-%dT%H:%M:%S.%fZ"
        )
        return datetimeToJulianDate(date_time)

    @property
    def created_at(self):
        """str: ISO date-time of creation for this instance of :class:`.AnalyzeRSOMessage` ."""
        return self._contents["createdAt"]

    @property
    def scenario_time(self):
        """str: ISO date-time of the current scenario for this instance of :class:`.AnalyzeRSOMessage` ."""
        return self._contents["scenarioTime"]


class AnalyzeRSOReply(JSONBaseMessage):
    """Class to abstract some helpful functionality from a SOLAR analyze RSO reply message."""

    REQUIRED_FIELDS = ("version", "replyToUuid", "createdAt",
                       "createdBy", "primaryId", "label", "status", )
    """tuple(str): Required fields in the contents of an analyze RSO reply message."""

    VIZ_FIELDS = ("lineChart", "stackedBarChart", "heatMap", "radarChart", "globe3d", )
    """tuple(str): At least one of these visualization fields should be present."""

    VERSION_DEFAULT = "1.9"
    """str: default value for 'version' attribute."""

    def __init__(self, contents):
        """Create a new :class:`.AnalyzeRSOReply` message and enforce message format rules."""
        if not contents.get("version"):
            contents["version"] = self.VERSION_DEFAULT

        if not contents.get("createdAt"):
            contents["createdAt"] = datetime.utcnow().isoformat() + "+00:00"

        if not contents.get("createdBy"):
            contents["createdBy"] = "resonaate_response"

        has_viz = False
        for field_name in self.VIZ_FIELDS:
            if contents.get(field_name):
                has_viz = True
                break
        if not has_viz:
            err = "Message contents missing visualization field."
            raise ValueError(err)

        super().__init__(contents)


class InsertSortedCacheList:
    """Class used to keep items in a list sorted upon insert."""

    def __init__(self, cache_time=0.5):
        """Construct a :class:`.InsertSortedCacheList` object.

        Args:
            cache_time (float): Number of days-worth of data to store in the cache list.
        """
        self._list = list()
        self._cache_time = cache_time
        if not isinstance(self._cache_time, (float, int)):
            err = "Cache time must be fo type float or int, not '{0}'".format(type(self._cache_time))
            raise TypeError(err)

    def addData(self, new_data):
        """Add new data to the cache list, and remove any 'old' data.

        Args:
            new_data (CacheableData): new data object to be added to the cache list.
        """
        self._list.append(new_data)

        new_index = -1
        if new_index - 1 >= len(self._list) * -1:
            while self._list[new_index - 1].julian_date > self._list[new_index].julian_date:
                self._list[new_index] = self._list[new_index - 1]
                self._list[new_index - 1] = new_data
                new_index -= 1

                if new_index - 1 < len(self._list) * -1:
                    break
        self.trimCache(self._list[-1].julian_date)

    def trimCache(self, julian_date):
        """Remove 'old' data from the cache list.

        Args:
            julian_date (float): Current time to determine freshness of data from.
        """
        slice_point = 0
        age = julian_date - self._list[slice_point].julian_date
        while age > self._cache_time:
            slice_point += 1
            age = julian_date - self._list[slice_point].julian_date

        self._list = self._list[slice_point:]

    def getDataContents(self):
        """Return copies of the contents of each cached :class:`.CacheableData` item."""
        return [ii.contents for ii in self._list]


class StorageCache:
    """Class used to store a cache of time-sorted, entity-segregated data."""

    def __init__(self, cache_time=0.5):
        """Construct a :class:`.StorageCache` object.

        Args:
            cache_time (float): Number of days-worth of data to store for each entity with
                relevant data.
        """
        self.cache_time = cache_time
        if not isinstance(self.cache_time, (float, int)):
            err = "Cache time must be fo type float or int, not '{0}'".format(type(self.cache_time))
            raise TypeError(err)

        self._cache = dict()
        self._cache_lock = Lock()

    def addData(self, new_data):
        """Add new data to the cache.

        Args:
            new_data (CacheableData): new data object to be added to the cache.
        """
        with self._cache_lock:
            _key = new_data.entity_id
            if not self._cache.get(_key):
                self._cache[_key] = InsertSortedCacheList(cache_time=self.cache_time)
            self._cache[_key].addData(new_data)

    def getDataContents(self, entity_id):
        """Return the contents of the cache for a specific ``entity_id`` .

        Args:
            entity_id (int): Unique identifier of desired segregated cache contents.
        """
        contents = []
        with self._cache_lock:
            contents = self._cache.get(entity_id, InsertSortedCacheList(cache_time=self.cache_time)).getDataContents()

        return contents


class ResponseService:
    """Base class implementing a response service using the Resonaate library."""

    LOG_COUNTED_INTERVAL = 10
    """int: Number of seconds between logging all counted messages."""

    def __init__(self, ):
        """Construct a :class:`.ResponseService` object with supporting infrastructure."""
        self.logger = Logger('resonaate', path=BehavioralConfig.getConfig().logging.OutputLocation)
        self._estimate_cache = StorageCache()
        self._observation_cache = StorageCache(cache_time=(2 / 24))

        self._message_counter = Counter()
        self._message_counter_lock = Lock()
        self._counter_logging_thread = Thread(target=self._countMessages, daemon=True)
        self._counter_logging_thread.start()

    def onReceiveEstimate(self, estimate_message):
        """Handle a new estimate message.

        Args:
            estimate_message (EstimateMessage): New estimate message to save.
        """
        if isinstance(estimate_message, EstimateMessage):
            self._estimate_cache.addData(estimate_message)
            self._countMessage(estimate_message)
        else:
            err = "Expected EstimateMessage, not {0}".format(type(estimate_message))
            raise TypeError(err)

    def onReceiveObservation(self, observation_message):
        """Handle a new observation message.

        Args:
            observation_message (ObservationMessage): New observation message to save.
            observation_json (str): JSON-formatted string representing an observation data point.
        """
        if isinstance(observation_message, ObservationMessage):
            self._observation_cache.addData(observation_message)
            self._countMessage(observation_message)
        else:
            err = "Expected ObservationMessage, not {0}".format(type(observation_message))
            raise TypeError(err)

    @staticmethod
    def getObservationResponse(analyze_rso_message, estimate_data, observation_data):
        """Create visibility response to AnalyzeRSO message.

        Args:
            analyze_rso_message (AnalyzeRSOMessage): New analyze RSO message to reply to.
        """
        # Grab timestamps and estimates from cached data
        timestamps = [est['timestampISO'] for est in estimate_data]
        estimates = asarray([est['position'] + est['velocity'] for est in estimate_data]).transpose()
        created_at = analyze_rso_message.created_at

        # Build visibility request object
        obs_chart = getObservationBarChart(
            analyze_rso_message.rso_id,
            timestamps,
            estimates,
            observation_data
        )
        obs_chart["createdAt"] = created_at

        # Add visibility request to the reply
        obs_response = {
            "replyToUuid": analyze_rso_message.request_id,
            "createdAt": created_at,
            "primaryId": str(analyze_rso_message.rso_id),
            "stackedBarChart": obs_chart,
            "status": "Observation count: {0}".format(len(observation_data)),
            "label": "Observations & Covariance"
        }
        return obs_response

    @staticmethod
    def getCovarianceResponse(analyze_rso_message, estimate_data):
        """Create Historic covariance response to analyze RSO message.

        Args:
            analyze_rso_message (AnalyzeRSOMessage): New analyze RSO message to reply to.
        """
        timestamps = [est['timestampISO'] for est in estimate_data]
        covariance = [est['covariance'] for est in estimate_data]
        created_at = analyze_rso_message.created_at

        # Build covariance request object
        covar_chart = getCovarianceLineChart(
            analyze_rso_message.rso_id,
            timestamps,
            covariance,
            (0.674490, 1.15035, 3),
            ("50%", "75%", "99.7%")
        )
        covar_chart["createdAt"] = created_at

        return covar_chart

    def getRSODistanceResponse(self, analyze_rso_message, primary_estimate_data, secondary_estimate_data):
        """Create Historic covariance response to analyze RSO message.

        Args:
            analyze_rso_message (AnalyzeRSOMessage): New analyze RSO message to reply to.
        """
        created_at = analyze_rso_message.created_at

        # Build covariance request object
        dist_chart, minimum_distance = getRSODistanceLineChart(
            analyze_rso_message.rso_id,
            primary_estimate_data,
            secondary_estimate_data
        )
        dist_chart["createdAt"] = created_at

        # Add Historical Covariance request to the reply
        dist_response = {
            "replyToUuid": analyze_rso_message.request_id,
            "createdAt": created_at,
            "primaryId": str(analyze_rso_message.rso_id),
            "secondaryIds": self.listToString(analyze_rso_message.secondary_rso_ids),
            "label": "RSO Distance",
            "status": "Minimum distance: {0:.3} km".format(minimum_distance),
            "lineChart": dist_chart,
        }
        return dist_response

    def onReceiveAnalyzeRSO(self, analyze_rso_message):
        """Handle a new analyze RSO message.

        Args:
            analyze_rso_message (AnalyzeRSOMessage): New analyze RSO message to reply to.
        """
        if not isinstance(analyze_rso_message, AnalyzeRSOMessage):
            err = "Expected AnalyzeRSOMessage, not {0}".format(type(analyze_rso_message))
            raise TypeError(err)
        if analyze_rso_message._contents.get("tools"):  # pylint: disable=protected-access
            return
        rso_id = analyze_rso_message.rso_id
        self.logger.info("Received analyze RSO message for {0}!".format(rso_id))

        # Parse required data
        primary_estimates = self._estimate_cache.getDataContents(rso_id)
        primary_observations = self._observation_cache.getDataContents(rso_id)

        # Log data for debugging
        if primary_estimates:
            self.logger.debug("Primary EstimateAgent message: {0}".format(primary_estimates[0]))
        else:
            # No response if we don't have any estimates
            self.logger.warning("No analyze RSO response for {0}. It is not a tier 1 RSO".format(rso_id))
            return
        if primary_observations:
            self.logger.debug("Observation message: {0}".format(primary_observations[0]))

        # Build response
        obs_response = self.getObservationResponse(analyze_rso_message, primary_estimates, primary_observations)
        obs_response["lineChart"] = self.getCovarianceResponse(analyze_rso_message, primary_estimates)
        # Handle response
        self.handleAnalyzeRSOReply(AnalyzeRSOReply(obs_response))

        # Parse required data
        secondary_estimates = {}
        skipped = []
        for second_rso in analyze_rso_message.secondary_rso_ids:
            est = self._estimate_cache.getDataContents(second_rso)
            if est:
                secondary_estimates[second_rso] = est
            else:
                skipped.append(second_rso)

        if secondary_estimates:
            self.logger.debug("Secondary EstimateAgent messages for: {0}".format(list(secondary_estimates.keys())))
            self.logger.warning("The following secondary ids are not tier 1 RSOs: {0}".format(skipped))
        else:
            # No distance response if the secondary estimates are not valid
            self.logger.warning("No tier 1 RSOs given in `secondaryIds`: {0}".format(list(secondary_estimates.keys())))
            return

        # Build Analyze RSO response/reply messages
        distance_response = self.getRSODistanceResponse(analyze_rso_message, primary_estimates, secondary_estimates)
        # Handle response
        self.handleAnalyzeRSOReply(AnalyzeRSOReply(distance_response))

    def handleAnalyzeRSOReply(self, analyze_rso_reply):
        """Handle the output analyze RSO reply(s).

        Note:
            This method should be overwritten by child classes to handle output in a specific way.
            By default, this method just logs the details of the message processing.

        Args:
            analyze_rso_reply (AnalyzeRSOReply): Analyze RSO reply message to be handled.
        """
        self.logger.info(analyze_rso_reply.jsonify())

    def _countMessage(self, counted_message):
        """Count a message so that it can be logged later.

        Args:
            counted_message (JSONBaseMessage): Message being counted.
        """
        with self._message_counter_lock:
            self._message_counter[type(counted_message)] += 1

    def _countMessages(self):
        """Log all messages that have been dropped on an interval."""
        while 1:
            sleep(self.LOG_COUNTED_INTERVAL)

            with self._message_counter_lock:
                for message_type, count in self._message_counter.items():
                    self.logger.info("Received {0} messages of type {1} in the last {2} seconds.".format(
                        count,
                        message_type,
                        self.LOG_COUNTED_INTERVAL
                    ))
                self._message_counter = Counter()

    @staticmethod
    def listToString(new_list):
        """Convert a list of items to a comma-separated string version."""
        new_str = ""
        if new_list:
            new_str = str(new_list[0])
            for item in new_list[1:]:
                new_str = new_str + "," + str(item)
        return new_str
