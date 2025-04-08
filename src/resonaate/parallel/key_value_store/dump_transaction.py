"""Module implementing the dump transaction."""

from __future__ import annotations

# Standard Library Imports
from json import dump
from time import time_ns

# Local Imports
from .transaction import Transaction


class DumpTransaction(Transaction):
    """Transaction encapsulating the dumping of the key value store construct."""

    def __init__(self, dump_filename: str | None = None):
        """Initialize a :class:`.DumpTransaction`.

        Args:
            dump_filename: Path to file to dump key value store contents to.
        """
        super().__init__(None)
        self.dump_filename = dump_filename
        if self.dump_filename is None:
            self.dump_filename = self.default_filename

    @property
    def default_filename(self) -> str:
        """Return a default file name to dump to."""
        return f"kvs_dump_{time_ns()}.json"

    def transact(self, key_value_store):
        """Write the contents of `key_value_store` to the specified file.

        Args:
            key_value_store: The dictionary object being transacted upon.

        See Also:
            :meth:`.KeyValueStore.dump()`.
        """
        with open(self.dump_filename, "w") as dump_file:
            dump(key_value_store, dump_file, indent=2)
