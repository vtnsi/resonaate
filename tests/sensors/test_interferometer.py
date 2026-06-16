"""Defines Interferometer Sensor unit test."""

from __future__ import annotations

# Standard Library Imports
from unittest.mock import create_autospec

# Third Party Imports
import numpy as np

# RESONAATE Imports
from resonaate.agents.sensing_agent import SensingAgent
from resonaate.common.labels import Explanation, PlatformLabel
from resonaate.physics.constants import DEG2RAD
from resonaate.physics.time.stardate import JulianDate, julianDateToDatetime
from resonaate.physics.transforms.methods import ecef2eci, getSlantRangeVector, lla2ecef
from resonaate.scenario.config.sensor_config import NodeConfig
from resonaate.sensors.field_of_view import ConicFoV
from resonaate.sensors.interferometer import Interferometer


def testSensorInit(interferometer_sensor_args):
    """Interferometer constructs."""
    assert Interferometer(**interferometer_sensor_args)


def testArrayFovRejectsDistantAntenna(interferometer_sensor_args):
    """A secondary antenna distant from the host cant see an overhead target, so the array FOV check returns not visible."""
    utc = julianDateToDatetime(JulianDate(2459486.09964))

    interferometer_sensor_args["field_of_view"] = ConicFoV(cone_angle=2.0 * DEG2RAD)
    interferometer_sensor_args["a_baseline_node"] = NodeConfig(
        name="NEAR",
        latitude=37.2,
        longitude=-80.41,
        altitude=0.6,
    )
    interferometer_sensor_args["c_baseline_node"] = NodeConfig(
        name="FAR",
        latitude=37.2,
        longitude=-70.41,
        altitude=0.6,
    )
    interferometer = Interferometer(**interferometer_sensor_args)

    # Host on the ground; target 1000 km straight up from it
    lla = np.array([37.2 * DEG2RAD, -80.41 * DEG2RAD, 0.6])
    host_ecef = lla2ecef(lla)
    host_eci = ecef2eci(host_ecef, utc)

    host = create_autospec(spec=SensingAgent, instance=True)
    host.agent_type = PlatformLabel.GROUND_FACILITY
    host.julian_date_epoch = JulianDate(2459486.09964)
    host.datetime_epoch = utc
    host.eci_state = host_eci
    host.ecef_state = host_ecef
    interferometer.host = host

    radial = host_eci[:3] / np.linalg.norm(host_eci[:3])
    target = np.concatenate([host_eci[:3] + 1000.0 * radial, np.zeros(3)])
    slant = getSlantRangeVector(host_eci, target, utc)

    visible, reason = interferometer.isVisible(target, 0.0, 0.0, slant)

    assert not visible
    assert reason == Explanation.FIELD_OF_VIEW
