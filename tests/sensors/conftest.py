from __future__ import annotations

# Standard Library Imports
from copy import deepcopy

# Third Party Imports
import numpy as np
import pytest

# RESONAATE Imports
from resonaate.physics.constants import DEG2RAD
from resonaate.physics.measurements import Measurement
from resonaate.scenario.config.sensor_config import NodeConfig
from resonaate.sensors.field_of_view import ConicFoV


@pytest.fixture(name="base_sensor_args")
def getSensorArgs() -> dict:
    """Create dictionary of valid arguments to Sensor init."""
    r_matrix = np.diag((1.0e-4, 2.5e-5))
    return {
        "measurement": Measurement.fromMeasurementLabels(
            ["azimuth_rad", "elevation_rad"],
            r_matrix,
        ),
        "az_mask": np.array((0.0, 360.0)),
        "el_mask": np.array((0.0, 90.0)),
        "r_matrix": r_matrix,
        "efficiency": 0.95,
        "slew_rate": 1.0,
        "field_of_view": {"fov_shape": "conic"},
        "background_observations": True,
        "minimum_range": 0.0,
        "maximum_range": np.inf,
    }


@pytest.fixture(name="optical_sensor_args")
def getOpticalSensorArgs() -> dict:
    """Create dictionary of valid arguments to Optical init."""
    return {
        "az_mask": np.array((0.0, 360.0)),
        "el_mask": np.array((0.0, 90.0)),
        "r_matrix": np.diag((1.0e-4, 2.5e-5)),
        "diameter": 10,
        "efficiency": 0.95,
        "slew_rate": 1.0,
        "field_of_view": {"fov_shape": "conic"},
        "background_observations": True,
        "detectable_vismag": 20.0,
        "minimum_range": 0.0,
        "maximum_range": np.inf,
    }


@pytest.fixture(name="radar_sensor_args")
def getRadarSensorArgs(base_sensor_args: dict) -> dict:
    """Create dictionary of valid arguments to Radar init."""
    radar_sensor_args = deepcopy(base_sensor_args)
    radar_sensor_args["diameter"] = 10.0
    radar_sensor_args["tx_power"] = 2.5e6
    radar_sensor_args["tx_frequency"] = 1.5e9
    radar_sensor_args["min_detectable_power"] = 1.0e-15
    radar_sensor_args["r_matrix"] = np.ones(
        4,
    )
    del radar_sensor_args["measurement"]
    return radar_sensor_args


@pytest.fixture(name="interferometer_sensor_args")
def getInterferometerSensorArgs(base_sensor_args: dict) -> dict:
    """Create dictionary of valid arguments to Interferometer Init."""
    interferometer_sensor_args = deepcopy(base_sensor_args)
    del interferometer_sensor_args["measurement"]
    interferometer_sensor_args["field_of_view"] = ConicFoV(cone_angle=2.0 * DEG2RAD)
    interferometer_sensor_args["azimuth_baseline_node"] = NodeConfig(
        name="az",
        latitude=0.0,
        longitude=0.0,
        altitude=0.0,
    )
    interferometer_sensor_args["elevation_baseline_node"] = NodeConfig(
        name="el",
        latitude=0.0,
        longitude=0.0,
        altitude=0.0,
    )
    return interferometer_sensor_args
