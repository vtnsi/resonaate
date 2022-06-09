# pylint: disable=unused-argument
# Standard Library Imports
from datetime import datetime
from json import dumps

# Third Party Imports
import pytest

try:
    # RESONAATE Imports
    from resonaate.data.data_interface import Agent
    from resonaate.data.events import TargetAdditionEvent
    from resonaate.physics.time.stardate import datetimeToJulianDate
    from resonaate.scenario.config.base import ConfigError
    from resonaate.scenario.config.event_configs import TargetAdditionEventConfigObject
except ImportError as error:
    raise Exception(f"Please ensure you have appropriate packages installed:\n {error}") from error
# Local Imports
# Testing Imports
from ...conftest import BaseTestCase


class TestTargetAdditionEventConfig(BaseTestCase):
    """Test class for :class:`.TargetAdditionEventConfig` class."""

    def testInitGoodArgs(self):
        """Test :class:`.TargetAdditionEventConfig` constructor with good arguments."""
        assert TargetAdditionEventConfigObject(
            {
                "scope": TargetAdditionEvent.INTENDED_SCOPE.value,
                "scope_instance_id": 123,
                "start_time": datetime(2021, 8, 3, 12),
                "event_type": TargetAdditionEvent.EVENT_TYPE,
                "sat_num": 12345,
                "sat_name": "new satellite",
                "init_eci": [0, 1, 2, 3, 4, 5],
                "station_keeping": {},
                "tasking_engine_id": 123,
            }
        )

    def testInitOtherGoodArgs(self):
        """Test :class:`.TargetAdditionEventConfig` constructor with other good arguments."""
        assert TargetAdditionEventConfigObject(
            {
                "scope": TargetAdditionEvent.INTENDED_SCOPE.value,
                "scope_instance_id": 123,
                "start_time": datetime(2021, 8, 3, 12),
                "event_type": TargetAdditionEvent.EVENT_TYPE,
                "sat_num": 12345,
                "sat_name": "new satellite",
                "init_coe": {
                    "sma": 10000,
                    "ecc": 0.00,
                    "inc": 10.0,
                    "raan": 100.0,
                    "arg_p": 1.0,
                    "true_anom": 1.0,
                },
                "station_keeping": {},
                "tasking_engine_id": 123,
            }
        )

    def testInitNoState(self):
        """Test :class:`.TargetAdditionEventConfig` constructor with no state configuration."""
        sat_num = 12345
        expected_err = f"Target {sat_num}: State not specified:"
        with pytest.raises(ConfigError, match=expected_err):
            _ = TargetAdditionEventConfigObject(
                {
                    "scope": TargetAdditionEvent.INTENDED_SCOPE.value,
                    "scope_instance_id": 123,
                    "start_time": datetime(2021, 8, 3, 12),
                    "event_type": TargetAdditionEvent.EVENT_TYPE,
                    "sat_num": sat_num,
                    "sat_name": "new satellite",
                    "station_keeping": {},
                    "tasking_engine_id": 123,
                }
            )

    def testInitDuplicateState(self):
        """Test :class:`.TargetAdditionEventConfig` constructor with duplicate state configurations."""
        sat_num = 12345
        expected_err = f"Target {sat_num}: Duplicate state specified:"
        with pytest.raises(ConfigError, match=expected_err):
            _ = TargetAdditionEventConfigObject(
                {
                    "scope": TargetAdditionEvent.INTENDED_SCOPE.value,
                    "scope_instance_id": 123,
                    "start_time": datetime(2021, 8, 3, 12),
                    "event_type": TargetAdditionEvent.EVENT_TYPE,
                    "sat_num": sat_num,
                    "sat_name": "new satellite",
                    "init_eci": [0, 1, 2, 3, 4, 5],
                    "init_coe": {
                        "sma": 10000,
                        "ecc": 0.01,
                        "inc": 10.0,
                        "raan": 100.0,
                        "arg_p": 1.0,
                        "true_anomaly": 1.0,
                    },
                    "station_keeping": {},
                    "tasking_engine_id": 123,
                }
            )

    def testInitBadECIState(self):
        """Test :class:`.TargetAdditionEventConfig` constructor with a bad initial ECI state."""
        bad_eci = [0, 1, 2]
        expected_err = f"ECI vector should have 6 elements, not {len(bad_eci)}"
        with pytest.raises(ConfigError, match=expected_err):
            _ = TargetAdditionEventConfigObject(
                {
                    "scope": TargetAdditionEvent.INTENDED_SCOPE.value,
                    "scope_instance_id": 123,
                    "start_time": datetime(2021, 8, 3, 12),
                    "event_type": TargetAdditionEvent.EVENT_TYPE,
                    "sat_num": 12345,
                    "sat_name": "new satellite",
                    "init_eci": bad_eci,
                    "station_keeping": {},
                    "tasking_engine_id": 123,
                }
            )

    def testDataDependency(self):
        """Test that :class:`.TargetAdditionEventConfig`'s data dependencies are correct."""
        addition_config = TargetAdditionEventConfigObject(
            {
                "scope": TargetAdditionEvent.INTENDED_SCOPE.value,
                "scope_instance_id": 123,
                "start_time": datetime(2021, 8, 3, 12),
                "event_type": TargetAdditionEvent.EVENT_TYPE,
                "sat_num": 12345,
                "sat_name": "new satellite",
                "init_eci": [0, 1, 2, 3, 4, 5],
                "station_keeping": {},
                "tasking_engine_id": 123,
            }
        )
        addition_dependencies = addition_config.getDataDependencies()
        assert len(addition_dependencies) == 1

        agent_dependency = addition_dependencies[0]
        assert agent_dependency.data_type == Agent
        assert agent_dependency.attributes == {
            "unique_id": addition_config.sat_num,
            "name": addition_config.sat_name,
        }


