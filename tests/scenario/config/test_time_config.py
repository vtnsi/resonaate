from __future__ import annotations

# Standard Library Imports
from copy import deepcopy
from dataclasses import fields
from datetime import datetime
from typing import TYPE_CHECKING

# Third Party Imports
import pytest

# RESONAATE Imports
from resonaate.scenario.config.base import ConfigValueError
from resonaate.scenario.config.time_config import DEFAULT_TIME_STEP, TIME_STAMP_FORMAT, TimeConfig

# Type Checking Imports
if TYPE_CHECKING:
    # Standard Library Imports
    from typing import Any


TEST_START_TIMESTAMP = "2020-01-01T00:00:00.000Z"
TEST_STOP_TIMESTAMP = "2020-01-02T00:00:00.000Z"


@pytest.fixture(name="time_cfg_dict")
def getTimeConfig() -> dict:
    """Generate the default TimeConfig dictionary."""
    return {
        "start_timestamp": TEST_START_TIMESTAMP,
        "stop_timestamp": TEST_STOP_TIMESTAMP,
        "physics_step_sec": DEFAULT_TIME_STEP,
        "output_step_sec": DEFAULT_TIME_STEP,
    }


def testCreateTimeConfig(time_cfg_dict: dict):
    """Test that TimeConfig can be created from a dictionary."""
    dt_start = datetime.strptime(TEST_START_TIMESTAMP, TIME_STAMP_FORMAT)
    dt_stop = datetime.strptime(TEST_STOP_TIMESTAMP, TIME_STAMP_FORMAT)
    time_cfg = TimeConfig(**time_cfg_dict)
    assert time_cfg.CONFIG_LABEL == "time"
    assert time_cfg.start_timestamp == dt_start
    assert time_cfg.stop_timestamp == dt_stop
    assert time_cfg.physics_step_sec == DEFAULT_TIME_STEP
    assert time_cfg.output_step_sec == DEFAULT_TIME_STEP

    # Enter dates as datetimes, rather than strings
    cfg_dict = deepcopy(time_cfg_dict)
    cfg_dict["start_timestamp"] = datetime.strptime(cfg_dict["start_timestamp"], TIME_STAMP_FORMAT)
    cfg_dict["stop_timestamp"] = datetime.strptime(cfg_dict["stop_timestamp"], TIME_STAMP_FORMAT)
    time_cfg = TimeConfig(**cfg_dict)
    assert time_cfg.start_timestamp == dt_start
    assert time_cfg.stop_timestamp == dt_stop

    assert time_cfg is not None
    for field in fields(TimeConfig):
        assert field.name in time_cfg.__dict__
        assert getattr(time_cfg, field.name) is not None

    # Test that this can be created from an empty dictionary
    with pytest.raises(TypeError):
        TimeConfig(**{})

    # Ensure the correct amount of req/opt keys
    assert len(TimeConfig.getRequiredFields()) == 2
    assert len(TimeConfig.getOptionalFields()) == 2


def testInputValues(time_cfg_dict: dict):
    """Test bad input values to TimeConfig."""
    cfg_dict = deepcopy(time_cfg_dict)
    cfg_dict["physics_step_sec"] = -1
    with pytest.raises(ConfigValueError):
        TimeConfig(**cfg_dict)

    cfg_dict = deepcopy(time_cfg_dict)
    cfg_dict["physics_step_sec"] = 0
    with pytest.raises(ConfigValueError):
        TimeConfig(**cfg_dict)

    cfg_dict = deepcopy(time_cfg_dict)
    cfg_dict["output_step_sec"] = -1
    with pytest.raises(ConfigValueError):
        TimeConfig(**cfg_dict)

    cfg_dict = deepcopy(time_cfg_dict)
    cfg_dict["output_step_sec"] = 0
    with pytest.raises(ConfigValueError):
        TimeConfig(**cfg_dict)

    cfg_dict = deepcopy(time_cfg_dict)
    cfg_dict["stop_timestamp"] = cfg_dict["start_timestamp"]
    with pytest.raises(ConfigValueError):
        TimeConfig(**cfg_dict)
