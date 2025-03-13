# Standard Library Imports
from json import dump
from pickle import PickleError, loads
from time import time_ns
# Package Imports
from .transaction import Transaction


def _default(obj):
    if isinstance(obj, bytes):
        try:
            loaded = loads(obj)
        except PickleError:
            loaded = obj.decode(encoding="utf-8")
        return loaded


class DumpTransaction(Transaction):
    """Dump the contents of the key value store to a JSON file."""

    DUMP_FILENAME = "kvs_dump_{0}.json"

    def __init__(self):
        super(DumpTransaction, self).__init__(None)

    def transact(self, key_value_store):
        file_name = self.DUMP_FILENAME.format(time_ns())
        with open(file_name, 'w') as dump_file:
            dump(key_value_store, dump_file, default=_default, indent=2)