class TestTargetAdditionEvent(BaseTestCase):
    """Test class for :class:`.TargetAdditionEvent` class."""

    def testFromConfig(self):
        """Test :meth:`.TargetAdditionEvent.fromConfig()`."""
        addition_config = TargetAdditionEventConfigObject(
            {
                "scope": TargetAdditionEvent.INTENDED_SCOPE.value,
                "scope_instance_id": 123,
                "start_time": datetime(2021, 8, 3, 12),
                "event_type": TargetAdditionEvent.EVENT_TYPE,
                "sat_num": 12345,
                "sat_name": "new satellite",
                "init_eci": [0, 1, 2, 3, 4, 5],
                "station_keeping": {},
                "tasking_engine_id": 123,
            }
        )
        addition_event = TargetAdditionEvent.fromConfig(addition_config)
        assert addition_event.eci == addition_config.init_eci
        assert (
            addition_event.station_keeping["routines"] == addition_config.station_keeping.routines
        )

    def testHandleEvent(self, mocked_scenario):
        """Test :meth:`.TargetAdditionEvent.handleEvent()`."""
        agent_obj = Agent(unique_id=12345, name="additional sat")
        impulse_event = TargetAdditionEvent(
            scope=TargetAdditionEvent.INTENDED_SCOPE.value,
            scope_instance_id=123,
            start_time_jd=datetimeToJulianDate(datetime(2021, 8, 3, 12)),
            end_time_jd=datetimeToJulianDate(datetime(2021, 8, 3, 12)),
            event_type=TargetAdditionEvent.EVENT_TYPE,
            tasking_engine_id=123,
            agent=agent_obj,
            pos_x_km=0,
            pos_y_km=1,
            pos_z_km=2,
            vel_x_km_p_sec=3,
            vel_y_km_p_sec=4,
            vel_z_km_p_sec=5,
            station_keeping_json=dumps([]),
        )
        impulse_event.handleEvent(mocked_scenario)
