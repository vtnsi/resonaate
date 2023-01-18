from __future__ import annotations

# Standard Library Imports
import re
from copy import deepcopy
from dataclasses import asdict, dataclass, field
from typing import TYPE_CHECKING
from unittest.mock import patch

# Third Party Imports
import pytest

# RESONAATE Imports
from resonaate.scenario.config.base import (
    ConfigError,
    ConfigMissingRequiredError,
    ConfigObject,
    ConfigObjectList,
    ConfigSettingError,
    ConfigTypeError,
    ConfigValueError,
    inclusiveRange,
)

# Type Checking Imports
if TYPE_CHECKING:
    # Standard Library Imports
    from typing import Any


def testConfigError():
    """Make sure the ConfigError class works properly."""
    label = "test_label"
    msg = "This is a Config error!"
    err = ConfigError(config_label=label, message=msg)

    expected = f"Error occurred in {label!r}: {msg}"
    assert str(err) == expected
    with pytest.raises(ConfigError, match=re.escape(expected)):
        raise err


@patch.multiple(ConfigSettingError, __abstractmethods__=set())
def testConfigSettingError():
    """Make sure the ConfigSettingError class works properly."""
    # pylint: disable=abstract-class-instantiated
    label = "test_label"
    setting = 45  # supposed to be a list or tuple
    requirements = (
        list,
        tuple,
    )
    err = ConfigSettingError(config_label=label, bad_setting=setting, requirements=requirements)

    assert err.requirements == requirements
    assert err.bad_setting == setting
    assert err.config_label == label


def testConfigTypeError():
    """Make sure the ConfigTypeError class works properly."""
    label = "test_label"
    setting = "supposed to be an int"
    requirements = (int,)
    err = ConfigTypeError(config_label=label, bad_setting=setting, requirements=requirements)

    expected = f"Setting {label!r} must be in types {requirements}, not {type(setting)}"
    assert str(err) == expected
    with pytest.raises(ConfigTypeError, match=re.escape(expected)):
        raise err


def testConfigValueError():
    """Make sure the ConfigValueError class works properly."""
    label = "test_label"
    setting = -1.0
    requirements = "greater than 0"
    err = ConfigValueError(config_label=label, bad_setting=setting, requirements=requirements)

    expected = f"Setting {setting!r} for {label!r} is not a valid setting: {requirements}"
    assert str(err) == expected
    with pytest.raises(ConfigValueError, match=re.escape(expected)):
        raise err


def testConfigMissingRequiredError():
    """Make sure the ConfigMissingRequiredError class works properly."""
    label = "test_label"
    missing = "missing_field"
    err = ConfigMissingRequiredError(config_label=label, missing=missing)

    expected = f"Missing required {missing!r} in {label!r} config"
    assert str(err) == expected
    with pytest.raises(ConfigMissingRequiredError, match=re.escape(expected)):
        raise err


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
    """``int``: Required setting of integer field."""

    str_field: str
    """``str``: Required setting of string field."""

    bool_field: bool
    """``bool``: Required setting of boolean field."""

    option_field: float = 0.0
    """``float``: Optional setting of float field with 0.0 default"""


@dataclass
class _ExtendedConfig(_TestConfigObject):
    """An extended :class:`.ConfigObject` for testing more complex fields."""

    optional_dict: dict = field(default_factory=dict)
    """``dict``: Optional dictionary setting with {} default."""


@dataclass
class _AllRequired(ConfigObject):
    req_field_1: int
    req_field_2: str


@dataclass
class _AllOptional(ConfigObject):
    opt_field_1: int = 10
    opt_field_2: str = "this is optional"


@pytest.fixture(name="test_config_dict")
def getTestConfigDict() -> dict[str, Any]:
    """Returns the config dict for a simple test object."""
    return {
        "int_field": 123,
        "str_field": "abc",
        "bool_field": True,
    }


def testConfigObject(test_config_dict: dict[str, Any]):
    """Test basic functionality of the :class:`.ConfigObject` class."""
    # Test equality and id
    test_obj1 = _TestConfigObject(**test_config_dict)
    test_obj2 = _TestConfigObject(**test_config_dict)
    assert test_obj1 == test_obj2
    assert test_obj1 is not test_obj2

    # Use default value for `option_field`
    config_dict = deepcopy(test_config_dict)
    test_obj = _TestConfigObject(**config_dict)
    assert test_obj.int_field == config_dict["int_field"]
    assert test_obj.str_field == config_dict["str_field"]
    assert test_obj.bool_field == config_dict["bool_field"]
    assert test_obj.option_field == 0.0

    # Use custom value for `option_field`
    config_dict = deepcopy(test_config_dict)
    config_dict["option_field"] = 10.0
    test_obj = _TestConfigObject(**config_dict)
    assert test_obj.int_field == config_dict["int_field"]
    assert test_obj.str_field == config_dict["str_field"]
    assert test_obj.bool_field == config_dict["bool_field"]
    assert test_obj.option_field == config_dict["option_field"]


