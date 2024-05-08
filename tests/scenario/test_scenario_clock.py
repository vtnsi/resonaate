from __future__ import annotations

# Standard Library Imports
from datetime import datetime, timedelta

# Third Party Imports
import pytest

# RESONAATE Imports
from resonaate.physics.time.stardate import datetimeToJulianDate
from resonaate.scenario.clock import ScenarioClock
from resonaate.scenario.config.time_config import TimeConfig


@pytest.fixture(name="scenario_start")
def scenarioStart():
    """Datetime corresponding to the beginning of the scenario."""
    return datetime(2021, 10, 12, 1, 0, 0)


@pytest.fixture(name="scenario_timestep")
def scenarioTimestep():
    """Time step of the scenario."""
    return 60.0


@pytest.fixture(name="scenario_end")
def scenarioEnd(scenario_start: datetime, scenario_timestep: float):
    """Datetime corresponding to the end of the scenario."""
    return scenario_start + timedelta(seconds=scenario_timestep)


@pytest.fixture(name="scenario_time_span")
def scenarioTimeSpan(scenario_start: datetime, scenario_end: datetime):
    """Duration of the scenario in seconds."""
    return (scenario_end - scenario_start).total_seconds()


@pytest.fixture(name="clock_instance")
def clockInstance(
    scenario_start: datetime,
    scenario_time_span: float,
    scenario_timestep: float,
    database: None,
):
    """Instance of `ScenarioClock`."""
    return ScenarioClock(scenario_start, scenario_time_span, scenario_timestep)


def testClockAttributes(
    clock_instance: ScenarioClock,
    scenario_start: datetime,
    scenario_time_span: float,
    scenario_timestep: float,
):
    """Test that the attributes of the clock are set correctly, and that `.ticToc` works correctly."""
    assert clock_instance.datetime_start == scenario_start
    assert clock_instance.julian_date_start == datetimeToJulianDate(scenario_start)
    assert clock_instance.datetime_stop == scenario_start + timedelta(seconds=scenario_time_span)
    assert clock_instance.time == 0.0
    clock_instance.ticToc()  # increment time by one timestep
    assert clock_instance.time == scenario_timestep
    assert clock_instance.datetime_epoch == scenario_start + timedelta(seconds=scenario_timestep)
    assert (
        clock_instance.julian_date_epoch
        == clock_instance.julian_date_start + scenario_timestep / 86400
    )


@pytest.fixture(name="clock_from_config")
def clockFromConfig(scenario_start: datetime, scenario_end: datetime, database: None):
    """Instance of `ScenarioClock` configured from `TimeConfig`."""
    time_config = TimeConfig(
        start_timestamp=scenario_start,
        stop_timestamp=scenario_end,
    )
    return ScenarioClock.fromConfig(time_config)


def testClockFromConfig(
    clock_from_config: ScenarioClock,
    scenario_start: datetime,
    scenario_end: datetime,
):
    """Test that the attributes of the clock match the config."""
    assert clock_from_config.datetime_start == scenario_start
    assert clock_from_config.datetime_stop == scenario_end
    assert clock_from_config.time_span == (scenario_end - scenario_start).total_seconds()
