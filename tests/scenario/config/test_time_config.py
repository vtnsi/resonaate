from __future__ import annotations

# Standard Library Imports
from copy import deepcopy
from datetime import datetime

# Third Party Imports
import pytest
from pydantic import ValidationError

# RESONAATE Imports
from resonaate.scenario.config.time_config import DEFAULT_TIME_STEP, TimeConfig

TEST_START = datetime(2020, 1, 1)
TEST_STOP = datetime(2020, 1, 2)


@pytest.fixture(name="time_cfg_dict")
def getTimeConfig() -> dict:
    """Generate the default TimeConfig dictionary."""
    return {
        "start_timestamp": TEST_START,
        "stop_timestamp": TEST_STOP,
        "physics_step_sec": DEFAULT_TIME_STEP,
        "output_step_sec": DEFAULT_TIME_STEP,
    }


def testCreateTimeConfig(time_cfg_dict: dict):
    """Test that TimeConfig can be created from a dictionary."""
    time_cfg = TimeConfig(**time_cfg_dict)
    assert time_cfg.start_timestamp == TEST_START
    assert time_cfg.stop_timestamp == TEST_STOP
    assert time_cfg.physics_step_sec == DEFAULT_TIME_STEP
    assert time_cfg.output_step_sec == DEFAULT_TIME_STEP

    # Enter dates as strings, rather than datetimes
    cfg_dict = deepcopy(time_cfg_dict)
    cfg_dict["start_timestamp"] = TEST_START.isoformat()
    cfg_dict["stop_timestamp"] = TEST_STOP.isoformat()
    time_cfg = TimeConfig(**cfg_dict)
    assert time_cfg.start_timestamp == TEST_START
    assert time_cfg.stop_timestamp == TEST_STOP

    # Test that this can be created from an empty dictionary
    with pytest.raises(ValidationError):
        TimeConfig()


def testInputValues(time_cfg_dict: dict):
    """Test bad input values to TimeConfig."""
    cfg_dict = deepcopy(time_cfg_dict)
    cfg_dict["physics_step_sec"] = -1
    with pytest.raises(ValidationError):
        TimeConfig(**cfg_dict)

    cfg_dict = deepcopy(time_cfg_dict)
    cfg_dict["physics_step_sec"] = 0
    with pytest.raises(ValidationError):
        TimeConfig(**cfg_dict)

    cfg_dict = deepcopy(time_cfg_dict)
    cfg_dict["output_step_sec"] = -1
    with pytest.raises(ValidationError):
        TimeConfig(**cfg_dict)

    cfg_dict = deepcopy(time_cfg_dict)
    cfg_dict["output_step_sec"] = 0
    with pytest.raises(ValidationError):
        TimeConfig(**cfg_dict)

    cfg_dict = deepcopy(time_cfg_dict)
    cfg_dict["stop_timestamp"] = cfg_dict["start_timestamp"]
    with pytest.raises(ValidationError):
        TimeConfig(**cfg_dict)
