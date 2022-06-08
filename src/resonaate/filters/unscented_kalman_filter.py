# Standard Library Imports
from pickle import loads
# Third Party Imports
from numpy import (
    ones, diagflat, zeros, sqrt, matmul, full, concatenate, sin,
    cos, arctan2, array
)
from numpy import sum as np_sum
from numpy.linalg import cholesky, LinAlgError, inv
from scipy.linalg import block_diag, norm
# RESONAATE Imports
from .filter_debug_utils import innovationsCovarianceInflation, findNearestPositiveDefiniteMatrix, logFilterStep
from .sequential_filter import SequentialFilter
from ..parallel import getRedisConnection
from ..physics.math import normalizeAngle
from ..common.behavioral_config import BehavioralConfig


class UnscentedKalmanFilter(SequentialFilter):  # pylint: disable=too-many-instance-attributes
    """UNSCENTED KALMAN FILTER (BASIC).

    The UKF class provides the framework and functionality for a basic Unscented Kalman Filter,
    which propagates nonlinearly the state estimate, and approximates the covariance by propagating
    nonlinearly and combining sigma points.  The Basic UKF class assumes additive process noise.
    """

    def __init__(self, dynamics, q_matrix, alpha=0.001, beta=2.0, kappa=None):
        """Instantiate a UKF object.

        Args:
            dynamics (:class:`.Dynamics`): dynamics object associated with the filter's target
            q_matrix (``numpy.ndarray``): dynamics error covariance matrix
            alpha (float, optional): sigma point spread. Defaults to 0.001.
            beta (float, optional): Gaussian pdf. Defaults to 2.0.
            kappa ([type], optional): UKF param. Defaults to None.
        """
        super(UnscentedKalmanFilter, self).__init__(dynamics, q_matrix)

        # Calculate scaling parameter, Lambda. Save tuning params
        if not kappa:
            kappa = 3 - self.x_dim
        lambda_kf = (alpha**2) * (self.x_dim + kappa) - self.x_dim

        # Save simple class variables
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
        self._alpha = alpha
        self._beta = beta
        self._lambda = lambda_kf
        self._kappa = kappa

        # Other class variables not immediately instantiated
        self.sigma_points = None
        self.sigma_x_variables = None
        self.sigma_y_variables = None
        self.sigma_obs = None
        self.last_obs_jdate = None

    def predict(self, final_time):
        """Propagate the state and covariance estimates.

        Args:
            final_time (:class:`.ScenarioTime`): time to propagate to
        """
        self.final_time = final_time
        # STEP 1: Calculate the predicted state estimate at t(k) (X(k|k - 1))
        self.predictStateEstimate()
        # STEP 2:  Calculate the predicted covariance at t(k) (P(k|k - 1))
        self.predictCovariance()
        # STEP 3: Update the time step
        self.time = self.final_time

    def forecast(self, obs):
        """Update the covariance estimate.

        Args:
            obs (list): :class:`.Observation` list associated with this timestep
        """
        if not isinstance(obs, list):
            obs = [obs]

        sensor_agents = loads(getRedisConnection().get('sensor_agents'))

        # STEP 1:  Calculate the Measurement Matrix (H)
        self.calculateMeasurementMatrix(sensor_agents, obs)
        # STEP 2:  Compile the Observation Noise Covariance (R)
        self.compileObsNoiseCovariance(sensor_agents, obs)
        # STEP 3:  Calculate the Cross Covariance (C), the Innovations Covariance (S), & the Kalman Gain (K)
        self.calculateKalmanGain(obs)
        # STEP 4:  Update the Covariance for the state (P(k|k))
        self.updateCovariance()

    def update(self, obs, truth):
        """Update the state estimate.

        Args:
            obs (list): :class:`.Observation` list associated with this timestep
            truth (``numpy.ndarray``): truth state vector for the target in ECI frame
        """
        if not obs:
            self.source = "Propagation"
            # If there are no observations, there is no update information and the predicted state
            #   estimate and covariance are stored as the updated state estimate and covariance
            self.est_x = self.pred_x
            self.est_p = self.pred_p
        else:
            self.source = "Observation"
            if BehavioralConfig.getConfig().debugging.EstimateErrorInflation:
                ## Grab debugging information before any steps take place
                description = {
                    "covar_before": self.est_p.tolist(),
                    "estimate_before": self.est_x.tolist(),
                    "sigma_x_variables": self.sigma_x_variables.tolist()
                }

            # If there are observations, the predicted state estimate and covariance are updated
            self.forecast(obs)
            # STEP 1:  Compile the true measurement state vector (Yt)
            self.compileTrueObsState(obs)
            # STEP 2:  Calculate the Innovations vector (nu)
            self.calculateInnovations()

            # STEP 3:  Update the State EstimateAgent (X(k|k))
            self.updateStateEstimate()

            # Check error inflation, and write debuggin info if needed
            if BehavioralConfig.getConfig().debugging.EstimateErrorInflation:
                tol_km = 5  # Estimate inflation error tolerance (km)
                pred_error = abs(norm(truth[:3] - self.pred_x[:3]))
                est_error = abs(norm(truth[:3] - self.est_x[:3]))

                # If error increase is larger than desired log the debug information
                if est_error > pred_error + tol_km:
                    sensor_agents = loads(getRedisConnection().get('sensor_agents'))
                    file_name = logFilterStep(self, description, obs, truth, sensor_agents)
                    self.logger.warning("EstimateAgent error inflation occurred:\n\t{0}".format(file_name))

    def predictStateEstimate(self):
        """Propagate the previous state estimate from k - 1 to k."""
        # STEP 1:  Find the covariance estimate's square root using Cholesky Decomposition
        ## [REVIEW][UKF-Numeric]: I think this is generally required. Could be worth checking in the future.
        try:
            cholesky_p = cholesky(self.est_p)
        except LinAlgError:
            if BehavioralConfig.getConfig().debugging.NearestPD:
                cholesky_p, file_name = findNearestPositiveDefiniteMatrix(self.est_p)
                self.logger.warning(
                    "`nearestPD()` function was used in `predictStateEstimate()`:\n\t{0}".format(file_name)
                )
            else:
                raise

        # STEP 2:  Calculate the sigma points based on the current state estimate
        tmp_sigma_points = matmul(self.est_x.reshape((self.x_dim, 1)), ones((1, self.num_sigmas))) \
            + self.gamma * concatenate((zeros((self.x_dim, 1)), cholesky_p, -cholesky_p), axis=1)
        self.sigma_points = self.dynamics.propagate(
            self.time,
            self.final_time,
            tmp_sigma_points
        ).reshape(self.x_dim, self.num_sigmas)

        # STEP 3:  Calculate the predicted state estimate by combining the sigma points
        self.pred_x = matmul(self.sigma_points, self.mean_weight)

    def predictCovariance(self):
        """Propagate the previous covariance estimate from k - 1 to k."""
        ## [TODO]: Add is thrusting check here?
        # STEP 4:  Calculate the predicted covariance estimate using the sigma points
        self.sigma_x_variables = self.sigma_points \
            - matmul(self.pred_x.reshape((self.x_dim, 1)), ones((1, self.num_sigmas)))
        self.pred_p = matmul(matmul(self.sigma_x_variables, self.cvr_weight), self.sigma_x_variables .T) + self.q_matrix

        ## [REVIEW][UKF-Numeric]: I think this is generally required. Could be worth checking in the future.
        try:
            cholesky_p = cholesky(self.pred_p)
        except LinAlgError:
            if BehavioralConfig.getConfig().debugging.NearestPD:
                cholesky_p, file_name = findNearestPositiveDefiniteMatrix(self.pred_p)
                self.logger.warning(
                    "`nearestPD()` function was used in `predictCovariance()`:\n\t{0}".format(file_name)
                )
            else:
                raise

        self.sigma_points = matmul(
            self.pred_x.reshape((self.x_dim, 1)),
            ones((1, self.num_sigmas))
        ) + self.gamma * concatenate((zeros((self.x_dim, 1)), cholesky_p, -cholesky_p), axis=1)

    def calculateMeasurementMatrix(self, sensor_agents, obs):
        """Calculate the stacked Observation/Measurement Matrix for a set of observations.

        The UKF doesn't use an H Matrix.  Instead, the differences between the predicted state or
        observations, and the associated sigma values are calculated.  These are used to
        determine the cross and innovations covariances.

        Args:
            obs (:class:`.Observation`): observations associated with this UKF step
        """
        obs_vector_list = []
        for number in range(self.num_sigmas):
            obs_states = []
            angular_measurement_bool = []
            for pred_observation in obs:
                sensor = sensor_agents[pred_observation.observer].sensors
                observation, angle_bool = sensor.makeObservation(
                    self.host.simulation_id,
                    self.host.name,
                    self.sigma_points[:, number],
                    self.host.visual_cross_section,
                    noisy=False,  # Don't add noise in sigma point measurements
                    check_viz=False  # Don't need to check visibility for sigma points
                )
                obs_states.append(observation.measurements)
                angular_measurement_bool.append(angle_bool)

            stacked_obs_state = concatenate(obs_states, axis=0)
            stacked_obs_state.shape = (stacked_obs_state.size, 1)

            # Add stacked observations to the list
            obs_vector_list.append(stacked_obs_state)

        # Concatenate stacked obs into (size of all obs)x(num sigma)
        self.sigma_obs = concatenate(obs_vector_list, axis=1)

        # 1D boolean array of whether each corresponding measurement was angular or not
        self.ang_meas_bool = concatenate(angular_measurement_bool, axis=0)

        # Save mean measurement state
        self.est_y = self.calcMeasurementMean(self.sigma_obs)

        # Determine the difference between the sigma pt observations and the mean observation
        self.sigma_y_variables = zeros(self.sigma_obs.shape)
        for item in range(self.sigma_obs.shape[1]):
            self.sigma_y_variables[:, item] = self.calcMeasurementResiduals(self.sigma_obs[:, item], self.est_y)

    def compileObsNoiseCovariance(self, sensor_agents, obs):
        """Combine the Measurement Noise Covariance matrices associated with the set of observations.

        Args:
            obs (:class:`.Observation`): observations associated with this UKF step
        """
        temp = [sensor_agents[observation.observer].sensors.r_matrix for observation in obs]
        self.r_matrix = block_diag(*temp)

    def calculateKalmanGain(self, obs):
        """Calculate the Kalman Gain matrix.

        Args:
            obs (:class:`.Observation`): observations associated with this UKF step
        """
        self.innov_cvr = matmul(self.sigma_y_variables, matmul(self.cvr_weight, self.sigma_y_variables.T)) \
            + self.r_matrix
        self.checkInnovCovariance(obs)
        self.cross_cvr = matmul(self.sigma_x_variables, matmul(self.cvr_weight, self.sigma_y_variables.T))
        self.kalman_gain = matmul(self.cross_cvr, inv(self.innov_cvr))

    def compileTrueObsState(self, obs):
        """Stack the true observation output vector based on a set of Observations objects.

        Args:
            obs (:class:`.Observation`): observations associated with this UKF step
        """
        # Retrieve list of obs states
        obs_vector_list = [observation.measurements for observation in obs]
        self.true_y = concatenate(obs_vector_list, axis=0)

    def calculateInnovations(self):
        """Calculate the Innovations (Residuals) vector."""
        # Calculate the mean observation
        self.residual = self.calcMeasurementResiduals(self.true_y, self.est_y)
        self.maneuver_metric = matmul(matmul(self.residual.T, inv(self.innov_cvr)), self.residual)

    def calcMeasurementResiduals(self, meas_a, meas_b):
        """Determine the measurement residuals.

        This is done generically which allows for measurements to be ordered in any
        fashion, but requires an associated boolean vector to flag for angle
        measurements. This special treatment is required because angles are
        nonlinear (modular), so subtraction is not a linear operation.
        """
        res = zeros(meas_b.shape)
        for item, is_angle in enumerate(self.ang_meas_bool):
            y_err = meas_a[item] - meas_b[item]
            if is_angle:
                # If we have an angular measurement, normalize the angles
                res[item] = normalizeAngle(y_err)
            else:
                res[item] = y_err

        return res

    def checkInnovCovariance(self, obs):
        """Check the Innovations Covariance matrix for numerical stability.

        Args:
            obs (:class:`.Observation`): observations associated with this UKF step
        """
        try:
            inv(self.innov_cvr)
        except LinAlgError:
            if BehavioralConfig.getConfig().debugging.SingularMatrix:
                self.logger.warning("Caught singular matrix error. Attempting to inflate covariance.")
                error_description = {
                    "original": {
                        "innov_cvr": self.innov_cvr.tolist(),
                        "r_matrix": self.r_matrix.tolist(),
                        "sigma_y_variables": self.sigma_y_variables.tolist(),
                        "cvr_weight": self.cvr_weight.tolist(),
                        "target": self.host.name,
                        "jDate": self.host.julian_date_epoch
                    }
                }
                self.innov_cvr, filename = innovationsCovarianceInflation(
                    self.innov_cvr,
                    self.r_matrix,
                    obs,
                    error_description
                )
                self.logger.warning("Successfully inflated innov cov:\n\t{0}".format(filename))
            else:
                raise

    def updateCovariance(self):
        """Update the covariance estimate at k. Rewritten for UKF form."""
        self.est_p = self.pred_p - matmul(self.kalman_gain, matmul(self.innov_cvr, self.kalman_gain.T))

    def updateStateEstimate(self):
        """Update the state estimate estimate at k."""
        self.est_x = self.pred_x + matmul(self.kalman_gain, self.residual)

    def calcMeasurementMean(self, measurement_sigma_pts):
        """Determine the mean of the predicted measurements.

        This is done generically which allows for measurements to be ordered in any
        fashion, but requires an associated boolean vector to flag for angle
        measurements. This special treatment is required because angles are
        nonlinear (modular), so calculating the mean is not a linear operation.

        Angular mean:
            th_bar = atan2(sum(sin(th))/N, cos(th)/N)

        Normal mean:
            x_bar = (1/N)*sum(x)
        """
        prediction_y = []
        for item, is_angle in enumerate(self.ang_meas_bool):
            if is_angle:
                # If we have an angle measurement, calculate mean differently
                sum_sin = np_sum(matmul(sin(measurement_sigma_pts[item, :]), self.mean_weight))
                sum_cos = np_sum(matmul(cos(measurement_sigma_pts[item, :]), self.mean_weight))
                prediction_y.append(arctan2(sum_sin, sum_cos))
            else:
                prediction_y.append(np_sum(matmul(measurement_sigma_pts[item, :], self.mean_weight)))

        return array(prediction_y)

    def getPredictionResult(self):
        """Compile result message for a predict step.

        Returns:
            dict: message with predict information
        """
        return {
            "time": self.time,
            "final_time": self.final_time,
            "est_x": self.est_x,
            "est_p": self.est_p,
            "pred_x": self.pred_x,
            "pred_p": self.pred_p,
            "sigma_points": self.sigma_points,
            "sigma_x_variables": self.sigma_x_variables,
        }

    def getForecastResult(self):
        """Compile result message for a forecast step.

        Returns:
            dict: message with forecast information
        """
        return {
            'ang_meas_bool': self.ang_meas_bool,
            'est_y': self.est_y,
            'sigma_y_variables': self.sigma_y_variables,
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
            "true_y": self.true_y,
            "residual": self.residual,
            "maneuver_metric": self.maneuver_metric,
            "source": self.source
        })
        return start

    def updateFromAsyncResult(self, predict_result):
        """Set the corresponding values of this filter based on a filter prediction result.

        Args:
            predict_result (dict): updated attributes of a filter after the prediction step
        """
        for key, value in predict_result.items():
            setattr(self, key, value)
