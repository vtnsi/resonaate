"""Defines the :class:`.EstimateAgent` class."""
# Standard Library Imports
# Third Party Imports
from numpy import ndarray, copy
from numpy.random import default_rng
# RESONAATE Imports
from .agent_base import Agent, DEFAULT_VIS_X_SECTION
from ..common.exceptions import ShapeError
from ..data.ephemeris import EstimateEphemeris
from ..filters import kalmanFilterFactory
from ..filters.sequential_filter import SequentialFilter
from ..physics.noise import initialEstimateNoise
from ..physics.transforms.methods import eci2ecef, ecef2lla


class EstimateAgent(Agent):
    """Define the behavior of the **estimated** target agents in the simulation."""

    def __init__(self, _id, name, agent_type, clock, initial_state,
                 initial_covariance, _filter, seed=None, station_keeping=None):
        """Construct an EstimateAgent object.

        Args:
            _id (``int``): unique identification number
            name (``str``): unique identification name
            agent_type (``str``): name signifying the type of agent `('Spacecraft', 'GroundFacility', )`
            clock (:class:`.ScenarioClock`): clock instance for retrieving proper times
            initial_state (``numpy.ndarray``): 6x1 ECI initial state vector
            initial_covariance (``numpy.ndarray``): 6x6 initial covariance or uncertainty
            _filter (:class:`.SequentialFilter`): tracks the estimate's state throughout the simulation
            seed (``int``, optional): number to seed random number generator. Defaults to ``None``.
            station_keeping (list, optional): list of :class:`.StationKeeper` objects describing the station
                keeping to be performed

        Raises:
            TypeError: raised on incompatible types for input params
            ShapeError: raised if process noise is not a 6x6 matrix
        """
        super().__init__(
            _id, name, agent_type, initial_state, clock, _filter.dynamics, True, DEFAULT_VIS_X_SECTION,
            station_keeping=station_keeping
        )
        if not isinstance(initial_covariance, ndarray):
            self._logger.error("Incorrect type for initial_covariance param")
            raise TypeError(type(initial_covariance))

        if initial_covariance.shape != (6, 6):
            self._logger.error("Incorrect shape for initial_covariance param")
            raise ShapeError(initial_covariance.shape)

        # Properly initialize the EstimateAgent's covariance types
        self._initial_covariance = copy(initial_covariance)
        self._error_covariance = copy(initial_covariance)

        if not isinstance(seed, int) and seed is not None:
            self._logger.error("Incorrect type for seed param")
            raise TypeError(type(seed))
        # Save the random number generator for generating noise
        self._rng = default_rng(seed)

        # Properly initialize the EstimateAgent's state types
        self._state_estimate = copy(initial_state)
        self._ecef_state = eci2ecef(initial_state)
        self._lla_state = ecef2lla(self._ecef_state)

        # Set the EstimateAgent's filter & set itself to the filter's host
        if isinstance(_filter, SequentialFilter):
            self._filter = _filter
            self._filter.host = self
        else:
            self._logger.error("Invalid input type for _filter param")
            raise TypeError(type(_filter))

        # Attribute to track the most recent _actual_ observation of this object
        self.last_observed_at = self.julian_date_start

        # Apply None value to estimate station_keeping
        assert not self.station_keeping, "Estimates do not perform station keeping maneuvers"

    def updateEstimate(self, obs, truth):
        """Perform update using EstimateAgent's :attr:`nominal_filter`.

        Save the *a posteriori* :attr:`state_estimate` and :attr:`error_covariance`. This occurs
        **during** execution of a job on a :class:`.Worker`. The job result is handled by
        the :class:`.QueueManager` to update the :attr:`nominal_filter`.

        See Also:
            :func:`.asyncExecuteTasking` to see how the result is computed

        Args:
            obs (``list`` (:class:`.Observation`)): observations associated with this timestep
            truth (``numpy.ndarray``): 6x1 ECI state vector for the true target agent
        """
        self.nominal_filter.update(obs, truth)
        self.state_estimate = self.nominal_filter.est_x
        self.error_covariance = self.nominal_filter.est_p

    def updateFromAsyncPredict(self, async_result):
        """Perform predict using EstimateAgent's :attr:`nominal_filter`'s async result.

        Save the *a priori* :attr:`.state_estimate` and :attr:`.error_covariance`. This occurs
        **after** execution of a job on a :class:`.Worker`. The job result is handled by the
        :class:`.QueueManager` to update the :attr:`nominal_filter`.

        See Also:
            :meth:`~.JobHandler.handleProcessedJob` to see how the result is handled

        Args:
            async_result (``dict``): Result from parallel :attr:`nominal_filter` predict.
        """
        self.nominal_filter.updateFromAsyncResult(async_result)
        self.state_estimate = self.nominal_filter.pred_x
        self.error_covariance = self.nominal_filter.pred_p

    def updateFromAsyncUpdateEstimate(self, async_result):
        """Perform update using EstimateAgent's :attr:`nominal_filter`'s async result.

        Save the *a posteriori* :attr:`.state_estimate` and :attr:`.error_covariance`. This occurs
        **after** execution of a job on a :class:`.Worker`. The job result is handled by the
        :class:`.QueueManager` to update the :attr:`nominal_filter`.

        See Also:
            :meth:`~.JobHandler.handleProcessedJob` to see how the result is handled

        Args:
            async_result (``dict``): Result from parallel :attr:`nominal_filter` update.
        """
        self.nominal_filter.updateFromAsyncResult(async_result["filter_update"])
        if async_result["observed"]:
            self.last_observed_at = self.julian_date_epoch
        self.state_estimate = self.nominal_filter.est_x
        self.error_covariance = self.nominal_filter.est_p

    def getCurrentEphemeris(self):
        """Returns the EstimateAgent's current ephemeris information.

        This is used for bulk-updating the output database with state information.

        Returns:
            :class:`.EstimateEphemeris`: valid data object for insertion into output database.
        """
        return EstimateEphemeris.fromCovarianceMatrix(
            agent_id=self.simulation_id,
            julian_date=self.julian_date_epoch,
            source=self.nominal_filter.source,
            eci=self.eci_state.tolist(),
            covariance=self.error_covariance.tolist()
        )

    def importState(self, ephemeris):
        """Set the state of this EstimateAgent based on a given :class:`.Ephemeris` object.

        Warning:
            This method is not implemented because EstimateAgent's cannot load data for propagation.

        Args:
            ephemeris (:class:`.Ephemeris`): data object to update this SensingAgent's state with
        """
        raise NotImplementedError("Cannot load state estimates directly into simulation")

    @classmethod
    def fromConfig(cls, config, events):
        """Factory to initialize :class:`.EstimateAgent` objects based on given configuration.

        Args:
            config (``dict``): formatted configuration parameters
            events (``dict``): corresponding formatted events

        Returns:
            :class:`.EstimateAgent`: properly constructed `EstimateAgent` object
        """
        # Grab multiple objects required for creating estimate agents
        tgt = config["target"]
        clock = config["clock"]
        nominal_filter = kalmanFilterFactory(config["filter"])
        # Create the initial state & covariance
        init_x, init_p = initialEstimateNoise(
            tgt.eci_state, config["position_std"], config["velocity_std"], config["rng"]
        )

        # Create the `EstimateAgent` and initialize its filter object
        est = cls(
            tgt.simulation_id,
            tgt.name,
            tgt.agent_type,
            clock,
            init_x,
            init_p,
            nominal_filter,
            config["seed"]
        )

        # Return properly initialized `EstimateAgent`
        return est

    @property
    def eci_state(self):
        """``numpy.ndarray``: Returns the 6x1 ECI current state estimate."""
        return self._state_estimate

    @property
    def ecef_state(self):
        """``numpy.ndarray``: Returns the 6x1 ECEF current state estimate."""
        return self._ecef_state

    @property
    def lla_state(self):
        """``numpy.ndarray``: Returns the 3x1 current position estimate in lat, lon, & alt."""
        return self._lla_state

    @property
    def process_noise_covariance(self):
        """``numpy.ndarray``: Returns the 6x6 process noise matrix."""
        return self._filter.q_matrix

    @property
    def initial_covariance(self):
        """``numpy.ndarray``: Returns the 6x6 original error covariance matrix."""
        return self._initial_covariance

    @property
    def error_covariance(self):
        """``numpy.ndarray``: Returns the 6x6 current error covariance (uncertainty) matrix."""
        return self._error_covariance

    @error_covariance.setter
    def error_covariance(self, new_covar):
        """Properly set the error covariance matrix.

        Args:
            new_covar (``numpy.ndarray``): updated error covariance matrix.

        Raises:
            TypeError: raised if not given a ``numpy.ndarray``
            ShapeError: raised if the matrix' shape is not ``(6,6)``
        """
        if not isinstance(new_covar, ndarray):
            self._logger.error("Incorrect type for setting error covariance")
            raise TypeError(type(new_covar))
        if new_covar.shape != (6, 6):
            self._logger.error("Incorrect dimensions for setting error covariance")
            raise ShapeError(new_covar.shape)
        self._error_covariance = new_covar

    @property
    def state_estimate(self):
        """``numpy.ndarray``: Returns the 6x1 ECI current state estimate."""
        return self._state_estimate

    @state_estimate.setter
    def state_estimate(self, new_state):
        """Set the EstimateAgent's new 6x1 ECI state vector.

        Args:
            new_state (``numpy.ndarray``): 6x1 ECI state vector
        """
        self._state_estimate = new_state
        self._ecef_state = eci2ecef(new_state)
        self._lla_state = ecef2lla(self._ecef_state)

    @property
    def nominal_filter(self):
        """:class:`.SequentialFilter`: Returns the EstimateAgent's associated filter instance."""
        return self._filter
