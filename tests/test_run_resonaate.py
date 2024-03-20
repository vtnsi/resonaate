"""Tests for :func:`.runResonaate`."""

from __future__ import annotations

# Standard Library Imports
from unittest.mock import MagicMock, patch

# RESONAATE Imports
from resonaate import runResonaate


@patch("resonaate.physics.time.conversions.getTargetJulianDate")
@patch("resonaate.scenario.buildScenarioFromConfigFile")
def testRunResonaate(
    mock_scenario_builder: MagicMock,
    mock_get_target_jd: MagicMock,
):
    """Test :func:`.runResonaate`."""
    # Create a fake scenario that is returned by the scenario builder
    mocked_app = MagicMock()
    mocked_propagate = MagicMock()
    mocked_app.propagateTo = mocked_propagate
    mock_scenario_builder.return_value = mocked_app

    # Create a fake target julian date for scenario
    mocked_target_jd = MagicMock()
    mock_get_target_jd.return_value = mocked_target_jd

    # Run the scenario
    runResonaate("foo", internal_db_path=None, importer_db_path=None)

    # Check that scenario builder was called
    mock_scenario_builder.assert_called_once_with(
        "foo",
        internal_db_path=None,
        importer_db_path=None,
    )

    # Check that target julian date was called
    mock_get_target_jd.assert_called_once()

    # Check that propagateTo was called with mocked target JulianDate
    mocked_propagate.assert_called_once_with(mocked_target_jd)
