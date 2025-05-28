r"""Defines the Unscented Kalman Filter class."""

from __future__ import annotations

# Standard Library Imports
from typing import TYPE_CHECKING

# Third Party Imports
from numpy import array, concatenate, diagflat, full, ones, sqrt, zeros
from numpy.linalg import LinAlgError, cholesky, inv
from scipy.linalg import block_diag

# RESONAATE Imports
from resonaate.estimation.sequential_filter import EstimateSource

# Local Imports
from ...common.behavioral_config import BehavioralConfig
from ...physics.maths import angularMean, residuals
from ...physics.measurements import VALID_ANGLE_MAP, VALID_ANGULAR_MEASUREMENTS
from ...physics.statistics import chiSquareQuadraticForm
from ...physics.time.stardate import JulianDate, julianDateToDatetime
from ..debug_utils import findNearestPositiveDefiniteMatrix
from ..results import UKFForecastResult, UKFPredictResult, UKFUpdateResult
from ..sequential_filter import FilterFlag, SequentialFilter
from .kalman_filter import KalmanFilter

if TYPE_CHECKING:
    # Standard Library Imports
    from collections.abc import Callable

    # Third Party Imports
    from numpy import ndarray

    # Local Imports
    from ...data.observation import Observation
    from ...dynamics.dynamics_base import Dynamics
    from ...dynamics.integration_events import ScheduledEventType
    from ...physics.measurements import IsAngle
    from ...physics.time.stardate import ScenarioTime
    from ...scenario.config.estimation_config import SequentialFilterConfig
    from ..maneuver_detection import ManeuverDetection


