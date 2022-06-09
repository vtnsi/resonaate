# Standard Library Imports
from abc import ABCMeta
from copy import deepcopy
# Third Party Imports
import pytest
# RESONAATE Imports
try:
    from resonaate.scenario.config.base import (ConfigSection, ConfigOption, ConfigObject, ConfigObjectList,
                                                ConfigError, ConfigTypeError, ConfigValueError,
                                                ConfigMissingRequiredError, NO_SETTING, inclusiveRange)
except ImportError as error:
    raise Exception(
        f"Please ensure you have appropriate packages installed:\n {error}"
    ) from error


def testBasicConfigOption():
    """Test basic constructor of a :class:`.ConfigOption`."""
    test_option = ConfigOption("test_item", (int, ))
    assert not test_option.nested_items


def testConfigOptionBadDefault():
    """Test :class:`.ConfigOption` with bad default settings."""
    expected_err = r"Setting .* must be in types .*, not .*"
    with pytest.raises(ConfigTypeError, match=expected_err):
        _ = ConfigOption("test_item", (int, ), default="abc")

    expected_err = r"Setting .* for .* is not a valid setting: .*"
    with pytest.raises(ConfigValueError, match=expected_err):
        _ = ConfigOption("test_item", (int, ), default=6, valid_settings=range(5))


def testConfigOptionValidation():
    """Test basic functionality of a :class:`.ConfigOption`'s setting validation."""
    test_item = ConfigOption("test_item", (int, ), default=0, valid_settings=range(10))

    assert test_item.setting == 0

    test_item.readConfig(5)
    assert test_item.setting == 5

    with pytest.raises(ConfigTypeError):
        test_item.readConfig("abc")

    with pytest.raises(ConfigValueError):
        test_item.readConfig(11)


def testConfigOptionRequired():
    """Test required functionality of :class:`.ConfigOption`."""
    required_item = ConfigOption("required", (int, ))
    assert required_item.isRequired()
    expected_err = r"Missing required .* in .* config"
    with pytest.raises(ConfigMissingRequiredError, match=expected_err):
        _ = required_item.setting


def testNoSettingDeepcopy():
    """Validate that `.NO_SETTING` cannot be copied."""
    assert NO_SETTING is deepcopy(NO_SETTING)


def testInclusiveRange():
    """Validate that the :meth:`.inclusiveRange()` method works as intended."""
    assert inclusiveRange(5) == range(5 + 1)
    assert inclusiveRange(1, 5) == range(1, 5 + 1)
    assert inclusiveRange(1, 5, 2) == range(1, 5 + 1, 2)

    with pytest.raises(TypeError):
        inclusiveRange()
    with pytest.raises(TypeError):
        inclusiveRange(0, 1, 2, 3)


class TestSection(ConfigSection, metaclass=ABCMeta):
    """Abstract base class for :class:`.ConfigSection` test fixtures to inherit from."""

    @property
    def nested_items(self):
        """list: List of nested :class:`.ConfigItem`s."""
        return [self._int_option, self._str_option, self._bool_option]  # pylint: disable=no-member

    @property
    def int_option(self):
        """int: Setting of integer option."""
        return self._int_option.setting  # pylint: disable=no-member

    @property
    def str_option(self):
        """str: Setting of string option."""
        return self._str_option.setting  # pylint: disable=no-member

    @property
    def bool_option(self):
        """bool: Setting of boolean option."""
        return self._bool_option.setting  # pylint: disable=no-member


@pytest.fixture(name="basic_test_section")
def getBasicTestSection():
    """Return an initialized :class:`.TestSection` that has default options."""
    class BasicTestSection(TestSection):
        def __init__(self):
            self._int_option = ConfigOption("int_option", (int, ), default=0)
            self._str_option = ConfigOption("str_option", (str, ), default="foo")
            self._bool_option = ConfigOption("bool_option", (bool, ), default=False)

    return BasicTestSection()


@pytest.fixture(name="required_test_section")
def getRequiredTestSection():
    """Return an initialized :class:`.TestSection` that has required options."""
    class RequiredTestSection(TestSection):
        def __init__(self):
            self._int_option = ConfigOption("int_option", (int, ))
            self._str_option = ConfigOption("str_option", (str, ))
            self._bool_option = ConfigOption("bool_option", (bool, ))

    return RequiredTestSection()


def testBasicConfigSection(basic_test_section):
    """Test the expected base functionality of a :class:`.BasicTestSection`."""
    assert basic_test_section.int_option == 0
    assert basic_test_section.str_option == "foo"
    assert basic_test_section.bool_option is False
    assert basic_test_section.isRequired() is False

    config_dict = {
        "int_option": 5,
        "str_option": "bar",
        "bool_option": True
    }
    basic_test_section.readConfig(config_dict)

    assert basic_test_section.int_option == config_dict["int_option"]
    assert basic_test_section.str_option == config_dict["str_option"]
    assert basic_test_section.bool_option == config_dict["bool_option"]


