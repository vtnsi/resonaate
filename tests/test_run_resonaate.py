"""Tests for :func:`.runResonaate`."""

from __future__ import annotations

# Standard Library Imports
from unittest.mock import MagicMock, patch

# RESONAATE Imports
from resonaate import runResonaate
from resonaate.common.config import EntrypointConfig, InputConfig
from resonaate.physics.time.stardate import JulianDate


@patch("resonaate.scenario.buildScenarioFromConfigFile")
def testRunResonaate(
    mock_scenario_builder: MagicMock,
):
    """Test :func:`.runResonaate`."""
    # Create a fake scenario that is returned by the scenario builder
    jd_stop = JulianDate(2400000.5 + 58924)  # arbitrary jd for March 16, 2020
    mocked_app = MagicMock()
    mocked_clock = MagicMock()
    mocked_clock.julian_date_stop = jd_stop
    mocked_propagate = MagicMock()
    mocked_app.clock = mocked_clock
    mocked_app.propagateTo = mocked_propagate
    mock_scenario_builder.return_value = mocked_app
    entry_config = EntrypointConfig(input_config=InputConfig(init_file="foo"))

    # Run the scenario
    runResonaate(entry_config)

    # Check that scenario builder was called
    mock_scenario_builder.assert_called_once_with(
        entry_config.input_config.init_file,
        internal_db_params=entry_config.output_config,
        importer_db_params=entry_config.input_config.importer_db_params,
    )

    # Check that propagateTo was called with mocked target JulianDate
    mocked_propagate.assert_called_once_with(jd_stop)


@patch("resonaate.scenario.buildScenarioFromConfigFile")
def testRunResonaate_duration(
    mock_scenario_builder: MagicMock,
):
    """Test :func:`.runResonaate`."""
    # Create a fake scenario that is returned by the scenario builder
    jd_start = JulianDate(2400000.5 + 58909)  # arbitrary jd for March 1, 2020
    jd_stop = JulianDate(2400000.5 + 58924)  # arbitrary jd for March 16, 2020
    mocked_app = MagicMock()
    mocked_clock = MagicMock()
    mocked_clock.julian_date_start = jd_start
    mocked_clock.julian_date_stop = jd_stop
    mocked_propagate = MagicMock()
    mocked_app.clock = mocked_clock
    mocked_app.propagateTo = mocked_propagate
    mock_scenario_builder.return_value = mocked_app
    entry_config = EntrypointConfig(input_config=InputConfig(init_file="foo", sim_duration=12))

    # Create a fake target julian date for scenario
    duration_target_jd = jd_start + JulianDate(0.5)
    # provided sim duration of 12 hours, so target jd should be .5 days later

    # Run the scenario
    runResonaate(entry_config)

    # Check that scenario builder was called
    mock_scenario_builder.assert_called_once_with(
        entry_config.input_config.init_file,
        internal_db_params=entry_config.output_config,
        importer_db_params=entry_config.input_config.importer_db_params,
    )

    # Check that propagateTo was called with mocked target JulianDate
    mocked_propagate.assert_called_once_with(duration_target_jd)
