from __future__ import annotations

# Standard Library Imports
import datetime
from unittest.mock import MagicMock, patch

# Third Party Imports
import pytest
from numpy import allclose, array, array_equal, diagflat, ones, sqrt, zeros
from numpy.linalg import LinAlgError, cholesky
from scipy.linalg import block_diag

# RESONAATE Imports
from resonaate.data.observation import Observation
from resonaate.dynamics import two_body
from resonaate.estimation import UnscentedKalmanFilter
from resonaate.estimation.sequential_filter import EstimateSource, FilterFlag
from resonaate.physics.measurements import IsAngle, Measurement
from resonaate.physics.time.stardate import ScenarioTime

# Local Imports
from .ukf_support import (
    GROUND_SENSOR_ECI,
    Q_MATRIX,
    R_MATRIX_OPTICAL,
    R_MATRIX_RADAR,
    SPACECRAFT_SENSOR_ECI,
    UKF_CROSS_CVR,
    UKF_CVR_WEIGHT,
    UKF_EST_P,
    UKF_EST_X,
    UKF_INNOV_CVR,
    UKF_KALMAN_GAIN,
    UKF_MEAN,
    UKF_MEAN_COV,
    UKF_MEAN_WEIGHT,
    UKF_MEAS_MEAN,
    UKF_MEAS_MEAN_RADAR,
    UKF_PRED_P,
    UKF_PRED_SIGMA_POINTS,
    UKF_PRED_X,
    UKF_SIGMA_OBS,
    UKF_SIGMA_POINTS,
    UKF_SIGMA_X_RES,
    UKF_SIGMA_Y_RES,
    UKF_TRUE_Y,
)


@pytest.fixture(name="ukf")
def createUKF() -> UnscentedKalmanFilter:
    """Construct a valid UKF object."""
    ukf = UnscentedKalmanFilter(
        tgt_id=10001,
        time=ScenarioTime(0.0),
        est_x=UKF_MEAN,
        est_p=UKF_MEAN_COV,
        dynamics=two_body.TwoBody(),
        q_matrix=Q_MATRIX,
        maneuver_detection=False,
        initial_orbit_determination=False,
        adaptive_estimation=False,
        resample=False,
    )

    # Directly set values for later use
    ukf.gamma = 0.0866025403784455
    ukf.mean_weight = UKF_MEAN_WEIGHT
    ukf.cvr_weight = UKF_CVR_WEIGHT
    return ukf


@pytest.fixture(name="radar_obs")
def createRadarObservation() -> Observation:
    """Construct a valid radar Observation object."""
    # [NOTE]: Easier to provide actual measurement than mocking...
    radar_measurement = Measurement.fromMeasurementLabels(
        ["azimuth_rad", "elevation_rad", "range_km", "range_rate_km_p_sec"],
        R_MATRIX_RADAR,
    )

    obs: Observation = MagicMock(spec=Observation)
    obs.measurement = radar_measurement
    obs.sensor_eci = SPACECRAFT_SENSOR_ECI
    obs.r_matrix = radar_measurement.r_matrix
    obs.dim = 4
    return obs


@pytest.fixture(name="optical_obs")
def createOpticalObservation() -> Observation:
    """Construct a valid optical Observation object."""
    # [NOTE]: Easier to provide actual measurement than mocking...
    optical_measurement = Measurement.fromMeasurementLabels(
        ["azimuth_rad", "elevation_rad"],
        R_MATRIX_OPTICAL,
    )

    obs: Observation = MagicMock(spec=Observation)
    obs.measurement = optical_measurement
    obs.sensor_eci = GROUND_SENSOR_ECI
    obs.r_matrix = optical_measurement.r_matrix
    obs.dim = 2
    return obs


@patch("resonaate.estimation.kalman.unscented_kalman_filter.BehavioralConfig")
def testCheckSqrtCovariance(mocked_config: MagicMock, ukf: UnscentedKalmanFilter):
    """Test method for checking covariance is positive semi-definite."""
    negative_definite = diagflat((-3, -2, -1))
    positive_definite = diagflat((1, 2, 3))

    # Check positive definiteness works as intended
    sqrt_cov = ukf._checkSqrtCovariance(positive_definite, cholesky)
    assert allclose(sqrt_cov, diagflat(sqrt((1, 2, 3))), rtol=1e-4, atol=1e-7)

    # Check that non-positive definite raises error without config
    mocked_config.getConfig().debugging.NearestPD = False
    with pytest.raises(LinAlgError):
        ukf._checkSqrtCovariance(negative_definite, cholesky)

    # Check that non-positive definite raises error with config
    mocked_config.getConfig().debugging.NearestPD = True
    sqrt_cov = ukf._checkSqrtCovariance(negative_definite, cholesky)
    expected = array(
        [
            [4.4408921e-16, 0.0000000e00, 0.0000000e00],
            [0.0000000e00, 4.4408921e-16, 0.0000000e00],
            [0.0000000e00, 0.0000000e00, 4.4408921e-16],
        ],
    )
    assert allclose(sqrt_cov, expected, rtol=1e-4, atol=1e-7)

    # Check zero matrix condition
    mocked_config.getConfig().debugging.NearestPD = True
    sqrt_cov = ukf._checkSqrtCovariance(zeros((3, 3)), cholesky)
    assert allclose(sqrt_cov, zeros((3, 3)), rtol=1e-7, atol=1e-12)