def testRequiredConfigSection(required_test_section):
    """Test the expected functionality of a :class:`.RequiredTestSection`."""
    assert required_test_section.isRequired() is True
    with pytest.raises(ConfigMissingRequiredError):
        _ = required_test_section.int_option

    incomplete_config = {
        "int_option": 5,
        "str_option": "bar"
    }
    with pytest.raises(ConfigMissingRequiredError):
        required_test_section.readConfig(incomplete_config)

    config_dict = {
        "int_option": 5,
        "str_option": "bar",
        "bool_option": True
    }
    required_test_section.readConfig(config_dict)

    assert required_test_section.int_option == config_dict["int_option"]
    assert required_test_section.str_option == config_dict["str_option"]
    assert required_test_section.bool_option == config_dict["bool_option"]


class _TestConfigObject(ConfigObject):
    """Generic :class:`.ConfigObject` for testing."""

    @staticmethod
    def getFields():
        """Returns a tuple of :class:`.ConfigOption`s defining the fields required for a :class:`.TestConfigObject`."""
        return (
            ConfigOption("int_field", (int, )),
            ConfigOption("str_field", (str, )),
            ConfigOption("bool_field", (bool, ))
        )

    @property
    def int_field(self):
        """int: Setting of integer field."""
        return self._int_field.setting  # pylint: disable=no-member

    @property
    def str_field(self):
        """str: Setting of string field."""
        return self._str_field.setting  # pylint: disable=no-member

    @property
    def bool_field(self):
        """bool: Setting of boolean field."""
        return self._bool_field.setting  # pylint: disable=no-member


def testConfigObject():
    """Test basic functionality of the :class:`.ConfigObject` class."""
    config_dict = {
        "int_field": 123,
        "str_field": "abc",
        "bool_field": True
    }
    test_obj = _TestConfigObject(config_dict)
    assert test_obj.int_field == config_dict["int_field"]
    assert test_obj.str_field == config_dict["str_field"]
    assert test_obj.bool_field == config_dict["bool_field"]


def testConfigObjectList():
    """Test basic functionality of the :class:`.ConfigObjectList` class."""
    list_item = ConfigObjectList("test_list", _TestConfigObject)
    assert list_item.isRequired() is True

    with pytest.raises(ConfigMissingRequiredError):
        _ = list_item.objects

    with pytest.raises(ConfigError):
        list_item.readConfig([{}])

    with pytest.raises(ConfigMissingRequiredError):
        list_item.readConfig([])

    with pytest.raises(ConfigTypeError):
        list_item.readConfig("bad")

    with pytest.raises(ConfigTypeError):
        list_item.readConfig([[], []])

    config_list = [{
        "int_field": 123,
        "str_field": "abc",
        "bool_field": True
    }]
    list_item.readConfig(config_list)
    for item in list_item.objects:
        assert isinstance(item, _TestConfigObject)
        assert item.int_field == config_list[0]["int_field"]
        assert item.str_field == config_list[0]["str_field"]
        assert item.bool_field == config_list[0]["bool_field"]


def testConfigObjectListDefaultEmpty():
    """Validate that :class:`.ConfigObjectList` methods don't throw errors when list is allowed to be empty."""
    conf_list = ConfigObjectList("list_label", _TestConfigObject, default_empty=True)
    conf_list.readConfig([])
    assert not conf_list.nested_items
    assert not conf_list.objects


class _TestConfigSection(ConfigSection):
    """:class:`.ConfigSection` for testing nested :class:`.ConfigObjectList`."""

    def __init__(self):
        """Construct an instance of a :class:`.TestConfigSection`."""
        self._list_option = ConfigObjectList("list_option", _TestConfigObject, default_empty=True)

    @property
    def nested_items(self):
        """list: List of nested :class:`.ConfigItem`s."""
        return [self._list_option]


def testReadConfigSectionWithList():
    """Test the integration of the :class:`.ConfigObjectList` with a :class:`.ConfigSection`."""
    test_config = _TestConfigSection()
    test_config.readConfig({})  # shouldn't throw error since `default_empty` flag is True

    config_section = {
        "list_option": [
            {
                "int_field": 123,
                "str_field": "abc",
                "bool_field": True
            },
            {
                "int_field": 456,
                "str_field": "def",
                "bool_field": False
            }
        ]
    }
    test_config.readConfig(config_section)
