# pylint: disable=attribute-defined-outside-init
# Standard Library Imports
# Third Party Imports
# RESONAATE Imports
try:
    # RESONAATE Imports
    from resonaate.data.agent import AgentModel
except ImportError as error:
    raise Exception(f"Please ensure you have appropriate packages installed:\n {error}") from error
# Local Imports
# Testing Imports
from ..conftest import BaseTestCase


class TestAgentTable(BaseTestCase):
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
