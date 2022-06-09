# pylint: disable=attribute-defined-outside-init, no-self-use
# Standard Library Imports
# Third Party Imports
# RESONAATE Imports
try:
    from resonaate.data.agent import Agent
except ImportError as error:
    raise Exception(
        f"Please ensure you have appropriate packages installed:\n {error}"
    ) from error
# Testing Imports
from ..conftest import BaseTestCase


class TestAgentTable(BaseTestCase):
    """Test class for :class:`.Agent` database table class."""

    def testInit(self):
        """Test the init of Agent database table."""
        _ = Agent()

    def testInitKwargs(self):
        """Test initializing the kewards of the table."""
        _ = Agent(
            unique_id=11111,
            name="Test Agent",
        )

    def testReprAndDict(self):
        """Test printing DB table object & making into dict."""
        agent = Agent(
            unique_id=11111,
            name="Test Agent",
        )
        print(agent)
        agent.makeDictionary()

    def testEquality(self):
        """Test equals and not equals operators."""
        agent1 = Agent(
            unique_id=11111,
            name="Test Agent",
        )

        agent2 = Agent(
            unique_id=11111,
            name="Test Agent",
        )

        agent3 = Agent(
            unique_id=11111,
            name="Test Agent",
        )
        agent3.name = "Different Agent"

        # Test equality and inequality
        assert agent1 == agent2
        assert agent1 != agent3