def testExtendedConfig(test_config_dict: dict[str, Any]):
    """Test functionality of the :class:`.ConfigObject` class with a non-basic field type."""
    # Use default factory
    config_dict = deepcopy(test_config_dict)
    expected = {}
    test_obj = _ExtendedConfig(**config_dict)
    assert isinstance(test_obj.optional_dict, dict)
    assert test_obj.optional_dict == expected

    # Use non-default value, but empty
    config_dict = deepcopy(test_config_dict)
    expected = {}
    config_dict["optional_dict"] = expected
    test_obj = _ExtendedConfig(**config_dict)
    assert isinstance(test_obj.optional_dict, dict)
    assert test_obj.optional_dict == expected

    # Use non-default, non-empty value
    config_dict = deepcopy(test_config_dict)
    expected = {
        "key1": "value1",
        "key2": 1932721,
    }
    config_dict["optional_dict"] = expected
    test_obj = _ExtendedConfig(**config_dict)
    assert isinstance(test_obj.optional_dict, dict)
    assert test_obj.optional_dict == expected


def testRequiredAndOptionalFields():
    """Test the getRequiredFields & getOptionalFields methods."""
    # Test required & optional fields
    assert len(_TestConfigObject.getRequiredFields()) == 3
    assert len(_TestConfigObject.getOptionalFields()) == 1

    assert len(_ExtendedConfig.getRequiredFields()) == 3
    assert len(_ExtendedConfig.getOptionalFields()) == 2

    # Test all-required config
    assert len(_AllRequired.getRequiredFields()) == 2
    assert len(_AllRequired.getOptionalFields()) == 0

    # Test all-required config
    assert len(_AllOptional.getRequiredFields()) == 0
    assert len(_AllOptional.getOptionalFields()) == 2


def testConfigObjectList(test_config_dict: dict[str, Any]):
    """Test basic functionality of the :class:`.ConfigObjectList` class."""
    test_obj1 = _TestConfigObject(**test_config_dict)
    test_obj2 = _TestConfigObject(**test_config_dict)

    object_list = ConfigObjectList("test_list", _TestConfigObject, [test_obj1, test_obj2])
    assert object_list
    for obj_list_item, test_obj in zip(object_list, (test_obj1, test_obj2)):
        assert obj_list_item == test_obj
        assert obj_list_item is test_obj

    input_list_dicts = [deepcopy(test_config_dict), deepcopy(test_config_dict)]
    object_list = ConfigObjectList(
        "test_list", _TestConfigObject, input_list_dicts, default_empty=False
    )
    assert object_list
    for obj_list_item, test_dict in zip(object_list, input_list_dicts):
        # [NOTE]: Need to add the optional field b/c the `asdict()` outputs it
        test_dict.update({"option_field": 0.0})
        assert asdict(obj_list_item) == test_dict
        # The `asdict()` returns a new dictionary object
        assert asdict(obj_list_item) is not test_dict

    # Test __getitem__(), __len__()
    item1, item2 = object_list[0], object_list[1]
    assert isinstance(item1, _TestConfigObject)
    assert isinstance(item2, _TestConfigObject)
    assert len(object_list) == 2

    # Test removing all items
    # pylint: disable=protected-access
    object_list._config_objects = []
    with pytest.raises(ConfigMissingRequiredError):
        _ = object_list.config_objects

    with pytest.raises(ConfigMissingRequiredError):
        list_item = ConfigObjectList("test_list", _TestConfigObject, [])

    with pytest.raises(ConfigMissingRequiredError):
        list_item = ConfigObjectList("test_list", _TestConfigObject, [{}])

    with pytest.raises(ConfigTypeError):
        list_item = ConfigObjectList("test_list", _TestConfigObject, "bad")

    with pytest.raises(ConfigTypeError):
        list_item = ConfigObjectList("test_list", _TestConfigObject, ["bad1", "bad2"])

    with pytest.raises(ConfigTypeError):
        list_item = ConfigObjectList("test_list", _TestConfigObject, [[], []])

    config_list = [{"int_field": 123, "str_field": "abc", "bool_field": True}]
    list_item = ConfigObjectList("test_list", _TestConfigObject, config_list)
    assert list_item.required

    for item in list_item.config_objects:
        assert isinstance(item, _TestConfigObject)
        assert item.int_field == config_list[0]["int_field"]
        assert item.str_field == config_list[0]["str_field"]
        assert item.bool_field == config_list[0]["bool_field"]


def testConfigObjectListDefaultEmpty(test_config_dict: dict[str, Any]):
    """Validate that :class:`.ConfigObjectList` methods don't throw errors when list is allowed to be empty."""
    conf_list = ConfigObjectList("list_label", _TestConfigObject, [], default_empty=True)
    assert not conf_list.config_objects

    with pytest.raises(ConfigMissingRequiredError):
        _ = ConfigObjectList("list_label", _TestConfigObject, [], default_empty=False)

    test_obj1 = _TestConfigObject(**test_config_dict)
    test_obj2 = _TestConfigObject(**test_config_dict)
    conf_list = ConfigObjectList(
        "list_label", _TestConfigObject, [test_obj1, test_obj2], default_empty=True
    )
    assert conf_list.config_objects
