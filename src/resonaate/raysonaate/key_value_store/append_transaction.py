"""Module implementing the 'append' key value store transaction."""

# Standard Library Imports
from collections.abc import MutableSequence

# Local Imports
from .transaction import Transaction


class AppendTransaction(Transaction):
    """Implements a transaction that appends a value to a specified key."""

    def transact(self, key_value_store: dict):
        """Append :attr:`.request_payload` to the value stored at :attr:`.key`.

        Args:
            key_value_store: The dictionary object being transacted on.

        See Also:
            :meth:`.KeyValueStore.appendValue()`.
        """
        existing_value = key_value_store.get(self.key)
        if existing_value:
            if isinstance(existing_value, MutableSequence):
                existing_value.append(self.request_payload)
            else:
                self.error = TypeError("Existing value is not a MutableSequence")
        else:
            key_value_store[self.key] = [self.request_payload]
        self.response_payload = key_value_store[self.key]
