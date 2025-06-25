# RESONAATE Imports
from resonaate.parallel.key_value_store.append_transaction import AppendTransaction
from resonaate.parallel.key_value_store.pop_transaction import PopTransaction


def testAppendTransaction():
    """Test basic use of the :class:`.AppendTransaction`."""
    test_dict = {"foo": ["bar", "baz"]}
    trans = AppendTransaction("foo", "box")
    trans.transact(test_dict)
    assert test_dict["foo"][-1] == "box"


def testAppendTransaction_noExisting():
    """Test use of :class:`.AppendTransaction` if there's no existing value at specified key."""
    test_dict = {}
    trans = AppendTransaction("foo", "bar")
    trans.transact(test_dict)
    assert test_dict["foo"] == ["bar"]


def testAppendTransaction_existingNonSequence():
    """Test use of :class:`.AppendTransaction` if the existing value isn't a mutable sequence."""
    test_dict = {"foo": 123}
    trans = AppendTransaction("foo", "bar")
    trans.transact(test_dict)
    assert test_dict["foo"] == 123
    assert trans.error is not None


def testPopTransaction():
    """Test basic use of the :class:`.PopTransaction`."""
    test_dict = {"foo": ["bar", "baz"]}
    trans = PopTransaction("foo")
    trans.transact(test_dict)
    assert len(test_dict["foo"]) == 1
    assert trans.response_payload == "baz"


def testPopTransaction_customIndex():
    """Test basic use of the :class:`.PopTransaction`."""
    test_dict = {"foo": ["bar", "baz"]}
    trans = PopTransaction("foo", 0)
    trans.transact(test_dict)
    assert len(test_dict["foo"]) == 1
    assert trans.response_payload == "bar"


def testPopTransaction_noExisting():
    """Test use of :class:`.PopTransaction` if there's no existing value at specified key."""
    test_dict = {}
    trans = PopTransaction("foo")
    trans.transact(test_dict)
    assert trans.error is None
    assert trans.response_payload is None


def testPopTransaction_existingNonSequence():
    """Test use of :class:`.PopTransaction` if the existing value isn't a mutable sequence."""
    test_dict = {"foo": 123}
    trans = PopTransaction("foo")
    trans.transact(test_dict)
    assert trans.response_payload is None
    assert trans.error is not None
