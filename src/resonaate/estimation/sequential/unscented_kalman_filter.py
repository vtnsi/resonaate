"""Defines the :class:`.UnscentedKalmanFilter` class."""
from __future__ import annotations

# Standard Library Imports
from typing import TYPE_CHECKING

# Third Party Imports
from numpy import array, concatenate, diagflat, full, ones, sqrt, zeros
from numpy.linalg import LinAlgError, cholesky, inv
from scipy.linalg import block_diag

# Local Imports
from ...common.behavioral_config import BehavioralConfig
from ...physics.maths import angularMean, wrapAngleNegPiPi
from ...physics.measurement_utils import VALID_ANGLE_MAP, VALID_ANGULAR_MEASUREMENTS
from ...physics.statistics import chiSquareQuadraticForm
from ...physics.time.stardate import JulianDate, julianDateToDatetime
from ..debug_utils import findNearestPositiveDefiniteMatrix
from .sequential_filter import FilterFlag, SequentialFilter

if TYPE_CHECKING:
    # Standard Library Imports
    from typing import Any, Callable, Optional

    # Third Party Imports
    from numpy import ndarray

    # Local Imports
    from ...data.observation import Observation
    from ...dynamics.dynamics_base import Dynamics
    from ...dynamics.integration_events import ScheduledEventType
    from ...physics.time.stardate import ScenarioTime
    from ..maneuver_detection import ManeuverDetection


