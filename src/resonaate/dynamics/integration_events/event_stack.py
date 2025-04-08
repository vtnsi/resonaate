"""Encapsulation of event tracking using ``strmbrkr`` with a :class:`.EventRecord` and :class:`.EventStack`."""

from __future__ import annotations

# Standard Library Imports
import logging
from collections import defaultdict
from json import dumps, loads

# Local Imports
from ...parallel.key_value_store import KeyValueStore


class EventRecord:
    """Record of an event that took place."""

    def __init__(self, event_type, performer):
        """Instantiate a :class:`.EventRecord` object.

        Args:
            event_type (str): String describing the event.
            performer (int): Unique identifier for the object that's performing the event.
        """
        self.event_type = event_type
        self.performer = performer

    def serialize(self):
        """Return a serialized string representation of this :class:`.EventRecord`."""
        return dumps({"event_type": self.event_type, "performer": self.performer})

    @classmethod
    def fromSerial(cls, serial):
        """Return a :class:`.EventRecord` object based on the specified `serial` string.

        Args:
            serial (str): Serialized string representation of a :class:`.EventRecord`.

        Returns:
            EventRecord: Based on the specified `serial` string.
        """
        _dict = loads(serial)
        return cls(_dict["event_type"], _dict["performer"])


class EventStack:
    """Encapsulation of event tracking using ``strmbrkr``."""

    EVENT_STACK_LOCATION = "event_stack"
    """str: :class:`.KeyValueStore` key where state change events are recorded."""

    @classmethod
    def pushEvent(cls, event_record):
        """Record the specified `event_record`.

        Args:
            event_record (EventRecord): Object describing the event that took place.
        """
        KeyValueStore.appendValue(cls.EVENT_STACK_LOCATION, event_record.serialize())

    @classmethod
    def logAndFlushEvents(cls):
        """Pop all events off of the stack and log the number of each event type there are."""
        popped_event = KeyValueStore.popValue(cls.EVENT_STACK_LOCATION, 0)
        event_buckets = defaultdict(list)
        while popped_event:
            event_record = EventRecord.fromSerial(popped_event)
            event_buckets[event_record.event_type].append(event_record.performer)

            popped_event = KeyValueStore.popValue(cls.EVENT_STACK_LOCATION, 0)

        logger = logging.getLogger("resonaate")
        for event_type, bucket in event_buckets.items():
            msg1 = f"{len(bucket)} events of type {event_type} performed."
            logger.info(msg1)
            msg2 = f"Performers: {bucket}"
            logger.debug(msg2)
