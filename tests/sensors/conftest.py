from __future__ import annotations

# Standard Library Imports
from copy import deepcopy

# Third Party Imports
import numpy as np
import pytest

# RESONAATE Imports
from resonaate.physics.measurements import Measurement


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
        "diameter": 10,
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
    radar_sensor_args["tx_power"] = 2.5e6
    radar_sensor_args["tx_frequency"] = 1.5e9
    radar_sensor_args["min_detectable_power"] = 1.0e-15
    radar_sensor_args["r_matrix"] = np.ones(
        4,
    )
    del radar_sensor_args["measurement"]
    return radar_sensor_args
