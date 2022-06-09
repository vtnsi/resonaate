# pylint: disable=unused-argument
# Standard Library Imports
from datetime import datetime
from unittest.mock import create_autospec

# Third Party Imports
import pytest

try:
    # RESONAATE Imports
    from resonaate.agents.target_agent import TargetAgent
    from resonaate.data.events import EventScope, ScheduledFiniteManeuverEvent
    from resonaate.physics.time.stardate import datetimeToJulianDate
    from resonaate.scenario.config.base import ConfigError
    from resonaate.scenario.config.event_configs import ScheduledFiniteManeuverConfigObject
except ImportError as error:
    raise Exception(f"Please ensure you have appropriate packages installed:\n {error}") from error
# Local Imports
# Testing Imports
from ...conftest import BaseTestCase


class TestFiniteManeuverEventConfig(BaseTestCase):
    """Test class for :class:`.ScheduledFiniteThrustEventConfig` class."""

    def testInitGoodArgs(self):
        """Test :class:`.ScheduledFiniteThrustEventConfig` constructor with good arguments."""
        assert ScheduledFiniteManeuverConfigObject(
            {
                "scope": ScheduledFiniteManeuverConfigObject.EVENT_CLASS.INTENDED_SCOPE.value,
                "scope_instance_id": 28868,
                "start_time": datetime(2019, 2, 1, 15, 20),
                "end_time": datetime(2019, 2, 1, 15, 22),
                "event_type": ScheduledFiniteManeuverConfigObject.EVENT_CLASS.EVENT_TYPE,
                "maneuver_mag": 0.002,
                "maneuver_type": "spiral",
                "planned": True,
            }
        )

    def testInitBadScope(self):
        """Test :class:`.ScheduledFiniteThrustEventConfig` constructor with bad ``scope`` argument."""
        event = ScheduledFiniteManeuverEvent
        scope = ScheduledFiniteManeuverEvent.INTENDED_SCOPE
        expected_err = f"{event} must have scope set to {scope}"
        with pytest.raises(ConfigError, match=expected_err):
            ScheduledFiniteManeuverConfigObject(
                {
                    "scope": EventScope.SCENARIO_STEP.value,  # pylint: disable=no-member
                    "scope_instance_id": 28868,
                    "start_time": datetime(2019, 2, 1, 15, 20),
                    "end_time": datetime(2019, 2, 1, 15, 22),
                    "event_type": ScheduledFiniteManeuverEvent.EVENT_TYPE,
                    "maneuver_mag": 0.002,
                    "maneuver_type": "spiral",
                    "planned": True,
                }
            )

    def testInitBadThrustType(self):
        """Test :class:`.ScheduledFiniteThrustEventConfig` constructor with bad ``applied_bias`` type."""
        with pytest.raises(ConfigError):
            ScheduledFiniteManeuverConfigObject(
                {
                    "scope": ScheduledFiniteManeuverConfigObject.EVENT_CLASS.INTENDED_SCOPE.value,
                    "scope_instance_id": 28868,
                    "start_time": datetime(2019, 2, 1, 15, 20),
                    "end_time": datetime(2019, 2, 1, 15, 22),
                    "event_type": ScheduledFiniteManeuverConfigObject.EVENT_CLASS.EVENT_TYPE,
                    "maneuver_mag": 0.002,
                    "maneuver_type": True,
                    "planned": False,
                }
            )


@pytest.fixture(name="mocked_target")
def getMockedAgent():
    """Get mocked :class:`.TargetAgent` object."""
    mocked_target = create_autospec(TargetAgent)
    mocked_target.julian_date_start = datetimeToJulianDate(datetime(2019, 2, 1, 0, 0))
    return mocked_target


class TestFiniteThrustEvent(BaseTestCase):
    """Test class for :class:`.ScheduledFiniteThrustEvent` class."""

    def testFromConfig(self):
        """Test :meth:`.ScheduledFiniteThrustEvent.fromConfig()`."""
        maneuver_config = ScheduledFiniteManeuverConfigObject(
            {
                "scope": ScheduledFiniteManeuverEvent.INTENDED_SCOPE.value,
                "scope_instance_id": 28868,
                "start_time": datetime(2019, 2, 1, 15, 20),
                "end_time": datetime(2019, 2, 1, 15, 22),
                "event_type": ScheduledFiniteManeuverEvent.EVENT_TYPE,
                "maneuver_mag": 0.002,
                "maneuver_type": "spiral",
                "planned": True,
            }
        )
        assert ScheduledFiniteManeuverEvent.fromConfig(maneuver_config)

    def testHandleEventSpiral(self, mocked_target):
        """Test :meth:`.ScheduledFiniteThrustEvent.handleEvent()` with a spiral maneuver."""
        maneuver_event = ScheduledFiniteManeuverEvent(
            scope=ScheduledFiniteManeuverEvent.INTENDED_SCOPE.value,
            scope_instance_id=28868,
            start_time_jd=datetimeToJulianDate(datetime(2019, 2, 1, 15, 20)),
            end_time_jd=datetimeToJulianDate(datetime(2019, 2, 1, 15, 22)),
            event_type=ScheduledFiniteManeuverEvent.EVENT_TYPE,
            maneuver_mag=0.002,
            maneuver_type="spiral",
            planned=True,
        )
        maneuver_event.handleEvent(mocked_target)

    def testHandleEventPlaneChange(self, mocked_target):
        """Test :meth:`.ScheduledFiniteThrustEvent.handleEvent()` with a plane change maneuver."""
        maneuver_event = ScheduledFiniteManeuverEvent(
            scope=ScheduledFiniteManeuverEvent.INTENDED_SCOPE.value,
            scope_instance_id=28868,
            start_time_jd=datetimeToJulianDate(datetime(2019, 2, 1, 15, 20)),
            end_time_jd=datetimeToJulianDate(datetime(2019, 2, 1, 15, 22)),
            event_type=ScheduledFiniteManeuverEvent.EVENT_TYPE,
            maneuver_mag=0.002,
            maneuver_type="plane_change",
            planned=True,
        )
        maneuver_event.handleEvent(mocked_target)

    def testHandleEventBadType(self, mocked_target):
        """Test :meth:`.ScheduledFiniteThrustEvent.handleEvent()` with a bad thrust type."""
        maneuver_event = ScheduledFiniteManeuverEvent(
            scope=ScheduledFiniteManeuverEvent.INTENDED_SCOPE.value,
            scope_instance_id=28868,
            start_time_jd=datetimeToJulianDate(datetime(2019, 2, 1, 15, 20)),
            end_time_jd=datetimeToJulianDate(datetime(2019, 2, 1, 15, 22)),
            event_type=ScheduledFiniteManeuverEvent.EVENT_TYPE,
            maneuver_mag=0.002,
            maneuver_type="bad",
            planned=True,
        )
        expected_err = f"{maneuver_event.maneuver_type} is not a valid thrust type."
        with pytest.raises(ValueError, match=expected_err):
            maneuver_event.handleEvent(mocked_target)
