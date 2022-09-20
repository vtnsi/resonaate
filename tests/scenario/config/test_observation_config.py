from __future__ import annotations

# RESONAATE Imports
from resonaate.scenario.config.observation_config import ObservationConfig


def testObservationConfig():
    """Test that ObservationConfig can be created from a dictionary."""
    cfg = ObservationConfig(background=True)
    assert cfg.background is True
