"""
UKF Step Demo
=============

Demonstrate how to create the required :class:`.agent_base.Agent` objects, propagate them forward, make an :class:`.Observation`, and apply the observation to an unscented Kalman filter.
This shows how to directly create and use the following classes:

- :class:`.TargetAgent`
- :class:`.EstimateAgent`
- :class:`.SensingAgent`
- :class:`.UnscentedKalmanFilter`
- :class:`.Observation`
"""

# isort: skip

# Standard Library Imports
# %%
# Initial Setup
# -------------
#
# General Imports
# ###############
#
from datetime import datetime

# Third Party Imports
import numpy as np

# RESONAATE Imports
from resonaate.data import setDBPath

# In-memory database.
# [NOTE]: This must be called before any calls to getDBConnection() are made!
setDBPath("sqlite://")

# RESONAATE Imports
# %%
# Setup problem time variables
# ----------------------------
#
# Creating a clock object requires the Julian date of the initial epoch, a timespan (seconds), and a timestep (seconds).
from resonaate.scenario.clock import ScenarioClock

# Define time variables
datetime_start = datetime(2019, 2, 1, 12, 0)
tspan = 300.0  # seconds
dt = 60.0  # seconds

# Create the clock object
clock = ScenarioClock(datetime_start, tspan, dt)

# For convenience, time is initialized to zero
t0 = clock.time

# RESONAATE Imports
# %%
#
# Build a satellite as a :class:`.TargetAgent`
# --------------------------------------------
#
# This requires an id number, name, initial state.
# Also, users must define a :class:`.Dynamics` object that handles propagating the satellite forward in time.
from resonaate.agents.target_agent import TargetAgent
from resonaate.dynamics.two_body import TwoBody

# Initial information
sat1_id = 10001  # Unique ID number of satellite
sat1_name = "RSO1"  # Human-readable name of satellite
sat1_type = "Spacecraft"  # Type of agent object
realtime = True  # Propagate using dynamics model, rather than importing data

# Initial state vector
sat1_x0 = np.array([10000.0, 0.0, 0.0, 0.0, 6.3134776, 0.0])  # Position (km)  # Velocity (km)

# Create a two body dynamics object for simple Keplerian propagation
two_body_dynamics = TwoBody()

# Construct the satellite object
sat1_agent = TargetAgent(
    sat1_id,
    sat1_name,
    sat1_type,
    sat1_x0,
    clock,
    two_body_dynamics,
    realtime,
    25.0,
    100,
    0.21,
)

# RESONAATE Imports
# %%
#
# Build a corresponding :class:`.EstimateAgent`
# ---------------------------------------------
#
from resonaate.agents.estimate_agent import EstimateAgent
from resonaate.estimation.kalman.unscented_kalman_filter import UnscentedKalmanFilter
from resonaate.physics.noise import continuousWhiteNoise, initialEstimateNoise
from resonaate.scenario.config.estimation_config import InitialOrbitDeterminationConfig

# Extra information required by EstimateAgent
seed = 12345  # Seeds the random number generator, used for adding noise
pos_var = 1e-3  # normalized variance for position
vel_var = 1e-6  # normalized variance for velocity uncertainty

# Generate a random vector centered on x0
sat1_est0, sat1_cov0 = initialEstimateNoise(sat1_x0, pos_var, vel_var, np.random.default_rng(seed))

# Generate the assumed noise covariance matrix used in the Kalman filter
q_matrix = continuousWhiteNoise(dt, 1e-12)

# Create an unscented Kalman filter (UKF) for tracking the satellite
ukf = UnscentedKalmanFilter(
    sat1_id,
    clock.time,
    sat1_est0,
    sat1_cov0,
    two_body_dynamics,
    q_matrix,
    None,
    False,
)

# Create an EstimateAgent object to track the actual TargetAgent satellite
sat1_estimate_agent = EstimateAgent(
    sat1_id,
    sat1_name,
    sat1_type,
    clock,
    sat1_est0,
    sat1_cov0,
    ukf,
    None,
    InitialOrbitDeterminationConfig(),
    25.0,
    100,
    0.21,
)

# RESONAATE Imports
# %%
#
# Build a :class:`.SensingAgent`
# ------------------------------
#
from resonaate.agents.sensing_agent import SensingAgent
from resonaate.dynamics.terrestrial import Terrestrial
from resonaate.physics.transforms.methods import ecef2eci, lla2ecef
from resonaate.sensors.radar import Radar

