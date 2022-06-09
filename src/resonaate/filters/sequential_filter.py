"""Defines the :class:`.SequentialFilter` base class to formalize an interface for sequential filtering algorithms."""
# Standard Library Imports
import logging
from abc import ABCMeta, abstractmethod
# Third Party Imports
# RESONAATE Imports
from ..common.utilities import getTypeString


class SequentialFilter(metaclass=ABCMeta):
    """Defines common interface for a recursive sequential state estimation filter.

    Most methods are abstract, so implementers can define their custom algorithms, but users can
    rely on a common interface. This class relies on interactions with a containing
    :class:`.EstimateAgent`, and references to :class:`.SensingAgent` to properly work.

    Terminology:
        The terminology used here refers to the **a** **priori** state estimate and error
        covariance as :attr:`.pred_x` and :attr:`.pred_p`, respectively, and the **a**
        **posteriori** state estimate and error covariance as :attr:`.est_x` and :attr:`.est_p`,
        respectively. For a more formalized definition of these terms and their rigorous
        derivations, see Bar-Shalom and/or Crassidis.

    Notation:
        - `x` refers to the state estimate vector
        - `p` refers to the error covariance matrix
        - `y` refers to the measurement vector
        - `N` is defined as the number of dimensions of the state estimate, `x`, which is constant
        - `M` is defined as the number of dimensions of the measurement, `y`, which can vary with time.
        - `k` is defined as the current timestep of the simulation
        - `k+1` is defined as the future timestep at which the filter is predicting/estimating

    Attributes:
        dynamics (:class:`.Dynamics`): dynamics model that propagates the estimate forward in time.
        x_dim (int): the dimension size of the state estimate.
        q_matrix (numpy.ndarray): `NxN` process noise covariance matrix. Defines the dynamics
            model uncertainty assumed by the filter.
        pred_x (numpy.ndarray): `Nx1` predicted (**priori**) state estimate at `k+1`.
        pred_p (numpy.ndarray): `NxN` predicted (**priori**) error covariance at `k+1`.
        est_x (numpy.ndarray): `Nx1` estimated (**posteriori**) state estimate at `k+1`.
        est_p (numpy.ndarray): `Nx1` estimated (**posteriori**) error covariance at `k+1`.
        nis (float): normalized innovations squared values. Defines a chi-squared distributed
            sequence with `M` degrees of freedom. This allows for simple checking of filter
            consistency and modeling errors.
        source (str): Variable determining whether observations were used during an update
            step. Acceptable values
            1. ``"Propagation"`` = no observations were used.
            2. ``"Observation"`` = at least one observation was used.
        r_matrix (numpy.ndarray): `MxM` measurement error covariance matrix at `k+1`. Most
            literature assumes that this is defined as constant/unchanging matrix, but this
            work allows it to change with varying numbers of sensors. This allows for disparate
            observations from many different types of sensors to contribute information, which is
            more flexible/realistic. This is done by concatenating individual measurement noise
            matrices of the observing sensors on every timestep, which means the size, `M`, varies
            with time.
        innov_cvr (numpy.ndarray): `MxM` innovation (aka measurement prediction) covariance
            matrix. Defines the "accuracy" of the measurements.
        cross_cvr (numpy.ndarray): `NxM` cross covariance matrix. Defines the covariance
            between the state and measurement.
        kalman_gain (numpy.ndarray): `NxM` Kalman gain matrix. Defines the relative importance
            of the state prediction variance vs. innovation variance.
        mean_pred_y (numpy.ndarray): `Mx1` predicted mean measurement vector. Defines mean
            value of the predicted measurement(s) based on the predicted state estimate.
        innovation (numpy.ndarray): `Mx1` innovation (aka measurement residual) vector. Defines
            the residual error between the true measurement and the mean predicted measurement.
        ang_meas_bool (numpy.ndarray): `Mx1` integer vector describing which measurements are
            angles. This allows proper handling of angle measurements when calculating the
            measurement mean and residuals vectors. The following values are valid:
            - `0` is a non-angular measurement, no special treatment is needed
            - `1` is an angular measurement valid in [-pi, pi]
            - `2` is an angular measurement valid in [0, 2pi]

    References:
        #. :cite:t:`bar-shalom_2001_estimation`
        #. :cite:t:`crassidis_2012_optest`
    """  # noqa: E501

    def __init__(self, dynamics, q_matrix, maneuver_detection_method):
        """Initialize a generic sequential filter class.

        Args:
            dynamics (:class:`.Dynamics`): dynamics object associated with the filter's target
            q_matrix (numpy.ndarray): dynamics error covariance matrix
            maneuver_detection_method (:class:`.Nis`): NIS object associated with the filter
        """
        self._logger = logging.getLogger("resonaate")

        # Define the filter's scope/behavior
        self.dynamics = dynamics
        self._host = None

        # Initialize key variables used in filter process
        self.x_dim = len(q_matrix)
        self.time = None
        self.q_matrix = q_matrix

        # Maneuver Detection products
        self.nis = None
        self.maneuver_gate = None
        self.maneuver_detection_method = maneuver_detection_method
        self.detected_maneuver = None  # maneuvers detected during the current timestep.

        # Main estimation products, used as outputs of the filter class
        self.pred_x = None
        self.pred_p = None
        self.est_x = None
        self.est_p = None
        self.source = None

        # Intermediate values, used for checking statistical consistency & simplifying equations
        self.r_matrix = None
        self.innov_cvr = None
        self.cross_cvr = None
        self.kalman_gain = None
        self.mean_pred_y = None
        self.innovation = None
        self.ang_meas_bool = None

    @abstractmethod
    def predict(self, final_time):
        """Propagate the state estimate and error covariance with uncertainty.

        Args:
            final_time (:class:`.ScenarioTime`): time to propagate to
        """
        raise NotImplementedError

    @abstractmethod
    def predictCovariance(self, final_time):
        """Propagate the previous covariance estimate from `k` to `k+1`.

        Args:
            final_time (:class:`.ScenarioTime`): time to propagate to
        """
        raise NotImplementedError

    @abstractmethod
    def predictStateEstimate(self, final_time):
        """Propagate the previous state estimate from `k` to `k+1`.

        Args:
            final_time (:class:`.ScenarioTime`): time to propagate to
        """
        raise NotImplementedError

    @abstractmethod
    def forecast(self, obs_tuples):
        """Update the error covariance with observations.

        Args:
            obs_tuples (list): :class:`.ObservationTuple` objects associated with the filter step
        """
        raise NotImplementedError

    @abstractmethod
    def update(self, obs_tuples, truth):
        """Update the state estimate with observations.

        Args:
            obs_tuples (list): :class:`.ObservationTuple` objects associated with the filter step
            truth (numpy.ndarray): truth state vector for the target in ECI frame
        """
        raise NotImplementedError

    @abstractmethod
    def updateCovariance(self):
        """Update the covariance estimate at `k+1`."""
        raise NotImplementedError

    @abstractmethod
    def updateStateEstimate(self):
        """Update the state estimate estimate at `k+1`."""
        raise NotImplementedError

    @abstractmethod
    def getPredictionResult(self):
        """Compile result message for a predict step.

        Returns:
            dict: message with predict information
        """
        raise NotImplementedError

    @abstractmethod
    def getForecastResult(self):
        """Compile result message for a forecast step.

        Returns:
            dict: message with forecast information
        """
        raise NotImplementedError

    @abstractmethod
    def getUpdateResult(self):
        """Compile result message for an update step.

        Returns:
            dict: message with update information
        """
        raise NotImplementedError

    def updateFromAsyncResult(self, async_result):
        """Set the corresponding values of this filter based on a filter async job result.

        Args:
            async_result (``dict``): updated attributes of a filter after an async job.
        """
        for key, value in async_result.items():
            setattr(self, key, value)

    def propagate(self, final_time):
        """Enable a filter to propagate the state forward in time like a :class:`.Dynamics` object.

        Args:
            final_time (:class:`.ScenarioTime`): value for the time of the propagated state (sec)
        Returns:
            (numpy.ndarray): Nx1 propagated state vector
            (numpy.ndarray): NxN propagated covariance matrix
        """
        self.predict(final_time)
        return self.pred_x, self.pred_p

    def _initialize(self, initial_time, est_x, est_p):
        """Set the filter's initial time, state estimate, and covariance.

        Args:
            initial_time (:class:`.ScenarioTime`): value for the initial time (sec)
            est_x (numpy.ndarray): Nx1 initial state estimate
            est_p (numpy.ndarray): NxN  initial covariance
        """
        self.time = initial_time
        self.est_x = est_x
        self.est_p = est_p

    @property
    def host(self):
        """:class:.`EstimateAgent`: Returns associated agent that contains this filter.

        This allows the filter to dynamically reference the agent's attributes that could possibly
        be updated over time (e.g. :attr:`~.agent_base.Agent.visual_cross_section`).

        Also, setting the ``host`` attribute initializes the filter's time, state estimate, and
        error covariance.
        """
        return self._host

    @host.setter
    def host(self, new_host):
        """Sets new host object.

        Args:
            new_host: (:class:.`EstimateAgent`): new host for filter.
        """
        if getTypeString(new_host) != "EstimateAgent":
            raise TypeError(f"SeqFilter: Incorrect type for host property: {type(new_host)}")
        self._host = new_host
        self._initialize(new_host.time, new_host.state_estimate, new_host.error_covariance)
