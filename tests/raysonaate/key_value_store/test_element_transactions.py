# RESONAATE Imports
from resonaate.parallel.key_value_store.get_transaction import GetTransaction
from resonaate.parallel.key_value_store.set_transaction import SetTransaction


def testSetTransaction():
    """Test basic use of the :class:`.SetTransaction`."""
    test_dict = {}
    set_trans = SetTransaction("foo", "bar")
    set_trans.transact(test_dict)
    assert test_dict["foo"] == "bar"


def testSetTransaction_alreadySet():
    """Test use of the :class:`.SetTransaction` when there's already a value set."""
    test_dict = {"foo": "bar"}
    set_trans = SetTransaction("foo", "baz")
    set_trans.transact(test_dict)
    assert test_dict["foo"] == "baz"


def testGetTransaction():
    """Test basic us of the :class:`.GetTransaction`."""
    test_dict = {"foo": "bar"}
    get_trans = GetTransaction("foo")
    get_trans.transact(test_dict)
    assert get_trans.response_payload == "bar"


def testGetTransaction_noValue():
    """Test use of the :class:`.GetTransaction` when a value hasn't been set."""
    test_dict = {}
    get_trans = GetTransaction("foo")
    get_trans.transact(test_dict)
    assert get_trans.response_payload is None
