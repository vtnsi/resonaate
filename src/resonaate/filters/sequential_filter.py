# Standard Library Imports
import logging
from abc import ABCMeta, abstractmethod
# Third Party Imports
# RESONAATE Imports
from ..common.utilities import getTypeString


class SequentialFilter(metaclass=ABCMeta):
    """Sequential Filter Abstract Base Class.

    The Sequential Filter Interface provides a standard method for integrating any recursive
    estimation algorithm into a Scenario
    """

    def __init__(self, dynamics, q_matrix):
        """Initialize generic sequential filter class."""
        # Set class variables
        self.dynamics = dynamics
        self.q_matrix = q_matrix
        self.x_dim = len(q_matrix)
        self.logger = logging.getLogger("resonaate")

        # Other possible variables
        self.time = None
        self.final_time = None
        self.pred_x = None
        self.pred_p = None
        self.est_x = None
        self.est_p = None
        self.r_matrix = None
        self.maneuver_gate = None
        self.maneuver_metric = None
        self.surprisal = None
        self._host = None
        self.h_matrix = None
        self.cross_cvr = None
        self.innov_cvr = None
        self.kalman_gain = None
        self.true_y = None
        self.est_y = None
        self.residual = None
        self.ang_meas_bool = None

        self.source = None
        """str: Variable used to determine whether observations were used during an update step.

        Acceptable values: "Propagation" = no observations were used; "Observation": at least one observation was used.
        """

    @abstractmethod
    def predict(self, final_time):
        """Propagate the state and covariance estimates.

        Args:
            final_time (:class:`.ScenarioTime`): time to propagate to
        """
        raise NotImplementedError

    @abstractmethod
    def predictCovariance(self):
        """Propagate the previous covariance estimate from k - 1 to k."""
        raise NotImplementedError

    @abstractmethod
    def predictStateEstimate(self):
        """Propagate the previous state estimate from k - 1 to k."""
        raise NotImplementedError

    @abstractmethod
    def forecast(self, obs):
        """Update the covariance estimate.

        Args:
            obs (list): :class:`.Observation` list associated with this timestep
        """
        raise NotImplementedError

    @abstractmethod
    def update(self, obs, truth):
        """Update the state estimate.

        Args:
            obs (list): :class:`.Observation` list associated with this timestep
            truth (``numpy.ndarray``): truth state vector for the target in ECI frame
        """
        raise NotImplementedError

    @abstractmethod
    def updateCovariance(self):
        """Update the covariance estimate at k. Rewritten for UKF form."""
        raise NotImplementedError

    @abstractmethod
    def updateStateEstimate(self):
        """Update the state estimate estimate at k."""
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

    @abstractmethod
    def updateFromAsyncResult(self, predict_result):
        """Set the corresponding values of this filter based on a filter prediction result.

        Args:
            predict_result (dict): updated attributes of a filter after the prediction step
        """
        raise NotImplementedError

    def propagate(self, final_time):
        """Enable a filter to propagate the Agent's state forward in time like a Dynamics object.

        Args:
            final_time (float): Scalar value for the time of the propagated state (seconds)

        Returns:
            (``numpy.ndarray``):  Nx1 propagated state vector
            (``numpy.ndarray``):  NxN propagated covariance matrix
        """
        self.predict(final_time)
        return self.pred_x, self.pred_p

    def retrogress(self, final_time):
        """Enable a filter to propagate the Agent's state backward in time like a Dynamics object.

        Args:
            final_time (float): Scalar value for the time of the propagated state (seconds)

        Returns:
            (``numpy.ndarray``):  Nx1 propagated state vector
            (``numpy.ndarray``):  NxN propagated covariance matrix
        """
        self.predict(final_time)
        return self.pred_x, self.pred_p

    def initialize(self, initial_time, est_x, est_p):
        """Set the filter's initial time, state estimate, and covariance.

        Args:
            initial_time (float): Scalar value for the initial time (seconds)
            est_x (``numpy.ndarray``): Nx1 initial state estimate
            est_p (``numpy.ndarray``): NxN  initial covariance
        """
        self.time = initial_time
        self.est_x = est_x
        self.est_p = est_p

    @property
    def host(self):
        """Return the :class:.`EstimateAgent` object that contains this class."""
        return self._host

    @host.setter
    def host(self, new_host):
        if getTypeString(new_host) != "EstimateAgent":
            raise TypeError("SeqFilter: Incorrect type for host property: {0}".format(type(new_host)))
        self._host = new_host
