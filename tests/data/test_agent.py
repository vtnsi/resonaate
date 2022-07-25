from __future__ import annotations

# RESONAATE Imports
from resonaate.data.agent import AgentModel


class TestAgentTable:
    """Test class for :class:`.AgentModel` database table class."""

    def testInit(self):
        """Test the init of AgentModel database table."""
        _ = AgentModel()

    def testInitKwargs(self):
        """Test initializing the kewards of the table."""
        _ = AgentModel(
            unique_id=11111,
            name="Test Agent",
        )

    def testReprAndDict(self):
        """Test printing DB table object & making into dict."""
        agent = AgentModel(
            unique_id=11111,
            name="Test Agent",
        )
        print(agent)
        agent.makeDictionary()

    def testEquality(self):
        """Test equals and not equals operators."""
        agent1 = AgentModel(
            unique_id=11111,
            name="Test Agent",
        )

        agent2 = AgentModel(
            unique_id=11111,
            name="Test Agent",
        )

        agent3 = AgentModel(
            unique_id=11111,
            name="Test Agent",
        )
        agent3.name = "Different Agent"

        # Test equality and inequality
        assert agent1 == agent2
        assert agent1 != agent3