def testCalculateSigmaPoints(ukf: UnscentedKalmanFilter):
    """Test the function to calculate sigma points."""
    sigma_points = ukf.generateSigmaPoints(ukf.est_x, ukf.est_p)

    assert sigma_points.shape == (ukf.x_dim, ukf.num_sigmas)
    assert allclose(sigma_points, UKF_SIGMA_POINTS, rtol=1e-4, atol=1e-7)


def testKappa():
    """Ensure kappa is overridden properly."""
    ukf = UnscentedKalmanFilter(
        tgt_id=10001,
        time=ScenarioTime(0.0),
        est_x=array([1, 2, 3, 4, 5, 6]),
        est_p=ones((6, 6)),
        dynamics=two_body.TwoBody(),
        q_matrix=ones((6, 6)),
    )
    assert ukf.extra_parameters["kappa"] is None

    ukf = UnscentedKalmanFilter(
        tgt_id=10001,
        time=ScenarioTime(0.0),
        est_x=array([1, 2, 3, 4, 5, 6]),
        est_p=ones((6, 6)),
        dynamics=two_body.TwoBody(),
        q_matrix=ones((6, 6)),
        kappa=0.0,
    )
    assert ukf.extra_parameters["kappa"] is not None
    assert ukf.extra_parameters["kappa"] == 0.0

    ukf = UnscentedKalmanFilter(
        tgt_id=10001,
        time=ScenarioTime(0.0),
        est_x=array([1, 2, 3, 4, 5, 6]),
        est_p=ones((6, 6)),
        dynamics=two_body.TwoBody(),
        q_matrix=ones((6, 6)),
        kappa=2.0,
    )
    assert ukf.extra_parameters["kappa"] is not None
    assert ukf.extra_parameters["kappa"] == 2.0


def testPredictStateEstimate(ukf: UnscentedKalmanFilter):
    """Test the function to calculate the predicted state estimate."""
    final_time = ScenarioTime(60.0)
    # Mock sigma point generation
    ukf.generateSigmaPoints = MagicMock()
    ukf.generateSigmaPoints.return_value = UKF_SIGMA_POINTS

    ukf.predictStateEstimate(final_time)

    ukf.generateSigmaPoints.assert_called_once_with(ukf.est_x, ukf.est_p)
    assert allclose(ukf.pred_x, UKF_PRED_X, rtol=1e-4, atol=1e-7)
    assert allclose(ukf.sigma_points, UKF_PRED_SIGMA_POINTS, rtol=1e-4, atol=1e-7)


def testPredictCovariance(ukf: UnscentedKalmanFilter):
    """Test the function to calculate the predicted."""
    # Define function inputs
    final_time = ScenarioTime(60.0)
    ukf.sigma_points = UKF_PRED_SIGMA_POINTS
    ukf.pred_x = UKF_PRED_X
    ukf.predictCovariance(final_time)

    assert allclose(ukf.sigma_x_res, UKF_SIGMA_X_RES, rtol=1e-4, atol=1e-7)
    assert allclose(ukf.pred_p, UKF_PRED_P, rtol=1e-4, atol=1e-7)


def testCalculateMeasurementMatrix(ukf: UnscentedKalmanFilter):
    """Test the function to calculate the measurement matrix."""
    obs: Observation = MagicMock(spec=Observation)
    obs.measurement.angular_values = [IsAngle.ANGLE_0_2PI, IsAngle.ANGLE_NEG_PI_PI]
    ukf._calcMeasurementSigmaPoints = MagicMock()
    ukf._calcMeasurementSigmaPoints.return_value = UKF_SIGMA_OBS
    ukf.calcMeasurementMean = MagicMock()
    ukf.calcMeasurementMean.return_value = UKF_MEAS_MEAN

    ukf.calculateMeasurementMatrix([obs])
    ukf._calcMeasurementSigmaPoints.assert_called_once()
    ukf.calcMeasurementMean.assert_called_once()

    true_is_angular = array([True, True])
    assert all(true_is_angular == ukf.is_angular)
    assert allclose(UKF_SIGMA_Y_RES, ukf.sigma_y_res, rtol=1e-4, atol=1e-7)


