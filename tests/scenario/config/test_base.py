# Standard Library Imports
from copy import deepcopy
from dataclasses import dataclass

# Third Party Imports
import pytest

try:
    # RESONAATE Imports
    from resonaate.scenario.config.base import (
        ConfigMissingRequiredError,
        ConfigObject,
        ConfigObjectList,
        ConfigTypeError,
        inclusiveRange,
    )
except ImportError as error:
    raise Exception(f"Please ensure you have appropriate packages installed:\n {error}") from error


def testInclusiveRange():
    """Validate that the :meth:`.inclusiveRange()` method works as intended."""
    assert inclusiveRange(5) == range(5 + 1)
    assert inclusiveRange(1, 5) == range(1, 5 + 1)
    assert inclusiveRange(1, 5, 2) == range(1, 5 + 1, 2)

    with pytest.raises(TypeError):
        inclusiveRange()
    with pytest.raises(TypeError):
        inclusiveRange(0, 1, 2, 3)


@dataclass
class _TestConfigObject(ConfigObject):
    """Generic :class:`.ConfigObject` for testing."""

    int_field: int
    """int: Setting of integer field."""

    str_field: str
    """str: Setting of string field."""

    bool_field: bool
    """bool: Setting of boolean field."""

    option_field: float = 0.0


TEST_CONFIG_OBJECT_DICT = {
    "int_field": 123,
    "str_field": "abc",
    "bool_field": True,
}


def testConfigObject():
    """Test basic functionality of the :class:`.ConfigObject` class."""
    config_dict = deepcopy(TEST_CONFIG_OBJECT_DICT)
    test_obj = _TestConfigObject(**config_dict)
    assert test_obj.int_field == config_dict["int_field"]
    assert test_obj.str_field == config_dict["str_field"]
    assert test_obj.bool_field == config_dict["bool_field"]
    assert test_obj.option_field == 0.0

    config_dict = deepcopy(TEST_CONFIG_OBJECT_DICT)
    config_dict["option_field"] = 10.0
    test_obj = _TestConfigObject(**config_dict)
    assert test_obj.int_field == config_dict["int_field"]
    assert test_obj.str_field == config_dict["str_field"]
    assert test_obj.bool_field == config_dict["bool_field"]
    assert test_obj.option_field == config_dict["option_field"]

    assert len(_TestConfigObject.getRequiredSections()) == 3
    assert len(_TestConfigObject.getOptionalSections()) == 1


def testConfigObjectList():
    """Test basic functionality of the :class:`.ConfigObjectList` class."""
    with pytest.raises(ConfigMissingRequiredError):
        list_item = ConfigObjectList("test_list", _TestConfigObject, [])

    with pytest.raises(ConfigMissingRequiredError):
        list_item = ConfigObjectList("test_list", _TestConfigObject, [{}])

    with pytest.raises(ConfigTypeError):
        list_item = ConfigObjectList("test_list", _TestConfigObject, "bad")

    with pytest.raises(ConfigTypeError):
        list_item = ConfigObjectList("test_list", _TestConfigObject, [[], []])

    config_list = [{"int_field": 123, "str_field": "abc", "bool_field": True}]
    list_item = ConfigObjectList("test_list", _TestConfigObject, config_list)
    assert list_item.required

    # list_item.readConfig(config_list)
    for item in list_item.config_objects:
        assert isinstance(item, _TestConfigObject)
        assert item.int_field == config_list[0]["int_field"]
        assert item.str_field == config_list[0]["str_field"]
        assert item.bool_field == config_list[0]["bool_field"]


def testConfigObjectListDefaultEmpty():
    """Validate that :class:`.ConfigObjectList` methods don't throw errors when list is allowed to be empty."""
    conf_list = ConfigObjectList("list_label", _TestConfigObject, [], default_empty=True)
    assert not conf_list.config_objects
