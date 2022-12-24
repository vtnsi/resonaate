from __future__ import annotations

# Standard Library Imports
from copy import deepcopy
from dataclasses import asdict
from datetime import datetime

# Third Party Imports
import pytest
from sqlalchemy.orm import Query

# RESONAATE Imports
from resonaate.data.data_interface import Epoch
from resonaate.data.events import Event, EventScope
from resonaate.physics.time.stardate import datetimeToJulianDate
from resonaate.scenario.config.base import ConfigTypeError, ConfigValueError
from resonaate.scenario.config.event_configs import (
    DataDependency,
    EventConfig,
    EventConfigList,
    MissingDataDependency,
    ScheduledImpulseEventConfig,
)
from resonaate.scenario.config.time_config import TIME_STAMP_FORMAT


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
        with pytest.raises(MissingDataDependency):
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


class TestEventConfigClass:
    """."""

    def testEventConfig(self):
        """Test that EventConfig can be created from a dictionary."""

        class _TestEventConfig(EventConfig):
            """Test EventConfig."""

        with pytest.raises(ConfigValueError):
            _TestEventConfig(
                **{
                    "scope": "invalid",
                    "scope_instance_id": 0,
                    "start_time": "2020-01-01T00:00:00.000Z",
                    "end_time": "2020-01-02T00:00:00.000Z",
                    "event_type": "test_event",
                }
            )

        with pytest.raises(ConfigValueError):
            _TestEventConfig(
                **{
                    "scope": "agent_propagation",
                    "scope_instance_id": 0,
                    "start_time": "2020-01-01T00:00:00.000Z",
                    "end_time": None,
                    "event_type": "invalid",
                }
            )

        cfg = ScheduledImpulseEventConfig(
            scope="agent_propagation",
            scope_instance_id=0,
            start_time="2020-01-01T00:00:00.000Z",
            end_time=None,
            event_type="impulse",
            thrust_vector=[1.0, 0.0, 1.0],
            thrust_frame="ntw",
        )
        assert cfg.scope == EventScope.AGENT_PROPAGATION.value
        assert cfg.scope_instance_id == 0
        assert cfg.start_time == datetime.strptime("2020-01-01T00:00:00.000Z", TIME_STAMP_FORMAT)
        assert cfg.event_type == "impulse"

    def testEventConfigList(self):
        """."""
        cfg_dict = {
            "scope": "agent_propagation",
            "scope_instance_id": 0,
            "start_time": datetime.strptime("2020-01-01T00:00:00.000Z", TIME_STAMP_FORMAT),
            "end_time": datetime.strptime("2020-01-02T00:00:00.000Z", TIME_STAMP_FORMAT),
            "event_type": "impulse",
            "thrust_vector": [1.0, 0.0, 1.0],
            "thrust_frame": "ntw",
            "planned": True,
        }
        cfg_list = EventConfigList("events", EventConfig, [cfg_dict, deepcopy(cfg_dict)])
        assert len(cfg_list) == 2
        assert isinstance(cfg_list[0], EventConfig)
        assert asdict(cfg_list[0]) == cfg_dict

        event_cfg = ScheduledImpulseEventConfig(**cfg_dict)
        cfg_list = EventConfigList("events", EventConfig, [event_cfg])
        assert len(cfg_list) == 1

        event_cfg_dict = deepcopy(cfg_dict)
        event_cfg_dict["event_type"] = "invalid"
        with pytest.raises(ConfigValueError):
            _ = ScheduledImpulseEventConfig(**event_cfg_dict)

        with pytest.raises(ConfigTypeError):
            _ = EventConfigList("events", EventConfig, [{}], default_empty=True)

        cfg_list = EventConfigList("events", EventConfig, [], default_empty=True)
        assert len(cfg_list) == 0
