# pylint: disable=unused-argument
# Standard Library Imports
from datetime import datetime
from json import dumps

# Third Party Imports
import pytest

try:
    # RESONAATE Imports
    from resonaate.data.data_interface import Agent
    from resonaate.data.events import SensorAdditionEvent
    from resonaate.physics.time.stardate import datetimeToJulianDate
    from resonaate.physics.transforms.reductions import updateReductionParameters
    from resonaate.scenario.config.base import ConfigError
    from resonaate.scenario.config.event_configs import SensorAdditionEventConfigObject
except ImportError as error:
    raise Exception(f"Please ensure you have appropriate packages installed:\n {error}") from error
# Local Imports
# Testing Imports
from ...conftest import BaseTestCase


class TestSensorAdditionEventConfig(BaseTestCase):
    """Test class for :class:`.SensorAdditionEventConfig` class."""

    def testInitGoodArgs(self):
        """Test :class:`.SensorAdditionEventConfig` constructor with good arguments."""
        assert SensorAdditionEventConfigObject(
            {
                "scope": SensorAdditionEvent.INTENDED_SCOPE.value,
                "scope_instance_id": 123,
                "start_time": datetime(2021, 8, 3, 12),
                "event_type": SensorAdditionEvent.EVENT_TYPE,
                "tasking_engine_id": 123,
                "name": "Test Optical",
                "id": 100000,
                "covariance": [[2.388200571127795e-11, 0.0], [0.0, 2.388200571127795e-11]],
                "slew_rate": 0.2617993877991494,
                "azimuth_range": [0.0, 6.283185132646661],
                "elevation_range": [0.0, 1.5707961522619713],
                "efficiency": 0.98,
                "aperture_area": 0.8107319665559964,
                "sensor_type": "Optical",
                "exemplar": [0.0014320086173409336, 32500.0],
                "field_of_view": 15.0,
                "lat": 0.1,
                "lon": 1.1,
                "alt": 1.0,
                "host_type": "GroundFacility",
            }
        )

    def testInitOtherGoodArgs(self):
        """Test :class:`.SensorAdditionEventConfig` constructor with other good arguments."""
        assert SensorAdditionEventConfigObject(
            {
                "scope": SensorAdditionEvent.INTENDED_SCOPE.value,
                "scope_instance_id": 123,
                "start_time": datetime(2021, 8, 3, 12),
                "event_type": SensorAdditionEvent.EVENT_TYPE,
                "tasking_engine_id": 123,
                "name": "Test Sensor 1",
                "id": 50001,
                "covariance": [[9.869604401089358e-14, 0.0], [0.0, 9.869604401089358e-14]],
                "slew_rate": 0.04363323129985824,
                "azimuth_range": [0.0, 6.283185132646661],
                "elevation_range": [-1.5707961522619713, 1.5707961522619713],
                "efficiency": 0.99,
                "aperture_area": 0.031415926535897934,
                "sensor_type": "Optical",
                "init_eci": [
                    -6997.811593501495,
                    63.69359356853797,
                    -447.53287804600023,
                    0.48666918798751624,
                    1.0600865385159703,
                    -7.448488839044817,
                ],
                "exemplar": [1, 36000],
                "field_of_view": 15.0,
                "host_type": "Spacecraft",
                "station_keeping": {"routines": ["LEO"]},
            }
        )

    def testInitNoState(self):
        """Test :class:`.SensorAdditionEventConfig` constructor with no state configuration."""
        sensor_num = 12345
        expected_err = f"Sensor {sensor_num}: State not specified:"
        with pytest.raises(ConfigError, match=expected_err):
            _ = SensorAdditionEventConfigObject(
                {
                    "scope": SensorAdditionEvent.INTENDED_SCOPE.value,
                    "scope_instance_id": 123,
                    "start_time": datetime(2021, 8, 3, 12),
                    "event_type": SensorAdditionEvent.EVENT_TYPE,
                    "tasking_engine_id": 123,
                    "name": "Test Optical",
                    "id": sensor_num,
                    "covariance": [[2.388200571127795e-11, 0.0], [0.0, 2.388200571127795e-11]],
                    "slew_rate": 0.2617993877991494,
                    "azimuth_range": [0.0, 6.283185132646661],
                    "elevation_range": [0.0, 1.5707961522619713],
                    "efficiency": 0.98,
                    "aperture_area": 0.8107319665559964,
                    "sensor_type": "Optical",
                    "exemplar": [0.0014320086173409336, 32500.0],
                    "field_of_view": 15.0,
                    "host_type": "GroundFacility",
                }
            )

    def testInitDuplicateState(self):
        """Test :class:`.SensorAdditionEventConfig` constructor with duplicate state configurations."""
        sensor_num = 12345
        expected_err = f"Sensor {sensor_num}: Duplicate state specified:"
        with pytest.raises(ConfigError, match=expected_err):
            _ = SensorAdditionEventConfigObject(
                {
                    "scope": SensorAdditionEvent.INTENDED_SCOPE.value,
                    "scope_instance_id": 123,
                    "start_time": datetime(2021, 8, 3, 12),
                    "event_type": SensorAdditionEvent.EVENT_TYPE,
                    "tasking_engine_id": 123,
                    "name": "Test Optical",
                    "id": sensor_num,
                    "covariance": [[2.388200571127795e-11, 0.0], [0.0, 2.388200571127795e-11]],
                    "slew_rate": 0.2617993877991494,
                    "azimuth_range": [0.0, 6.283185132646661],
                    "elevation_range": [0.0, 1.5707961522619713],
                    "efficiency": 0.98,
                    "aperture_area": 0.8107319665559964,
                    "sensor_type": "Optical",
                    "exemplar": [0.0014320086173409336, 32500.0],
                    "field_of_view": 15.0,
                    "lat": 0.1,
                    "lon": 1.1,
                    "alt": 1.0,
                    "init_eci": [
                        -6997.811593501495,
                        63.69359356853797,
                        -447.53287804600023,
                        0.48666918798751624,
                        1.0600865385159703,
                        -7.448488839044817,
                    ],
                    "host_type": "GroundFacility",
                }
            )

    def testInitBadECIState(self):
        """Test :class:`.SensorAdditionEventConfig` constructor with a bad initial ECI state."""
        bad_eci = [0, 1, 2]
        expected_err = f"ECI vector should have 6 elements, not {len(bad_eci)}"
        with pytest.raises(ConfigError, match=expected_err):
            _ = SensorAdditionEventConfigObject(
                {
                    "scope": SensorAdditionEvent.INTENDED_SCOPE.value,
                    "scope_instance_id": 123,
                    "start_time": datetime(2021, 8, 3, 12),
                    "event_type": SensorAdditionEvent.EVENT_TYPE,
                    "tasking_engine_id": 123,
                    "name": "Test Sensor 1",
                    "id": 50001,
                    "covariance": [[9.869604401089358e-14, 0.0], [0.0, 9.869604401089358e-14]],
                    "slew_rate": 0.04363323129985824,
                    "azimuth_range": [0.0, 6.283185132646661],
                    "elevation_range": [-1.5707961522619713, 1.5707961522619713],
                    "efficiency": 0.99,
                    "aperture_area": 0.031415926535897934,
                    "sensor_type": "Optical",
                    "init_eci": bad_eci,
                    "exemplar": [1, 36000],
                    "field_of_view": 15.0,
                    "host_type": "Spacecraft",
                    "station_keeping": {"routines": ["LEO"]},
                }
            )

    def testInitRadarNoTx(self):
        """Test :class:`.SensorAdditionEventConfig` constructor with no transmit info for a radar."""
        sensor_num = 12345
        expected_err = f"Sensor {sensor_num}: Radar transmit parameters not set:"
        with pytest.raises(ConfigError, match=expected_err):
            _ = SensorAdditionEventConfigObject(
                {
                    "scope": SensorAdditionEvent.INTENDED_SCOPE.value,
                    "scope_instance_id": 123,
                    "start_time": datetime(2021, 8, 3, 12),
                    "event_type": SensorAdditionEvent.EVENT_TYPE,
                    "tasking_engine_id": 123,
                    "name": "Test Sensor 1",
                    "id": sensor_num,
                    "covariance": [[9.869604401089358e-14, 0.0], [0.0, 9.869604401089358e-14]],
                    "slew_rate": 0.04363323129985824,
                    "azimuth_range": [0.0, 6.283185132646661],
                    "elevation_range": [-1.5707961522619713, 1.5707961522619713],
                    "efficiency": 0.99,
                    "aperture_area": 0.031415926535897934,
                    "sensor_type": "Radar",
                    "init_eci": [
                        -6997.811593501495,
                        63.69359356853797,
                        -447.53287804600023,
                        0.48666918798751624,
                        1.0600865385159703,
                        -7.448488839044817,
                    ],
                    "exemplar": [1, 36000],
                    "field_of_view": 15.0,
                    "host_type": "Spacecraft",
                    "station_keeping": {"routines": ["LEO"]},
                }
            )

    def testInitGroundFacilityWithStationKeeping(self):
        """Test :class:`.SensorAdditionEventConfig` constructor with station keeping set for a ground facility."""
        expected_err = "Ground based sensors cannot perform station keeping"
        with pytest.raises(ConfigError, match=expected_err):
            _ = SensorAdditionEventConfigObject(
                {
                    "scope": SensorAdditionEvent.INTENDED_SCOPE.value,
                    "scope_instance_id": 123,
                    "start_time": datetime(2021, 8, 3, 12),
                    "event_type": SensorAdditionEvent.EVENT_TYPE,
                    "tasking_engine_id": 123,
                    "name": "Test Optical",
                    "id": 100000,
                    "covariance": [[2.388200571127795e-11, 0.0], [0.0, 2.388200571127795e-11]],
                    "slew_rate": 0.2617993877991494,
                    "azimuth_range": [0.0, 6.283185132646661],
                    "elevation_range": [0.0, 1.5707961522619713],
                    "efficiency": 0.98,
                    "aperture_area": 0.8107319665559964,
                    "sensor_type": "Optical",
                    "exemplar": [0.0014320086173409336, 32500.0],
                    "field_of_view": 15.0,
                    "lat": 0.1,
                    "lon": 1.1,
                    "alt": 1.0,
                    "host_type": "GroundFacility",
                    "station_keeping": {"routines": ["LEO"]},
                }
            )

    def testDataDependency(self):
        """Test that :class:`.SensorAdditionEventConfig`'s data dependencies are correct."""
        addition_config = SensorAdditionEventConfigObject(
            {
                "scope": SensorAdditionEvent.INTENDED_SCOPE.value,
                "scope_instance_id": 123,
                "start_time": datetime(2021, 8, 3, 12),
                "event_type": SensorAdditionEvent.EVENT_TYPE,
                "tasking_engine_id": 123,
                "name": "Test Optical",
                "id": 100000,
                "covariance": [[2.388200571127795e-11, 0.0], [0.0, 2.388200571127795e-11]],
                "slew_rate": 0.2617993877991494,
                "azimuth_range": [0.0, 6.283185132646661],
                "elevation_range": [0.0, 1.5707961522619713],
                "efficiency": 0.98,
                "aperture_area": 0.8107319665559964,
                "sensor_type": "Optical",
                "exemplar": [0.0014320086173409336, 32500.0],
                "field_of_view": 15.0,
                "lat": 0.1,
                "lon": 1.1,
                "alt": 1.0,
                "host_type": "GroundFacility",
            }
        )
        addition_dependencies = addition_config.getDataDependencies()
        assert len(addition_dependencies) == 1

        agent_dependency = addition_dependencies[0]
        assert agent_dependency.data_type == Agent
        assert agent_dependency.attributes == {
            "unique_id": addition_config.id,
            "name": addition_config.name,
        }