@patch("resonaate.estimation.kalman.unscented_kalman_filter.julianDateToDatetime")
def testCalcMeasurementSigmaPoints(mocked_jd2dt: MagicMock, ukf: UnscentedKalmanFilter):
    """Test calculating measurement sigma points with H matrix."""
    mocked_jd2dt.return_value = datetime.datetime(2023, 10, 20, 20, 43, 44)

    # Mocking observation
    obs: Observation = MagicMock(spec=Observation)
    obs.measurement.calculateMeasurement = MagicMock()
    # [NOTE]: This will loop over the iterable and return the next entry.
    #   The transpose is necessary. Also, the call expects a dict of measurements to be returned
    obs.measurement.calculateMeasurement.side_effect = [
        {"azimuth": sigma_obs[0], "elevation": sigma_obs[1]}
        for sigma_obs in UKF_SIGMA_OBS.transpose()
    ]

    ukf.sigma_points = UKF_SIGMA_POINTS

    sigma_obs = ukf._calcMeasurementSigmaPoints([obs])

    mocked_jd2dt.assert_called()
    assert allclose(sigma_obs, UKF_SIGMA_OBS, rtol=1e-4, atol=1e-7)


@patch("resonaate.estimation.kalman.unscented_kalman_filter.julianDateToDatetime")
def testCalcMeasurementMean(
    mocked_jd2dt: MagicMock,
    ukf: UnscentedKalmanFilter,
    radar_obs: Observation,
):
    """Test measurement mean calculation."""
    mocked_jd2dt.return_value = datetime.datetime(2021, 10, 21, 11, 26, 13)
    # [NOTE]: Generating valid measurement sigma points
    ukf.sigma_points = UKF_PRED_SIGMA_POINTS
    meas_sigma_pts = ukf._calcMeasurementSigmaPoints([radar_obs])

    meas_mean = ukf.calcMeasurementMean(meas_sigma_pts, radar_obs.measurement.angular_values)
    assert allclose(meas_mean, UKF_MEAS_MEAN_RADAR, rtol=1e-4, atol=1e-7)


def testPredictionResult(ukf: UnscentedKalmanFilter):
    """Test data compilation function."""
    # [NOTE]: set values expected to be in result ahead of time
    ukf.sigma_points = UKF_SIGMA_POINTS
    ukf.sigma_x_res = UKF_SIGMA_X_RES
    # [NOTE]: Ensure all keys are included
    expected_keys = [
        "time",
        "est_x",
        "est_p",
        "pred_x",
        "pred_p",
        "sigma_points",
        "sigma_x_res",
    ]

    result = ukf.getPredictionResult()
    assert array_equal(result.sigma_points, UKF_SIGMA_POINTS)
    assert array_equal(result.sigma_x_res, UKF_SIGMA_X_RES)
    for key in expected_keys:
        assert hasattr(result, key)


def testForecastResult(ukf: UnscentedKalmanFilter):
    """Test data compilation function."""
    # [NOTE]: set values expected to be in result ahead of time
    ukf.sigma_points = UKF_SIGMA_POINTS
    ukf.sigma_y_res = UKF_SIGMA_Y_RES
    # [NOTE]: Ensure all keys are included
    expected_keys = [
        "is_angular",
        "mean_pred_y",
        "r_matrix",
        "cross_cvr",
        "innov_cvr",
        "kalman_gain",
        "est_p",
        "sigma_points",
        "sigma_y_res",
    ]

    result = ukf.getForecastResult()
    assert array_equal(result.sigma_points, UKF_SIGMA_POINTS)
    assert array_equal(result.sigma_y_res, UKF_SIGMA_Y_RES)
    for key in expected_keys:
        assert hasattr(result, key)


def testPredict(ukf: UnscentedKalmanFilter):
    """Test predict() method."""
    ukf.predictCovariance = MagicMock()
    ukf.predictStateEstimate = MagicMock()

    final_time = ScenarioTime(300.0)
    assert ukf.time == ScenarioTime(0.0)

    ukf.predict(final_time)

    assert ukf.time == final_time
    assert ukf._flags == FilterFlag.NONE
    ukf.predictCovariance.assert_called_once_with(final_time)
    ukf.predictStateEstimate.assert_called_once_with(final_time, scheduled_events=None)


