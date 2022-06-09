"""Defines the :class:`.UnscentedKalmanFilter` class."""
# Standard Library Imports
# Third Party Imports
from numpy import (
    ones, diagflat, zeros, sqrt, full, concatenate, array, sum as np_sum
)
from numpy.linalg import cholesky, LinAlgError, inv
from scipy.linalg import block_diag, norm
from scipy.stats import chi2
# RESONAATE Imports
from .filter_debug_utils import innovationsCovarianceInflation, findNearestPositiveDefiniteMatrix, logFilterStep
from .sequential_filter import SequentialFilter
from ..data.maneuver_detection import ManeuverDetection
from ..physics.math import wrapAngleNegPiPi, wrapAngle2Pi, angularMean
from ..common.behavioral_config import BehavioralConfig
from ..sensors.measurements import IsAngle


VALID_ANGLES = {IsAngle.ANGLE_PI, IsAngle.ANGLE_2PI}


class UnscentedKalmanFilter(SequentialFilter):
    """Describes necessary equations for state estimation using the Unscented Transform.

    The UKF class provides the framework and functionality for a basic Unscented Kalman filter,
    which propagates the state estimate, and approximates the covariance by combining
    sigma points. These sigma points are defined by the Unscented Transform which is a minimal
    way to capture the random state's pdf. This basic UKF class assumes additive process and
    measurement noise. See references for non-additive forms.

    The defining equations are modified from their original summation/looping form into
    vector/matrix equations to improve speed as well as similarity with standard Kalman filter
    equation notation which uses linear algebra.

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
        - `S` is defined as the number of sigma points generated.

    See Also:
        :class:`.SequentialFilter` for defintion of common class attributes

    Attributes:
        num_sigmas (int): number of sigma points to generate: `S=2*N + 1`.
        gamma (float): sigma point scaling parameter.
        mean_weight (numpy.ndarray): `Sx1` vector for calculating weighted sum in mean equations.
        cvr_weight (numpy.ndarray): `Sx1` vector for calculating weighted sum in covariance
            equations.
        tuning_parameters (dict): tuning parameters used to instantiate UKF, for debugging.
        sigma_points (numpy.ndarray): `S` sigma point `Nx1` vectors combined into single matrix.
        sigma_x_res (numpy.ndarray): `NxS` state sigma point residuals.
        sigma_y_res (numpy.ndarray): `MxS` measurement sigma point residuals.

    References:
        #. :cite:t:`bar-shalom_2001_estimation`
        #. :cite:t:`crassidis_2012_optest`
        #. :cite:t:`julier_acc_1995_approach`
        #. :cite:t:`julier_transac_2000_method`
        #. :cite:t:`wan_2001_ukf`
    """  # noqa: E501

    def __init__(self, dynamics, q_matrix, maneuver_detection_method, alpha=0.001, beta=2.0, kappa=None):
        """Initialize a UKF instance.

        Args:
            dynamics (:class:`.Dynamics`): dynamics object associated with the filter's target
            q_matrix (numpy.ndarray): dynamics error covariance matrix
            maneuver_detection_method (:class:`.Nis`): NIS object associated with the filter
            alpha (float, optional): sigma point spread. Defaults to 0.001. This parameter
                should be a small positive value <= 1.
            beta (float, optional): Gaussian pdf parameter. Defaults to 2.0. This parameter
                defines prior knowledge of the distribution, and the default value of 2 is optimal
                for Gaussian distributions.
            kappa (float, optional): scaling parameter. Defaults to `3 - N`. This parameter
                defines knowledge of the higher order moments. The equation used by default
                minimizes the mean squared error to the fourth degree. However, when this value
                is negative, the predicted error covariance can become positive semi-definite.
        """
        super().__init__(dynamics, q_matrix, maneuver_detection_method)

        # Calculate scaling parameters lambda & gamma.
        if not kappa:
            kappa = 3 - self.x_dim
        lambda_kf = (alpha**2) * (self.x_dim + kappa) - self.x_dim

        self.num_sigmas = 2 * self.x_dim + 1
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

        # Save tuning params as class variables
        self.tuning_parameters = {
            "alpha": alpha,
            "beta": beta,
            "lambda": lambda_kf,
            "kappa": kappa,
        }
        self.sigma_points = None
        self.sigma_x_res = None
        self.sigma_y_res = None

    def generateSigmaPoints(self, mean, cov, sqrt_func=cholesky):
        """Generate sigma points according to the Unscented Transform.

        Args:
            mean (numpy.ndarray): `Nx1` estimate mean to sample around.
            cov (numpy.ndarray): `NxN` covariance used to sample sigma points.
            sqrt_func (callable, optional): matrix square root algorithm to use. Defaults to
                ``numpy.linalg.cholesky``. Defines how matrix square roots are calculated.

        Returns:
            numpy.ndarray: `NxS` sampled sigma points around the given mean and covariance.
        """
        # Find the square root of the error covariance
        try:
            sqrt_cov = sqrt_func(cov)
        except LinAlgError:
            if BehavioralConfig.getConfig().debugging.NearestPD:
                sqrt_cov, file_name = findNearestPositiveDefiniteMatrix(cov)
                msg = f"`nearestPD()` function was used:\n\t{file_name}"
                self._logger.warning(msg)
            else:
                raise

        # Calculate the sigma points based on the current state estimate
        return mean.reshape((self.x_dim, 1)).dot(ones((1, self.num_sigmas))) \
            + self.gamma * concatenate((zeros((self.x_dim, 1)), sqrt_cov, -sqrt_cov), axis=1)

    def predict(self, final_time):
        """Propagate the state estimate and error covariance with uncertainty.

        Args:
            final_time (:class:`.ScenarioTime`): time to propagate to
        """
        # STEP 1: Calculate the predicted state estimate at t(k) (X(k + 1|k))
        self.predictStateEstimate(final_time)
        # STEP 2: Calculate the predicted covariance at t(k) (P(k + 1|k))
        self.predictCovariance(final_time)
        # STEP 3: Update the time step
        self.time = final_time

    def forecast(self, obs_tuples):
        """Update the error covariance with observations.

        Args:
            obs_tuples (list): :class:`.ObservationTuple` objects associated with the UKF step
        """
        # STEP 1: Re-sample the sigma points around predicted (sampled) state estimate
        self.sigma_points = self.generateSigmaPoints(self.pred_x, self.pred_p)
        # STEP 2: Calculate the Measurement Matrix (H)
        self.calculateMeasurementMatrix(obs_tuples)
        # STEP 3: Compile the Observation Noise Covariance (R)
        # STEP 4: Calculate the Cross Covariance (C), the Innovations Covariance (S), & the Kalman Gain (K)
        self.calculateKalmanGain(obs_tuples)
        # STEP 5: Update the Covariance for the state (P(k + 1|k + 1))
        self.updateCovariance()

    def update(self, obs_tuples, truth):
        """Update the state estimate with observations.

        Args:
            obs_tuples (list): :class:`.ObservationTuple` objects associated with the UKF step
            truth (numpy.ndarray): truth state vector for the target in ECI frame
        """
        if not obs_tuples:
            self.source = "Propagation"
            # Save the 0th sigma point because it is the non-sampled propagated state. This means that
            #   we don't inject any noise into the state estimate when no measurements occur.
            self.est_x = self.sigma_points[:, 0]
            # If there are no observations, there is no update information and the predicted error
            #   covariance is stored as the updated error covariance
            self.est_p = self.pred_p
        else:
            self.source = "Observation"
            if BehavioralConfig.getConfig().debugging.EstimateErrorInflation:
                ## Grab debugging information before any steps take place
                description = {
                    "covar_before": self.est_p.tolist(),
                    "estimate_before": self.est_x.tolist(),
                    "sigma_x_res": self.sigma_x_res.tolist()
                }

            # If there are observations, the predicted state estimate and covariance are updated
            self.forecast(obs_tuples)
            # STEP 1:  Compile the true measurement state vector (Yt)
            # STEP 2:  Calculate the Innovations vector (nu)
            self.calculateInnovations(obs_tuples)
            # STEP 3:  Update the State EstimateAgent (X(k + 1|k + 1))
            self.updateStateEstimate()
            # STEP 4:  Maneuver detection
            if self.maneuver_detection_method and self.nis > self.maneuver_gate:
                sat_num = self.host.simulation_id
                sensor_num = obs_tuples[0].agent.simulation_id
                time = self.host.julian_date_epoch
                msg = f"Maneuver Detected for RSO {sat_num} by Sensor {sensor_num} at time {time}"
                self.detected_maneuver = ManeuverDetection.recordManeuverDetection(
                    julian_date=self.host.julian_date_epoch,
                    sensor_id=sensor_num,
                    target_id=sat_num,
                    nis=self.nis,
                    maneuver_gate=self.maneuver_gate
                )  # tuple
                self._logger.info(msg)

            # Check error inflation, and write debuggin info if needed
            if BehavioralConfig.getConfig().debugging.EstimateErrorInflation:
                tol_km = 5  # Estimate inflation error tolerance (km)
                pred_error = abs(norm(truth[:3] - self.pred_x[:3]))
                est_error = abs(norm(truth[:3] - self.est_x[:3]))

                # If error increase is larger than desired log the debug information
                if est_error > pred_error + tol_km:
                    file_name = logFilterStep(self, description, obs_tuples, truth)
                    msg = f"EstimateAgent error inflation occurred:\n\t{file_name}"
                    self._logger.warning(msg)

    def predictStateEstimate(self, final_time):
        """Propagate the previous state estimate from `k` to `k+1`.

        Args:
            final_time (:class:`.ScenarioTime`): time to propagate to
        """
        # Sample sigma points and propagate through dynamics
        sigma_points_k = self.generateSigmaPoints(self.est_x, self.est_p)
        self.sigma_points = self.dynamics.propagate(
            self.time,
            final_time,
            sigma_points_k
        )

        # Calculate the predicted state estimate by combining the sigma points
        self.pred_x = self.sigma_points.dot(self.mean_weight)

    def predictCovariance(self, final_time):
        """Propagate the previous covariance estimate from `k` to `k+1`.

        Args:
            final_time (:class:`.ScenarioTime`): time to propagate to
        """
        # Calculate the predicted covariance estimate using the sigma points
        self.sigma_x_res = self.sigma_points \
            - self.pred_x.reshape((self.x_dim, 1)).dot(ones((1, self.num_sigmas)))
        self.pred_p = self.sigma_x_res.dot(self.cvr_weight.dot(self.sigma_x_res.T)) + self.q_matrix

    def calculateMeasurementMatrix(self, obs_tuples):
        """Calculate the stacked observation/measurement matrix for a set of observations.

        The UKF doesn't use an H Matrix. Instead, the differences between the predicted state or
        observations, and the associated sigma values are calculated. These are used to
        determine the cross and innovations covariances.

        Args:
            obs_tuples (list): :class:`.ObservationTuple` objects associated with the UKF step
        """
        obs_vector_list = []
        for sigma_idx in range(self.num_sigmas):
            obs_states = []
            angular_measurement_bool = []
            for obs_tuple in obs_tuples:
                sensor = obs_tuple.agent.sensors
                observation_tuple = sensor.makeObservation(
                    self.host.simulation_id,
                    self.sigma_points[:, sigma_idx],
                    self.host.visual_cross_section,
                    noisy=False,  # Don't add noise in sigma point measurements
                    check_viz=False  # Don't need to check visibility for sigma points
                )
                obs_states.append(observation_tuple.observation.measurements)
                angular_measurement_bool.append(observation_tuple.angles)

            # Add stacked observations to the list
            stacked_obs_state = concatenate(obs_states, axis=0)
            stacked_obs_state.shape = (stacked_obs_state.size, 1)
            obs_vector_list.append(stacked_obs_state)

        # Concatenate stacked obs into MxS
        sigma_obs = concatenate(obs_vector_list, axis=1)

        # Mx1 boolean array of whether each corresponding measurement was angular or not
        self.ang_meas_bool = concatenate(angular_measurement_bool, axis=0)

        # Save mean predicted measurement vector
        self.mean_pred_y = self.calcMeasurementMean(sigma_obs)

        # Determine the difference between the sigma pt observations and the mean observation
        self.sigma_y_res = zeros(sigma_obs.shape)
        for item in range(sigma_obs.shape[1]):
            self.sigma_y_res[:, item] = self.calcMeasurementResiduals(sigma_obs[:, item], self.mean_pred_y)

    def calculateKalmanGain(self, obs_tuples):
        """Calculate the Kalman gain matrix.

        Compiles the stacked measurement noise covariance matrix, calculates the innovations
        covariance matrix, and calculates the cross covariance matrix.

        Args:
            obs_tuples (list): :class:`.ObservationTuple` objects associated with the UKF step
        """
        self.r_matrix = block_diag(*[obs_tuple.agent.sensors.r_matrix for obs_tuple in obs_tuples])
        self.innov_cvr = self.sigma_y_res.dot(self.cvr_weight.dot(self.sigma_y_res.T)) + self.r_matrix
        if BehavioralConfig.getConfig().debugging.SingularMatrix:
            self.checkInnovationsCovariance(obs_tuples)
        self.cross_cvr = self.sigma_x_res.dot(self.cvr_weight.dot(self.sigma_y_res.T))
        self.kalman_gain = self.cross_cvr.dot(inv(self.innov_cvr))

    def calculateInnovations(self, obs_tuples):
        """Calculate the innovations (residuals) vector and normalized innovations squared.

        Args:
            obs_tuples (list): :class:`.ObservationTuple` objects associated with the UKF step
        """
        true_y = concatenate(
            [obs_tuple.observation.measurements for obs_tuple in obs_tuples],
            axis=0
        )
        self.innovation = self.calcMeasurementResiduals(true_y, self.mean_pred_y)
        if self.maneuver_detection_method:
            self.maneuver_detection_method.calculateNIS(self.innovation, self.innov_cvr)
            self.nis = self.maneuver_detection_method.current_nis
            self.maneuver_gate = chi2.isf(self.maneuver_detection_method.maneuver_gate_val, len(true_y))

    def calcMeasurementResiduals(self, measurement_set_a, measurement_set_b):
        """Determine the measurement residuals.

        This is done generically which allows for measurements to be ordered in any fashion, but
        requires an associated boolean vector to flag for angle measurements. This special
        treatment is required because angles are nonlinear (modular), so subtraction is not a
        linear operation.

        Args:
            measurement_set_a (numpy.ndarray): `Mx1` compiled measurement array.
            measurement_set_b (numpy.ndarray): `Mx1` compiled measurement array.

        Returns:
            numpy.ndarray: `Mx1` measurement residual
        """
        # If we have an angular measurement, normalize the angles
        # Works for all angular values, because [-pi/2, pi/2] domains will never have diff > pi
        residual = map(
            lambda err, ang: wrapAngleNegPiPi(err) if ang in VALID_ANGLES else err,
            measurement_set_a - measurement_set_b,
            self.ang_meas_bool
        )

        return array(list(residual))

    def checkInnovationsCovariance(self, obs_tuples):
        """Check the innovations covariance matrix for numerical stability.

        Args:
            obs_tuples (list): :class:`.ObservationTuple` objects associated with the UKF step
        """
        self._logger.warning("Caught singular matrix error. Attempting to inflate covariance.")
        error_description = {
            "original": {
                "innov_cvr": self.innov_cvr.tolist(),
                "r_matrix": self.r_matrix.tolist(),
                "sigma_y_res": self.sigma_y_res.tolist(),
                "cvr_weight": self.cvr_weight.tolist(),
                "target": self.host.name,
                "jDate": self.host.julian_date_epoch
            }
        }
        self.innov_cvr, filename = innovationsCovarianceInflation(
            self.innov_cvr,
            self.r_matrix,
            obs_tuples,
            error_description
        )
        msg = f"Successfully inflated innov cov:\n\t{filename}"
        self._logger.warning(msg)

    def updateCovariance(self):
        """Update the covariance estimate at `k+1`."""
        self.est_p = self.pred_p - self.kalman_gain.dot(self.innov_cvr.dot(self.kalman_gain.T))

    def updateStateEstimate(self):
        """Update the state estimate estimate at `k+1`."""
        self.est_x = self.pred_x + self.kalman_gain.dot(self.innovation)

    def calcMeasurementMean(self, measurement_sigma_pts):
        """Determine the mean of the predicted measurements.

        This is done generically which allows for measurements to be ordered in any fashion, but
        requires an associated boolean vector to flag for angle measurements. This special
        treatment is required because angles are nonlinear (modular), so calculating the mean is
        not a linear operation.

            Angular mean:
                `theta_bar = atan2(sum(sin(th))/N, cos(th)/N)`

            Normal mean:
                `x_bar = (1/N)*sum(x)`

        Args:
            measurement_sigma_pts (numpy.ndarray): `MxS` array of predicted measurements, where
                `M` is the compiled measurement space, and `S` is the number of sigma points.

        Returns:
            numpy.ndarray: Mx1 predicted measurement mean
        """
        # If we have an angle measurement, calculate mean differently
        meas_mean = zeros((measurement_sigma_pts.shape[0], ))
        for idx, (meas, angular) in enumerate(zip(measurement_sigma_pts, self.ang_meas_bool)):
            if angular in VALID_ANGLES:
                mean = angularMean(meas, self.mean_weight)
                # Normalize angles valid in [0, 2pi]
                if angular == IsAngle.ANGLE_PI:
                    mean = wrapAngle2Pi(mean)
            else:
                mean = np_sum(meas.dot(self.mean_weight))

            meas_mean[idx] = mean

        return meas_mean

    def getPredictionResult(self):
        """Compile result message for a predict step.

        Returns:
            dict: message with predict information
        """
        return {
            "time": self.time,
            "est_x": self.est_x,
            "est_p": self.est_p,
            "pred_x": self.pred_x,
            "pred_p": self.pred_p,
            "sigma_points": self.sigma_points,
            "sigma_x_res": self.sigma_x_res,
        }

    def getForecastResult(self):
        """Compile result message for a forecast step.

        Returns:
            dict: message with forecast information
        """
        return {
            "sigma_points": self.sigma_points,
            'ang_meas_bool': self.ang_meas_bool,
            'mean_pred_y': self.mean_pred_y,
            'sigma_y_res': self.sigma_y_res,
            'r_matrix': self.r_matrix,
            'cross_cvr': self.cross_cvr,
            'innov_cvr': self.innov_cvr,
            'kalman_gain': self.kalman_gain,
            'est_p': self.est_p,
        }

    def getUpdateResult(self):
        """Compile result message for an update step.

        Returns:
            dict: message with update information
        """
        start = self.getForecastResult()
        start.update({
            "est_x": self.est_x,
            "innovation": self.innovation,
            "nis": self.nis,
            "source": self.source,
            "detected_maneuver": self.detected_maneuver
        })
        return start
