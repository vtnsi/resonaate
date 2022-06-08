# pylint: disable=attribute-defined-outside-init, no-self-use
# Standard Library Imports
# Third Party Imports
# RESONAATE Imports
try:
    from resonaate.data.observation import Observation
except ImportError as error:
    raise Exception(
        "Please ensure you have appropriate packages installed:\n {0}".format(error)
    ) from error
# Testing Imports
from ..conftest import BaseTestCase


class TestObservationTable(BaseTestCase):
    """Test class for :class:`.Observation` database table class."""

    def testInit(self):
        """Test the init of Observation database table."""
        _ = Observation()

    def testInitKwargs(self):
        """Test initializing the kewards of the truth ephemeris table."""
        _ = Observation(
            sensor_type="Optical",
            unique_id=27020,
            observer="Sensor1",
            target_id=11111,
            target_name="Sat2",
            azimuth_rad=1.010036549841,
            elevation_rad=0.33006189181,
            range_km=0.0,
            range_rate_km_p_sec=0.0,
            julian_date=2458484.507891,
            timestampISO="2019-01-01T00:06:00.000Z",
            sez_state_s_km=-4957.659229144096,
            sez_state_e_km=7894.2462525123365,
            sez_state_z_km=3193.92927600744,
            position_lat_rad=0.44393147656176574,
            position_long_rad=1.124890532,
            position_altitude_km=0.6253
        )

    def testfromSEZVector(self):
        """Test initializing the kewards of the truth ephemeris table."""
        sez = [
            -4957.659229144096, 7894.2462525123365, 3193.9292760074436,
            1.7500003208790118, 3.931727930569842, -2.338646528282177
        ]
        _ = Observation.fromSEZVector(
            sensor_type="Optical",
            unique_id=27020,
            observer="Sensor1",
            target_id=11111,
            target_name="Sat2",
            azimuth_rad=1.010036549841,
            elevation_rad=0.33006189181,
            range_km=0.0,
            range_rate_km_p_sec=0.0,
            julian_date=2458484.507891,
            timestampISO="2019-01-01T00:06:00.000Z",
            sez=sez,
            sensor_position=[0.44393147656176574, 1.124890532, 0.6253]
        )