class UnscentedKalmanFilter(KalmanFilter):
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
        num_sigmas (int): number of sigma points to generate: :math:`S=2\times N + 1`.
        gamma (float): sigma point scaling parameter.
        mean_weight (ndarray): :math:`S\times 1` vector for calculating weighted sum in mean equations.
        cvr_weight (ndarray): :math:`S\times 1` vector for calculating weighted sum in covariance
            equations.
        sigma_points (ndarray): :math:`S` sigma point :math:`N\times 1` vectors combined into single matrix.
        sigma_x_res (ndarray): :math:`N\times S` state sigma point residuals.
        sigma_y_res (ndarray): :math:`M\times S` measurement sigma point residuals.

    References:
        #. :cite:t:`bar-shalom_2001_estimation`
        #. :cite:t:`crassidis_2012_optest`
        #. :cite:t:`julier_acc_1995_approach`
        #. :cite:t:`julier_transac_2000_method`
        #. :cite:t:`wan_2001_ukf`
    """

    def __init__(  # noqa: PLR0913
        self,
        tgt_id: int,
        time: ScenarioTime,
        est_x: ndarray,
        est_p: ndarray,
        dynamics: Dynamics,
        q_matrix: ndarray,
        maneuver_detection: ManeuverDetection | None = None,
        initial_orbit_determination: bool = False,
        adaptive_estimation: bool = False,
        resample: bool = False,
        alpha: float = 0.001,
        beta: float = 2.0,
        kappa: float | None = None,
    ):
        r"""Initialize a UKF instance.

        Args:
            tgt_id (int): unique ID of the target associated with this filter object
            time (.ScenarioTime): value for the initial time (sec)
            est_x (ndarray): :math:`N\times 1` initial state estimate
            est_p (ndarray): :math:`N\times N` initial covariance
            dynamics (.Dynamics): dynamics object associated with the filter's target
            q_matrix (ndarray): dynamics error covariance matrix
            maneuver_detection (.ManeuverDetection): ManeuverDetection associated with the filter
            initial_orbit_determination (bool): Indicator that IOD can be flagged by the filter
            adaptive_estimation (bool): Indicator that adaptive estimation can be flagged by the filter
            resample (bool): Indicator sigma points should be resampled at the start of a measurement update step
            alpha (float): sigma point spread. Defaults to 0.001. This should be a
                small positive value: :math:`\alpha <= 1`.
            beta (float): Gaussian pdf parameter. Defaults to 2.0. This parameter
                defines prior knowledge of the distribution, and the default value of 2 is optimal
                for Gaussian distributions.
            kappa (float): scaling parameter. Defaults to :math:`3 - N`. This parameter
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
                "resample": resample,
            },
        )

        # Calculate scaling parameters lambda & gamma.
        if kappa is None:
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

        self._resample = resample
        self.sigma_points = array([])
        self.sigma_x_res = array([])
        self.sigma_y_res = array([])

    @classmethod
    def fromConfig(
        cls,
        config: SequentialFilterConfig,
        tgt_id: int,
        time: ScenarioTime,
        est_x: ndarray,
        est_p: ndarray,
        dynamics: Dynamics,
        q_matrix: ndarray,
        maneuver_detection: ManeuverDetection,
    ) -> SequentialFilter:
        """Build a :class:`.SequentialFilter` object for target state estimation.

        Args:
            config (:class:`.SequentialFilterConfig`): describes the filter to be built
            tgt_id (``int``): unique ID of the associated target agent
            time (:class:`.ScenarioTime`): initial time of scenario
            est_x (``ndarray``): 6x1, initial state estimate
            est_p (``ndarray``): 6x6, initial error covariance matrix
            dynamics (:class:`.Dynamics`): dynamics object to propagate estimate
            q_matrix (``ndarray``): process noise covariance matrix
            maneuver_detection (.ManeuverDetection): ManeuverDetection associated with the filter

        Returns:
            :class:`.SequentialFilter`: constructed filter object
        """
        return cls(
            tgt_id,
            time,
            est_x,
            est_p,
            dynamics,
            q_matrix,
            maneuver_detection=maneuver_detection,
            initial_orbit_determination=config.initial_orbit_determination,
            adaptive_estimation=config.adaptive_estimation,
            resample=config.resample,
            alpha=config.alpha,
            beta=config.beta,
            kappa=config.kappa,
        )

    @property
    def num_sigmas(self):
        r"""``int``: Returns the number of sigma points to use in this UKF."""
        return 2 * self.x_dim + 1

    def _checkSqrtCovariance(
        self,
        cov: ndarray,
        sqrt_func: Callable[[ndarray], ndarray],
    ) -> ndarray:
        try:
            sqrt_cov = sqrt_func(cov)
        except LinAlgError:
            if BehavioralConfig.getConfig().debugging.NearestPD:
                msg = f"`nearestPD()` function was used on RSO {self.target_id}"
                self.logger.warning(msg)
                sqrt_cov = findNearestPositiveDefiniteMatrix(cov)
            else:
                raise

        return sqrt_cov

    def generateSigmaPoints(
        self,
        mean: ndarray,
        cov: ndarray,
        sqrt_func: Callable[[ndarray], ndarray] = cholesky,
    ) -> ndarray:
        r"""Generate sigma points according to the Unscented Transform.

        Args:
            mean (ndarray): :math:`N\times 1` estimate mean to sample around.
            cov (ndarray): :math:`N\times N` covariance used to sample sigma points.
            sqrt_func (callable): matrix square root algorithm to use. Defaults to
                ``numpy.linalg.cholesky``. Defines how matrix square roots are calculated.

        Returns:
            ``ndarray``: :math:`N\times S` sampled sigma points around the given mean and covariance.
        """
        sqrt_cov = self._checkSqrtCovariance(cov, sqrt_func)

        return mean.reshape((self.x_dim, 1)).dot(
            ones((1, self.num_sigmas)),
        ) + self.gamma * concatenate((zeros((self.x_dim, 1)), sqrt_cov, -sqrt_cov), axis=1)

    def predict(
        self,
        final_time: ScenarioTime,
        scheduled_events: list[ScheduledEventType] | None = None,
    ):
        r"""Propagate the state estimate and error covariance with uncertainty.

        Args:
            final_time (.ScenarioTime): time to propagate to
            scheduled_events (list): scheduled events to apply during propagation which
                can either be implemented :class:`.ContinuousStateChangeEvent` or
                :class:`.DiscreteStateChangeEvent` objects.
        """
        # Reset filter flags
        self._flags = FilterFlag.NONE

        # STEP 1: Calculate the predicted state estimate at t(k) (X(k + 1|k))
        self.predictStateEstimate(final_time, scheduled_events=scheduled_events)

        # STEP 2: Calculate the predicted covariance at t(k) (P(k + 1|k))
        self.predictCovariance(final_time)

        # STEP 3: Update the time step
        self.time = final_time

    def forecast(self, observations: list[Observation]):
        r"""Update the error covariance with observations.

        Args:
            observations (list): :class:`.Observation` objects associated with the UKF step
        """
        # Reset filter flags
        self._flags = FilterFlag.NONE

        # STEP 0: Re-sample the sigma points around predicted (sampled) state estimate
        if self._resample:
            self.sigma_points = self.generateSigmaPoints(self.pred_x, self.pred_p)

        # STEP 1: Calculate the Measurement Matrix (H)
        self.calculateMeasurementMatrix(observations)

        # STEP 2: Compile the Observation Noise Covariance (R)
        self.r_matrix = block_diag(*[ob.r_matrix for ob in observations])

        # STEP 3: Calculate the Cross Covariance (C), the Innovations Covariance (S), & the Kalman Gain (K)
        self.innov_cvr = (
            self.sigma_y_res.dot(self.cvr_weight.dot(self.sigma_y_res.T)) + self.r_matrix
        )
        self.cross_cvr = self.sigma_x_res.dot(self.cvr_weight.dot(self.sigma_y_res.T))
        self.kalman_gain = self.cross_cvr.dot(inv(self.innov_cvr))

        # STEP 4: Update the error covariance (P(k + 1|k + 1))
        self.est_p = self.pred_p - self.kalman_gain.dot(self.innov_cvr.dot(self.kalman_gain.T))

    def update(self, observations: list[Observation]):
        r"""Update the state estimate with observations.

        Args:
            observations (list): :class:`.Observation` objects associated with the UKF step
        """
        if not observations:
            self.source = EstimateSource.INTERNAL_PROPAGATION

            # Save the 0th sigma point because it is the non-sampled propagated state. This means that
            #   we don't inject any noise into the state estimate when no measurements occur.
            self.est_x = self.sigma_points[:, 0]

            # If there are no observations, there is no update information and the predicted error
            #   covariance is stored as the updated error covariance
            self.est_p = self.pred_p
        else:
            self.source = EstimateSource.INTERNAL_OBSERVATION

            # Performs covariance portion of the update step
            self.forecast(observations)

            # STEP 1: Compile the true measurement state vector (Yt)
            self.true_y = concatenate([ob.measurement_states for ob in observations], axis=0)

            # STEP 2: Calculate the Innovations vector (nu)
            self.innovation = residuals(self.true_y, self.mean_pred_y, self.is_angular)
            self.nis = chiSquareQuadraticForm(self.innovation, self.innov_cvr)

            # STEP 3: Update the state estimate (X(k + 1|k + 1))
            self.est_x = self.pred_x + self.kalman_gain.dot(self.innovation)

            # STEP 4: Maneuver detection
            self.checkManeuverDetection()

            self._debugChecks(observations)

    def predictStateEstimate(
        self,
        final_time: ScenarioTime,
        scheduled_events: list[ScheduledEventType] | None = None,
    ):
        r"""Propagate the previous state estimate from :math:`k` to :math:`k+1`.

        Args:
            final_time (.ScenarioTime): time to propagate to
            scheduled_events (list): scheduled events to apply during propagation which
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

        self.pred_x = self.sigma_points.dot(self.mean_weight)

    def predictCovariance(self, final_time: ScenarioTime):
        r"""Propagate the previous covariance estimate from :math:`k` to :math:`k+1`.

        Args:
            final_time (.ScenarioTime): time to propagate to
        """
        self.sigma_x_res = self.sigma_points - self.pred_x.reshape((self.x_dim, 1)).dot(
            ones((1, self.num_sigmas)),
        )
        self.pred_p = self.sigma_x_res.dot(self.cvr_weight.dot(self.sigma_x_res.T)) + self.q_matrix

    def _calcMeasurementSigmaPoints(self, observations: list[Observation]) -> ndarray:
        r"""Calculate the measurement sigma points by passing sigma points into the measurement function.

        This properly handles disparate measurement types being combined on a single timestep by stacking
        them together into a single measurement with an uncorrelated measurement noise covariance constructed
        as a block diagonal of the individual measurement noise covariances.

        Args:
            observations (list): :class:`.Observation` objects associated with the UKF step

        Returns:
            ``ndarray``: :math:`M\times S` properly configured measurement sigma point set, where
            :math:`M` is the compiled measurement space, and :math:`S` is the number of sigma points.
        """
        obs_vector_list = []
        for sigma_idx in range(self.num_sigmas):
            obs_states = []
            for observation in observations:
                utc_datetime = julianDateToDatetime(JulianDate(observation.julian_date))
                sigma_measurement = observation.measurement.calculateMeasurement(
                    observation.sensor_eci,
                    self.sigma_points[:, sigma_idx],
                    utc_datetime,
                    noisy=False,
                )
                obs_states.append(list(sigma_measurement.values()))

            # Add stacked observations to the list
            stacked_obs_state = concatenate(obs_states, axis=0)
            stacked_obs_state.shape = (stacked_obs_state.size, 1)
            obs_vector_list.append(stacked_obs_state)

        # Concatenate stacked obs into MxS
        return concatenate(obs_vector_list, axis=1)

    def calculateMeasurementMatrix(self, observations: list[Observation]):
        r"""Calculate the stacked observation/measurement matrix for a set of observations.

        The UKF doesn't use an :math:`H` Matrix. Instead, the differences between the predicted state or
        observations, and the associated sigma values are calculated. These are used to
        determine the cross and innovations covariances.

        Args:
            observations (list): :class:`.Observation` objects associated with the UKF step
        """
        # Create observations for each sigma point
        sigma_obs = self._calcMeasurementSigmaPoints(observations)

        # Convert to 1-D list of IsAngle values for the combined observation state
        angular_measurements = concatenate(
            [ob.measurement.angular_values for ob in observations],
            axis=0,
        )

        # Mx1 array of whether each corresponding measurement was angular or not
        self.is_angular = array(
            [a in VALID_ANGULAR_MEASUREMENTS for a in angular_measurements],
            dtype=bool,
        )

        # Save mean predicted measurement vector
        self.mean_pred_y = self.calcMeasurementMean(sigma_obs, angular_measurements)

        # Determine the difference between the sigma pt observations and the mean observation
        self.sigma_y_res = zeros(sigma_obs.shape)
        for item in range(sigma_obs.shape[1]):
            self.sigma_y_res[:, item] = residuals(
                sigma_obs[:, item],
                self.mean_pred_y,
                self.is_angular,
            )

    def calcMeasurementMean(
        self,
        measurement_sigma_pts: ndarray,
        is_angular: list[IsAngle],
    ) -> ndarray:
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
            measurement_sigma_pts (ndarray): :math:`M\times S` array of predicted measurements, where
                :math:`M` is the compiled measurement space, and :math:`S` is the number of sigma points.
            is_angular (list): :class:`.IsAngle` objects corresponding to type of angular measurement.

        Returns:
            ``ndarray``: :math:`M\times 1` predicted measurement mean
        """
        meas_mean = zeros((measurement_sigma_pts.shape[0],))
        for idx, (meas, angular) in enumerate(zip(measurement_sigma_pts, is_angular)):
            if angular in VALID_ANGULAR_MEASUREMENTS:
                low, high = VALID_ANGLE_MAP[angular]
                mean = angularMean(meas, weights=self.mean_weight, low=low, high=high)
            else:
                mean = meas.dot(self.mean_weight)

            meas_mean[idx] = mean

        return meas_mean

    def getPredictionResult(self) -> UKFPredictResult:
        """Compile result message for a predict step.

        Returns:
            Filter results from the 'predict' step.
        """
        return UKFPredictResult.fromFilter(self)

    def getForecastResult(self) -> UKFForecastResult:
        """Compile result message for a forecast step.

        Returns:
            Filter results from the 'forecast' step.
        """
        return UKFForecastResult.fromFilter(self)

    def getUpdateResult(self) -> UKFUpdateResult:
        """Compile result message for an update step.

        Returns:
            Filter results from the 'update' step.
        """
        return UKFUpdateResult.fromFilter(self)