class UnscentedKalmanFilter(SequentialFilter):
    r"""Describes necessary equations for state estimation using the Unscented Transform.

    The UKF class provides the framework and functionality for a basic Unscented Kalman filter,
    which propagates the state estimate, and approximates the covariance by combining
    sigma points. These sigma points are defined by the Unscented Transform which is a minimal
    way to capture the random state's pdf. This basic UKF class assumes additive process and
    measurement noise. See references for non-additive forms.

    The defining equations are modified from their original summation/looping form into
    vector/matrix equations to improve speed as well as similarity with standard Kalman filter
    equation notation which uses linear algebra.

    .. rubric:: Terminology

    The terminology used here refers to the **a** **priori** state estimate and error
    covariance as :attr:`.pred_x` and :attr:`.pred_p`, respectively, and the **a**
    **posteriori** state estimate and error covariance as :attr:`.est_x` and :attr:`.est_p`,
    respectively. For a more formalized definition of these terms and their rigorous
    derivations, see :cite:p:`bar-shalom_2001_estimation` or :cite:p:`crassidis_2012_optest`.

    .. rubric:: Notation

    - :math:`x` refers to the state estimate vector
    - :math:`P` refers to the error covariance matrix
    - :math:`y` refers to the measurement vector
    - :math:`N` is defined as the number of dimensions of the state estimate, :math:`x`, which is constant
    - :math:`M` is defined as the number of dimensions of the measurement, :math:`y`, which can vary with time.
    - :math:`k` is defined as the current timestep of the simulation
    - :math:`k+1` is defined as the future timestep at which the filter is predicting/estimating
    - :math:`S` is defined as the number of sigma points generated.

    See Also:
        :class:`.SequentialFilter` for definition of common class attributes

    Attributes:
        num_sigmas (``int``): number of sigma points to generate: :math:`S=2\times N + 1`.
        gamma (``float``): sigma point scaling parameter.
        mean_weight (``ndarray``): :math:`S\times 1` vector for calculating weighted sum in mean equations.
        cvr_weight (``ndarray``): :math:`S\times 1` vector for calculating weighted sum in covariance
            equations.
        sigma_points (``ndarray``): :math:`S` sigma point :math:`N\times 1` vectors combined into single matrix.
        sigma_x_res (``ndarray``): :math:`N\times S` state sigma point residuals.
        sigma_y_res (``ndarray``): :math:`M\times S` measurement sigma point residuals.

    References:
        #. :cite:t:`bar-shalom_2001_estimation`
        #. :cite:t:`crassidis_2012_optest`
        #. :cite:t:`julier_acc_1995_approach`
        #. :cite:t:`julier_transac_2000_method`
        #. :cite:t:`wan_2001_ukf`
    """

    LABELS = ("ukf", "unscented_kalman_filter")

    def __init__(
        self,
        tgt_id: int,
        time: ScenarioTime,
        est_x: ndarray,
        est_p: ndarray,
        dynamics: Dynamics,
        q_matrix: ndarray,
        maneuver_detection: Optional[ManeuverDetection],
        initial_orbit_determination: bool = False,
        adaptive_estimation: bool = False,
        alpha: float = 0.001,
        beta: float = 2.0,
        kappa: Optional[float] = None,
    ):
        r"""Initialize a UKF instance.

        Args:
            tgt_id (``int``): unique ID of the target associated with this filter object
            time (:class:`.ScenarioTime`): value for the initial time (sec)
            est_x (``ndarray``): :math:`N\times 1` initial state estimate
            est_p (``ndarray``): :math:`N\times N` initial covariance
            dynamics (:class:`.Dynamics`): dynamics object associated with the filter's target
            q_matrix (``ndarray``): dynamics error covariance matrix
            maneuver_detection (:class:`.ManeuverDetection`): ManeuverDetection associated with the filter
            initial_orbit_determination (``bool``, optional): Indicator that IOD can be flagged by the filter
            adaptive_estimation (``bool``, optional): Indicator that adaptive estimation can be flagged by the filter
            alpha (``float``, optional): sigma point spread. Defaults to 0.001. This should be a
                small positive value: :math:`\alpha <= 1`.
            beta (``float``, optional): Gaussian pdf parameter. Defaults to 2.0. This parameter
                defines prior knowledge of the distribution, and the default value of 2 is optimal
                for Gaussian distributions.
            kappa (``float``, optional): scaling parameter. Defaults to :math:`3 - N`. This parameter
                defines knowledge of the higher order moments. The equation used by default
                minimizes the mean squared error to the fourth degree. However, when this value
                is negative, the predicted error covariance can become positive semi-definite.
        """
        super().__init__(
            tgt_id,
            time,
            est_x,
            est_p,
            dynamics,
            q_matrix,
            maneuver_detection,
            initial_orbit_determination,
            adaptive_estimation,
            extra_parameters={
                "alpha": alpha,
                "beta": beta,
                "kappa": kappa,
            },
        )

        # Calculate scaling parameters lambda & gamma.
        if not kappa:
            kappa = 3 - self.x_dim
        lambda_kf = (alpha**2) * (self.x_dim + kappa) - self.x_dim

        self.gamma = sqrt(self.x_dim + lambda_kf)

        # Calculate weight values
        first_weight = lambda_kf / (self.x_dim + lambda_kf)
        weight = 1 / (2.0 * (lambda_kf + self.x_dim))

        # Weights for the mean
        self.mean_weight = full(self.num_sigmas, weight)
        self.mean_weight[0] = first_weight
        # Weights for the covariance
        self.cvr_weight = diagflat(self.mean_weight)
        self.cvr_weight[0, 0] += 1 - alpha**2.0 + beta

        self.sigma_points = array([])
        self.sigma_x_res = array([])
        self.sigma_y_res = array([])

    @property
    def num_sigmas(self):
        """``int``: Returns the number of sigma points to use in this UKF."""
        return 2 * self.x_dim + 1

    def generateSigmaPoints(
        self, mean: ndarray, cov: ndarray, sqrt_func: Callable[[ndarray], ndarray] = cholesky
    ) -> ndarray:
        r"""Generate sigma points according to the Unscented Transform.

        Args:
            mean (``ndarray``): :math:`N\times 1` estimate mean to sample around.
            cov (``ndarray``): :math:`N\times N` covariance used to sample sigma points.
            sqrt_func (``callable``, optional): matrix square root algorithm to use. Defaults to
                ``numpy.linalg.cholesky``. Defines how matrix square roots are calculated.

        Returns:
            ``ndarray``: :math:`N\times S` sampled sigma points around the given mean and covariance.
        """
        # Find the square root of the error covariance
        try:
            sqrt_cov = sqrt_func(cov)
        except LinAlgError:
            if BehavioralConfig.getConfig().debugging.NearestPD:
                msg = f"`nearestPD()` function was used on RSO {self.target_id}"
                self._logger.warning(msg)
                sqrt_cov = findNearestPositiveDefiniteMatrix(cov)
            else:
                raise

        # Calculate the sigma points based on the current state estimate
        return mean.reshape((self.x_dim, 1)).dot(
            ones((1, self.num_sigmas))
        ) + self.gamma * concatenate((zeros((self.x_dim, 1)), sqrt_cov, -sqrt_cov), axis=1)

    def predict(
        self,
        final_time: ScenarioTime,
        scheduled_events: Optional[list[ScheduledEventType]] = None,
    ):
        """Propagate the state estimate and error covariance with uncertainty.

        Args:
            final_time (:class:`.ScenarioTime`): time to propagate to
            scheduled_events (``list``, optional): scheduled events to apply during propagation which
                can either be implemented :class:`.ContinuousStateChangeEvent` or
                :class:`.DiscreteStateChangeEvent` objects.
        """
        self._flags = FilterFlag.NONE
        # STEP 1: Calculate the predicted state estimate at t(k) (X(k + 1|k))
        self.predictStateEstimate(final_time, scheduled_events=scheduled_events)
        # STEP 2: Calculate the predicted covariance at t(k) (P(k + 1|k))
        self.predictCovariance(final_time)
        # STEP 3: Update the time step
        self.time = final_time

    def forecast(self, observations: list[Observation]):
        """Update the error covariance with observations.

        Args:
            observations (``list``): :class:`.Observation` objects associated with the UKF step
        """
        self._flags = FilterFlag.NONE
        # STEP 1: Re-sample the sigma points around predicted (sampled) state estimate
        self.sigma_points = self.generateSigmaPoints(self.pred_x, self.pred_p)
        # STEP 2: Calculate the Measurement Matrix (H)
        self.calculateMeasurementMatrix(observations)
        # STEP 3: Compile the Observation Noise Covariance (R)
        # STEP 4: Calculate the Cross Covariance (C), the Innovations Covariance (S), & the Kalman Gain (K)
        self.calculateKalmanGain(observations)
        # STEP 5: Update the Covariance for the state (P(k + 1|k + 1))
        self.updateCovariance()

    def update(self, observations: list[Observation]):
        """Update the state estimate with observations.

        Args:
            observations (``list``): :class:`.Observation` objects associated with the UKF step
        """
        if not observations:
            self.source = self.INTERNAL_PROPAGATION_LABEL
            # Save the 0th sigma point because it is the non-sampled propagated state. This means that
            #   we don't inject any noise into the state estimate when no measurements occur.
            self.est_x = self.sigma_points[:, 0]
            # If there are no observations, there is no update information and the predicted error
            #   covariance is stored as the updated error covariance
            self.est_p = self.pred_p
        else:
            self.source = self.INTERNAL_OBSERVATION_LABEL

            # If there are observations, the predicted state estimate and covariance are updated
            self.forecast(observations)
            # STEP 1: Compile the true measurement state vector (Yt)
            # STEP 2: Calculate the Innovations vector (nu)
            self.calculateInnovations(observations)
            # STEP 3: Update the State EstimateAgent (X(k + 1|k + 1))
            self.updateStateEstimate()
            # STEP 4: Maneuver detection
            self.checkManeuverDetection()

            # Check and write debugging info if needed
            self._debugChecks(observations)

    def predictStateEstimate(
        self,
        final_time: ScenarioTime,
        scheduled_events: Optional[list[ScheduledEventType]] = None,
    ):
        """Propagate the previous state estimate from :math:`k` to :math:`k+1`.

        Args:
            final_time (:class:`.ScenarioTime`): time to propagate to
            scheduled_events (``list``, optional): scheduled events to apply during propagation which
                can either be implemented :class:`.ContinuousStateChangeEvent` or
                :class:`.DiscreteStateChangeEvent` objects.
        """
        # Sample sigma points and propagate through dynamics
        sigma_points_k = self.generateSigmaPoints(self.est_x, self.est_p)
        self.sigma_points = self.dynamics.propagate(
            self.time,
            final_time,
            sigma_points_k,
            scheduled_events=scheduled_events,
        )

        # Calculate the predicted state estimate by combining the sigma points
        self.pred_x = self.sigma_points.dot(self.mean_weight)

    def predictCovariance(self, final_time: ScenarioTime):
        """Propagate the previous covariance estimate from :math:`k` to :math:`k+1`.

        Args:
            final_time (:class:`.ScenarioTime`): time to propagate to
        """
        # pylint: disable=unused-argument
        # Calculate the predicted covariance estimate using the sigma points
        self.sigma_x_res = self.sigma_points - self.pred_x.reshape((self.x_dim, 1)).dot(
            ones((1, self.num_sigmas))
        )
        self.pred_p = self.sigma_x_res.dot(self.cvr_weight.dot(self.sigma_x_res.T)) + self.q_matrix

    def calculateMeasurementMatrix(self, observations: list[Observation]):
        """Calculate the stacked observation/measurement matrix for a set of observations.

        The UKF doesn't use an :math:`H` Matrix. Instead, the differences between the predicted state or
        observations, and the associated sigma values are calculated. These are used to
        determine the cross and innovations covariances.

        Args:
            observations (``list``): :class:`.Observation` objects associated with the UKF step
        """
        obs_vector_list = []
        for sigma_idx in range(self.num_sigmas):
            obs_states = []
            is_angular = []
            for observation in observations:
                utc_datetime = julianDateToDatetime(JulianDate(observation.julian_date))
                sigma_measurement = observation.measurement.calculateMeasurement(
                    observation.sensor_eci,
                    self.sigma_points[:, sigma_idx],
                    utc_datetime,
                    noisy=False,
                )
                obs_states.append(list(sigma_measurement.values()))
                is_angular.append(observation.measurement.angular_values)

            # Add stacked observations to the list
            stacked_obs_state = concatenate(obs_states, axis=0)
            stacked_obs_state.shape = (stacked_obs_state.size, 1)
            obs_vector_list.append(stacked_obs_state)

        # Concatenate stacked obs into MxS
        sigma_obs = concatenate(obs_vector_list, axis=1)

        # Mx1 array of whether each corresponding measurement was angular or not
        self.is_angular = concatenate(is_angular, axis=0)

        # Save mean predicted measurement vector
        self.mean_pred_y = self.calcMeasurementMean(sigma_obs)

        # Determine the difference between the sigma pt observations and the mean observation
        self.sigma_y_res = zeros(sigma_obs.shape)
        for item in range(sigma_obs.shape[1]):
            self.sigma_y_res[:, item] = self.calcMeasurementResiduals(
                sigma_obs[:, item], self.mean_pred_y
            )

    def calculateKalmanGain(self, observations: list[Observation]):
        """Calculate the Kalman gain matrix.

        Compiles the stacked measurement noise covariance matrix, calculates the innovations
        covariance matrix, and calculates the cross covariance matrix.

        Args:
            observations (``list``): :class:`.Observation` objects associated with the UKF step
        """
        self.r_matrix = block_diag(*[ob.r_matrix for ob in observations])
        self.innov_cvr = (
            self.sigma_y_res.dot(self.cvr_weight.dot(self.sigma_y_res.T)) + self.r_matrix
        )
        self.cross_cvr = self.sigma_x_res.dot(self.cvr_weight.dot(self.sigma_y_res.T))
        self.kalman_gain = self.cross_cvr.dot(inv(self.innov_cvr))

    def calculateInnovations(self, observations: list[Observation]):
        """Calculate the innovations (residuals) vector and normalized innovations squared.

        Args:
            observations (``list``): :class:`.Observation` objects associated with the UKF step
        """
        self.true_y = concatenate([ob.measurement_states for ob in observations], axis=0)
        self.innovation = self.calcMeasurementResiduals(self.true_y, self.mean_pred_y)
        self.nis = chiSquareQuadraticForm(self.innovation, self.innov_cvr)

    def calcMeasurementResiduals(
        self, measurement_set_a: ndarray, measurement_set_b: ndarray
    ) -> ndarray:
        r"""Determine the measurement residuals.

        This is done generically which allows for measurements to be ordered in any fashion, but
        requires an associated boolean vector to flag for angle measurements. This special
        treatment is required because angles are nonlinear (modular), so subtraction is not a
        linear operation.

        Args:
            measurement_set_a (``ndarray``): :math:`M\times 1` compiled measurement array.
            measurement_set_b (``ndarray``): :math:`M\times 1` compiled measurement array.

        Returns:
            ``ndarray``: :math:`M\times 1` measurement residual
        """
        # If we have an angular measurement, normalize the angles
        # Works for all angular values, because [-pi/2, pi/2] domains will never have diff > pi
        residual = [
            wrapAngleNegPiPi(err) if ang in VALID_ANGULAR_MEASUREMENTS else err
            for err, ang in zip(measurement_set_a - measurement_set_b, self.is_angular)
        ]

        return array(residual)

    def updateCovariance(self):
        """Update the covariance estimate at :math:`k+1`."""
        self.est_p = self.pred_p - self.kalman_gain.dot(self.innov_cvr.dot(self.kalman_gain.T))

    def updateStateEstimate(self):
        """Update the state estimate estimate at :math:`k+1`."""
        self.est_x = self.pred_x + self.kalman_gain.dot(self.innovation)

    def calcMeasurementMean(self, measurement_sigma_pts: ndarray) -> ndarray:
        r"""Determine the mean of the predicted measurements.

        This is done generically which allows for measurements to be ordered in any fashion, but
        requires an associated boolean vector to flag for angle measurements. This special
        treatment is required because angles are nonlinear (modular), so calculating the mean is
        not a linear operation.

        Angular mean:

        .. math::

            \bar{\theta} = \arctan \left( \frac{\sum^{N}_{i=1}\sin{\theta_{i}}}{\sum^{N}_{i=1}\cos{\theta_{i}}} \right)

        Normal mean:

        .. math::

            \bar{x} = \frac{1}{N}\sum^{N}_{i=1}{x_i}

        Args:
            measurement_sigma_pts (``ndarray``): :math:`M\times S` array of predicted measurements, where
                :math:`M` is the compiled measurement space, and :math:`S` is the number of sigma points.

        Returns:
            ``ndarray``: :math:`M\times 1` predicted measurement mean
        """
        # If we have an angle measurement, calculate mean differently
        meas_mean = zeros((measurement_sigma_pts.shape[0],))
        for idx, (meas, angular) in enumerate(zip(measurement_sigma_pts, self.is_angular)):
            if angular in VALID_ANGULAR_MEASUREMENTS:
                low, high = VALID_ANGLE_MAP[angular]
                mean = angularMean(
                    meas,
                    weights=self.mean_weight,
                    low=low,
                    high=high,
                )
            else:
                mean = meas.dot(self.mean_weight)

            meas_mean[idx] = mean

        return meas_mean

    def getPredictionResult(self) -> dict[str, Any]:
        """Compile result message for a predict step.

        Returns:
            ``dict``: message with predict information
        """
        result = super().getPredictionResult()
        result.update(
            {
                "sigma_points": self.sigma_points,
                "sigma_x_res": self.sigma_x_res,
            }
        )
        return result

    def getForecastResult(self) -> dict[str, Any]:
        """Compile result message for a forecast step.

        Returns:
            ``dict``: message with forecast information
        """
        result = super().getForecastResult()
        result.update(
            {
                "sigma_points": self.sigma_points,
                "sigma_y_res": self.sigma_y_res,
            }
        )
        return result
