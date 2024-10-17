from __future__ import annotations

# Standard Library Imports
from datetime import datetime

# Third Party Imports
import pytest
from sqlalchemy.orm import Query

# RESONAATE Imports
from resonaate.data.data_interface import Epoch
from resonaate.data.events import Event
from resonaate.physics.time.stardate import datetimeToJulianDate
from resonaate.scenario.config.event_configs import DataDependency, MissingDataDependencyError


class TestBaseEventClass:
    """Test class for :class:`.Event` database table class."""

    def testInit(self):
        """Test the init of Event database table."""
        _ = Event()

    def testInitKwargs(self):
        """Test initializing the kewards of the table."""
        _ = Event(
            scope="test_scope",
            scope_instance_id=12345,
            start_time_jd=datetimeToJulianDate(datetime(2018, 12, 1, 12, 5)),
            end_time_jd=datetimeToJulianDate(datetime(2018, 12, 1, 12, 5)),
            event_type="test_event",
        )

    def testEventTypes(self):
        """Test :meth:`.Event.eventTypes()`."""
        assert Event.eventTypes()

    def testChildEventChecks(self):
        """Test to make sure a good child event doesn't throw any errors."""

        class TestChild(Event):
            __abstract__ = True

            EVENT_TYPE = "test_event"

            def handleEvent(self, scope_instance):
                pass

            @classmethod
            def fromConfig(cls, config):
                pass

        Event.EVENT_REGISTRY = None
        assert Event.eventTypes()

        # make `TestChild.EVENT_TYPE` bad
        orig_type = TestChild.EVENT_TYPE
        del TestChild.EVENT_TYPE

        # re-run child class checking
        Event.EVENT_REGISTRY = None
        with pytest.raises(AttributeError):
            _ = Event.eventTypes()

        # reset `TestChild.EVENT_TYPE`
        TestChild.EVENT_TYPE = orig_type

        # make `TestChild.handleEvent` bad
        orig_func = TestChild.handleEvent
        del TestChild.handleEvent

        # re-run child class checking
        Event.EVENT_REGISTRY = None
        with pytest.raises(AttributeError):
            _ = Event.eventTypes()

        # reset `TestChild.handleEvent`
        TestChild.handleEvent = orig_func

        # make `TestChild.fromConfig` bad
        orig_func = TestChild.fromConfig
        del TestChild.fromConfig

        # re-run child class checking
        Event.EVENT_REGISTRY = None
        with pytest.raises(AttributeError):
            _ = Event.eventTypes()

        # reset `TestChild.fromConfig`
        TestChild.fromConfig = orig_func


class TestDataDependency:
    """Test class for the :class:`.DataDependency` class."""

    def testNoAttributes(self):
        """Test a :class:`.DataDependency` with no ``attributes``."""
        dep = DataDependency(Epoch, Query([Epoch]))
        with pytest.raises(MissingDataDependencyError):
            dep.createDependency()

    def testWithAttributes(self):
        """Test a :class:`.DataDependency` with no ``attributes``."""
        timestamp = datetime(2021, 8, 3, 12)
        dep = DataDependency(
            Epoch,
            Query([Epoch]),
            {
                "julian_date": datetimeToJulianDate(timestamp),
                "timestampISO": timestamp.isoformat(timespec="microseconds"),
            },
        )
        created_dep = dep.createDependency()
        assert isinstance(created_dep, Epoch)
        assert created_dep.julian_date == datetimeToJulianDate(timestamp)
        assert created_dep.timestampISO == timestamp.isoformat(timespec="microseconds")