@patch("resonaate.estimation.kalman.unscented_kalman_filter.julianDateToDatetime")
def testForecast(mocked_jd2dt: MagicMock, ukf: UnscentedKalmanFilter, optical_obs: Observation):
    """Test forecast() method."""
    mocked_jd2dt.return_value = datetime.datetime(2021, 10, 21, 11, 26, 13)
    ukf._resample = False
    ukf.sigma_points = UKF_SIGMA_POINTS
    ukf.sigma_y_res = UKF_SIGMA_Y_RES
    ukf.sigma_x_res = UKF_SIGMA_X_RES
    ukf.pred_p = UKF_PRED_P
    ukf.generateSigmaPoints = MagicMock()

    ukf.forecast([optical_obs])

    ukf.generateSigmaPoints.assert_not_called()
    assert allclose(ukf.innov_cvr, UKF_INNOV_CVR, rtol=1e-4, atol=1e-7)
    assert allclose(ukf.cross_cvr, UKF_CROSS_CVR, rtol=1e-4, atol=1e-7)
    assert allclose(ukf.kalman_gain, UKF_KALMAN_GAIN, rtol=1e-4, atol=1e-7)
    assert allclose(ukf.est_p, UKF_EST_P, rtol=1e-4, atol=1e-7)


@patch("resonaate.estimation.kalman.unscented_kalman_filter.julianDateToDatetime")
def testForecastResample(
    mocked_jd2dt: MagicMock,
    ukf: UnscentedKalmanFilter,
    radar_obs: Observation,
    optical_obs: Observation,
):
    """Test forecast() method with resampling."""
    mocked_jd2dt.return_value = datetime.datetime(2021, 10, 21, 11, 26, 13)
    ukf._resample = True
    ukf.sigma_points = UKF_SIGMA_POINTS
    ukf.sigma_y_res = UKF_SIGMA_Y_RES
    ukf.sigma_x_res = UKF_SIGMA_X_RES
    ukf.pred_p = UKF_PRED_P
    ukf.generateSigmaPoints = MagicMock()
    ukf.generateSigmaPoints.return_value = UKF_SIGMA_POINTS

    ukf.forecast([radar_obs, optical_obs])

    ukf.generateSigmaPoints.assert_called_once_with(ukf.pred_x, ukf.pred_p)
    assert array_equal(ukf.r_matrix, block_diag(R_MATRIX_RADAR, R_MATRIX_OPTICAL))

    z_dim = radar_obs.dim + optical_obs.dim
    assert ukf.innov_cvr.shape == (z_dim, z_dim)
    assert ukf.cross_cvr.shape == (ukf.x_dim, z_dim)
    assert ukf.kalman_gain.shape == (ukf.x_dim, z_dim)
    assert ukf.est_p.shape == (ukf.x_dim, ukf.x_dim)


def testUpdateNoObservations(ukf: UnscentedKalmanFilter):
    """Test update() method without any observations."""
    ukf.sigma_points = UKF_SIGMA_POINTS
    ukf.pred_p = UKF_PRED_P
    ukf.est_p = 2 * UKF_PRED_P
    ukf.forecast = MagicMock()

    ukf.update([])
    assert ukf.source == EstimateSource.INTERNAL_PROPAGATION
    assert array_equal(ukf.est_x, UKF_SIGMA_POINTS[:, 0])
    assert array_equal(ukf.est_p, UKF_PRED_P)
    ukf.forecast.assert_not_called()


@patch("resonaate.estimation.kalman.unscented_kalman_filter.chiSquareQuadraticForm")
@patch("resonaate.estimation.kalman.unscented_kalman_filter.residuals")
def testUpdate(
    mocked_residuals: MagicMock,
    mocked_chi_square: MagicMock,
    ukf: UnscentedKalmanFilter,
    optical_obs: Observation,
):
    """Test update() method with observations."""
    mocked_residuals.return_value = UKF_MEAS_MEAN
    optical_obs.measurement_states = UKF_TRUE_Y
    ukf.forecast = MagicMock()
    ukf.checkManeuverDetection = MagicMock()
    ukf._debugChecks = MagicMock()
    ukf.kalman_gain = UKF_KALMAN_GAIN
    ukf.pred_x = UKF_MEAN

    ukf.update([optical_obs])

    ukf.forecast.assert_called_once()
    ukf.checkManeuverDetection.assert_called_once()
    ukf._debugChecks.assert_called_once()
    mocked_chi_square.assert_called_once()
    mocked_residuals.assert_called_once()
    assert array_equal(ukf.true_y, UKF_TRUE_Y)
    assert allclose(ukf.est_x, UKF_EST_X, rtol=1e-4, atol=1e-7)