# Sensor information
sensor_name = "Test Sensor"
sensor_type = "Ground-Based"  # Provides 3D measurements
sensor_id = 123690  # Unique ID number

# Create a measurement noise covariance for this sensor
r_matrix = np.diagflat(
    [
        3.0461741978670863e-12,
        3.0461741978670863e-12,
        2.5000000000000004e-11,
        1.0000000000000002e-14,
    ],
)

az_mask = np.array([60.0, 300.0])  # Valid azimuth range (deg), measured positive from North
el_mask = np.array(
    [5.0, 90.0],
)  # Valid elevation range (deg), measured positive from local horizon
slew_rate = 5.0  # Sensor slew rate (deg/sec)
efficiency = 0.95  # Sensor efficiency (unitless)
diameter = 14  # Effective aperture diameter (m)
tx_power = 2500000.0  # Sensor transmit power (W)
tx_frequency = 1.5 * 1e9  # Sensor transmit center frequency (Hz)
min_detectable_power = 1.1954373300571727e-14  # Minimum detectable power by radar (W)
field_of_view = "conic"
calc_background = True

radar_sensor = Radar(
    az_mask,
    el_mask,
    r_matrix,
    diameter,
    efficiency,
    tx_power,
    tx_frequency,
    min_detectable_power,
    np.radians(slew_rate),
    field_of_view,
    calc_background,
    None,
    None,
)

# Lat, Lon, Alt for sensor near VT
sensor_lla = np.asarray(
    [
        np.radians(37.20723655488582),  # latitude (degrees)
        np.radians(-80.41918669095047),  # longitude (degrees)
        0.105,  # Altitude (km)
    ],
)

# Convert sensor location to ECEF
sensor_ecef = lla2ecef(sensor_lla)

# Use terrestrial (ground-based) sensor dynamics
sensor_dynamics = Terrestrial(clock.julian_date_start, sensor_ecef)

sensor_agent = SensingAgent(
    sensor_id,
    sensor_name,
    sensor_type,
    ecef2eci(sensor_ecef, clock.datetime_start),
    clock,
    radar_sensor,
    sensor_dynamics,
    True,  # real time propagation
    25.0,
    100.0,
    0.21,
)

# %%
#
# Propagate agents forward
# ------------------------
#

# Update time values
clock.ticToc()
t1 = clock.time

# Propagate sensor agent to t1
sensor_agent.eci_state = sensor_agent.dynamics.propagate(t0, t1, sensor_agent.eci_state)

# Propagate satellite to t1, and save its ECI state
sat1_agent.eci_state = two_body_dynamics.propagate(t0, t1, sat1_x0)

# Propagate estimate's filter via the prediction step (a priori)
sat1_estimate_agent.nominal_filter.predict(t1)

# Predict step: no observations are made
obs = []
truth_state = sat1_agent.eci_state  # [NOTE]: only used for debugging purposes!
# Apply filter prediction step to estimate's state
sat1_estimate_agent.update(obs)

# Magnitude of true error (true - estimate) after prediction step
prior_error = np.linalg.norm(truth_state[:3] - sat1_estimate_agent.eci_state[:3])
print(prior_error)

# RESONAATE Imports
# %%
#
# Make an :class:`.Observation`
# -----------------------------
#
from resonaate.data.observation import Observation

observation = Observation.fromMeasurement(
    sensor_type="Radar",
    sensor_id=sensor_id,
    target_id=sat1_agent.simulation_id,
    tgt_eci_state=sat1_agent.eci_state,
    sensor_eci=sensor_agent.eci_state,
    epoch_jd=clock.julian_date_epoch,
    measurement=radar_sensor.measurement,
    noisy=True,
)

print(observation)

# %%
#
# Apply :class:`.Observation` to :class:`.UnscentedKalmanFilter`
# ---------------------------------------------------------------
#

# Update estimate's filter via the measurement update step (a posteriori)
sat1_estimate_agent.nominal_filter.update([observation])

# Apply filter measurement update step to estimate's state
sat1_estimate_agent.state_estimate = sat1_estimate_agent.nominal_filter.est_x
sat1_estimate_agent.error_covariance = sat1_estimate_agent.nominal_filter.est_p

# Magnitude of true error (true - estimate) after measurement update step
posterior_error = np.linalg.norm(truth_state[:3] - sat1_estimate_agent.state_estimate[:3])

# Observation should reduce the estimation error
print(prior_error - posterior_error)
