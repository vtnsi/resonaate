# Third Party Imports
from numpy import array, zeros

try:
    # RESONAATE Imports
    from resonaate.agents.estimate_agent import EstimateAgent
    from resonaate.agents.sensing_agent import SensingAgent
    from resonaate.dynamics.two_body import TwoBody
    from resonaate.estimation.maneuver_detection import StandardNis
    from resonaate.estimation.sequential.unscented_kalman_filter import UnscentedKalmanFilter
    from resonaate.physics.time.stardate import JulianDate, ScenarioTime
    from resonaate.physics.transforms.methods import getSlantRangeVector
    from resonaate.physics.transforms.reductions import updateReductionParameters
    from resonaate.scenario.clock import ScenarioClock
    from resonaate.scenario.config.agent_configs import SensorConfigObject

except ImportError as error:
    raise Exception(f"Please ensure you have appropriate packages installed:\n {error}") from error

# Local Imports
# Testing Imports
from ..conftest import BaseTestCase

CONIC_SENSOR_CONFIG = {
    "name": "Test Radar",
    "id": 200000,
    "covariance": [
        [3.0461741978670863e-12, 0.0, 0.0, 0.0],
        [0.0, 3.0461741978670863e-12, 0.0, 0.0],
        [0.0, 0.0, 2.5000000000000004e-11, 0.0],
        [0.0, 0.0, 0.0, 4.0000000000000015e-12],
    ],
    "slew_rate": 0.08726646259971647,
    "azimuth_range": [0.0, 6.283185132646661],
    "elevation_range": [0.017453292519943295, 1.5707961522619713],
    "efficiency": 0.95,
    "aperture_area": 530.929158456675,
    "sensor_type": "Radar",
    "exemplar": [0.04908738521234052, 40500.0],
    "field_of_view": {"fov_shape": "conic"},
    "calculate_fov": True,
    "lat": 0.2281347875532986,
    "lon": 0.5432822498364406,
    "alt": 0.095,
    "host_type": "GroundFacility",
    "tx_power": 2.5e6,
    "tx_frequency": 1.5e9,
}


class TestFieldOfView(BaseTestCase):
    """Test observation of multiple objects in a field of view."""

    julian_date = JulianDate(2459006.5)
    clock = ScenarioClock(julian_date, 60.0, 30.0)
    conic_sensor_config = {
        "agent": SensorConfigObject(**CONIC_SENSOR_CONFIG),
        "realtime": True,
        "clock": clock,
    }
    conic_sensor_agent = SensingAgent.fromConfig(conic_sensor_config)
    conic_sensor_agent.sensors.host.time = ScenarioTime(30)

    CONIC_SENSOR_CONFIG["field_of_view"]["fov_shape"] = "rectangular"
    rectangular_sensor_config = {
        "agent": SensorConfigObject(**CONIC_SENSOR_CONFIG),
        "realtime": True,
        "clock": clock,
    }
    rectangular_sensor_agent = SensingAgent.fromConfig(rectangular_sensor_config)
    rectangular_sensor_agent.sensors.host.time = ScenarioTime(30)

    nominal_filter = UnscentedKalmanFilter(
        10001, 0.0, zeros((6,)), zeros((6, 6)), TwoBody(), zeros((6, 6)), StandardNis(0.01), None
    )
    primary_rso = EstimateAgent(
        10001,
        "Primary RSO",
        "Spacecraft",
        clock,
        array([26111.6, 33076.1, 0, -2.41152, 1.9074, 0]),
        zeros((6, 6)),
        nominal_filter,
        None,
        25.0,
        100.0,
        0.21,
    )
    secondary_rso = EstimateAgent(
        10002,
        "Secondary RSO",
        "Spacecraft",
        clock,
        array([26111.5, 33076.1, 0, -2.41153, 1.9074, 0]),
        zeros((6, 6)),
        nominal_filter,
        None,
        25.0,
        100.0,
        0.21,
    )

    def testCanSlew(self):
        """Test if you can slew to an RSO."""
        good_slant = array(
            [
                2.29494590e03,
                4.08271784e04,
                3.91179470e03,
                2.07249105e-04,
                -6.64332739e-05,
                2.16300407e-04,
            ]
        )
        val = self.conic_sensor_agent.sensors.canSlew(good_slant)
        assert bool(val) is True

    def testCheckTargetsInView(self):
        """Test if multiple targets are in the Field of View."""
        updateReductionParameters(self.julian_date)
        slant_range_sez = getSlantRangeVector(
            self.conic_sensor_agent.sensors.host.ecef_state, self.primary_rso.eci_state
        )
        agents = self.conic_sensor_agent.sensors.checkTargetsInView(
            slant_range_sez, [self.primary_rso, self.secondary_rso]
        )
        assert len(agents) == 2

    def testInFoV(self):
        """Test observations of two RSO with a single sensor at one time."""
        in_fov = self.conic_sensor_agent.sensors.inFOV(
            self.primary_rso.eci_state[:3], self.secondary_rso.eci_state[:3]
        )
        assert bool(in_fov) is True
        not_in_fov = self.conic_sensor_agent.sensors.inFOV(
            self.primary_rso.eci_state[:3], array([0, 0.01, 0])
        )
        assert bool(not_in_fov) is False

        rectangle_in_fov = self.rectangular_sensor_agent.sensors.inFOV(
            self.primary_rso.eci_state[:3], self.secondary_rso.eci_state[:3]
        )
        assert bool(rectangle_in_fov) is True
