"""Defines Interferometer Sensor unit test."""

from __future__ import annotations

# RESONAATE Imports
from resonaate.sensors.interferometer import Interferometer


def testSensorInit(interferometer_sensor_args: dict):
    """Test interferometer sensor initialization.

    Args:
        interferometer_sensor_args(``dict``): arguments to interferometer init.
    """
    interfereometer = Interferometer(**interferometer_sensor_args)
    assert interfereometer