class TestSensorAdditionEvent(BaseTestCase):
    """Test class for :class:`.SensorAdditionEvent` class."""

    def testFromConfig(self):
        """Test :meth:`.SensorAdditionEvent.fromConfig()`."""
        addition_config = SensorAdditionEventConfigObject(
            {
                "scope": SensorAdditionEvent.INTENDED_SCOPE.value,
                "scope_instance_id": 123,
                "start_time": datetime(2019, 8, 3, 12),
                "event_type": SensorAdditionEvent.EVENT_TYPE,
                "tasking_engine_id": 123,
                "name": "Test Optical",
                "id": 100000,
                "covariance": [[2.388200571127795e-11, 0.0], [0.0, 2.388200571127795e-11]],
                "slew_rate": 0.2617993877991494,
                "azimuth_range": [0.0, 6.283185132646661],
                "elevation_range": [0.0, 1.5707961522619713],
                "efficiency": 0.98,
                "aperture_area": 0.8107319665559964,
                "sensor_type": "Optical",
                "exemplar": [0.0014320086173409336, 32500.0],
                "field_of_view": 15.0,
                "lat": 0.1,
                "lon": 1.1,
                "alt": 1.0,
                "host_type": "GroundFacility",
            }
        )
        updateReductionParameters(datetimeToJulianDate(addition_config.start_time))
        assert SensorAdditionEvent.fromConfig(addition_config)

    def testHandleEvent(self, mocked_scenario):
        """Test :meth:`.SensorAdditionEvent.handleEvent()`."""
        agent_obj = Agent(unique_id=12345, name="additional sensor")
        impulse_event = SensorAdditionEvent(
            scope=SensorAdditionEvent.INTENDED_SCOPE,
            scope_instance_id=123,
            start_time_jd=datetimeToJulianDate(datetime(2021, 8, 3, 12)),
            end_time_jd=datetimeToJulianDate(datetime(2021, 8, 3, 12)),
            event_type=SensorAdditionEvent.EVENT_TYPE,
            tasking_engine_id=123,
            agent=agent_obj,
            host_type="GroundFacility",
            pos_x_km=0,
            pos_y_km=1,
            pos_z_km=2,
            vel_x_km_p_sec=3,
            vel_y_km_p_sec=4,
            vel_z_km_p_sec=5,
            azimuth_min=0,
            azimuth_max=1,
            elevation_min=0,
            elevation_max=1,
            covariance_json=dumps([[2.388200571127795e-11, 0.0], [0.0, 2.388200571127795e-11]]),
            aperture_area=0.8107319665559964,
            efficiency=0.98,
            slew_rate=0.2617993877991494,
            sensor_type="Optical",
            exemplar_cross_section=0.0014320086173409336,
            exemplar_range=32500.0,
            station_keeping_json=dumps([]),
        )
        impulse_event.handleEvent(mocked_scenario)
