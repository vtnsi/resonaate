from __future__ import annotations

# Standard Library Imports
from copy import deepcopy
from typing import TYPE_CHECKING

# Third Party Imports
import pytest

# Type Checking Imports
if TYPE_CHECKING:

    # RESONAATE Imports
    from resonaate.data.agent import AgentModel
    from resonaate.data.epoch import Epoch


def testComparison(epoch: Epoch, target_agent: AgentModel):
    """Ensure comparison between data objects behave properly."""
    with pytest.raises(TypeError):
        assert epoch == target_agent

    new_target = deepcopy(target_agent)
    assert new_target == target_agent
