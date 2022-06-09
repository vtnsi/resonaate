# pylint: disable=attribute-defined-outside-init, no-self-use
# Standard Library Imports
# Third Party Imports
import pytest
from numpy import (
    any as np_any, asarray, array_equal, full, nonzero, sort, unique
)
# RESONAATE Imports
try:
    from resonaate.tasking.decisions.decision_base import Decision
    from resonaate.tasking.decisions.decisions import (
        MunkresDecision, MyopicNaiveGreedyDecision, RandomDecision, AllVisibleDecision
    )
except ImportError as error:
    raise Exception(
        f"Please ensure you have appropriate packages installed:\n {error}"
    ) from error
# Testing Imports
from ..conftest import BaseTestCase


@pytest.fixture(name="mocked_decision_class")
def mockedDecisionClass():
    """Return reference to a minimal :class:`.Decision` class."""
    class MockedDecision(Decision):
        def _makeDecision(self, reward_matrix, **kwargs):
            return 3

    return MockedDecision


class TestDecisionBase(BaseTestCase):
    """Test the base class of the decisions module."""

    def testRegistry(self, mocked_decision_class):
        """Test to make sure the decision object is registered."""
        # Test that new implemented class isn't registered
        test_decision = mocked_decision_class()
        assert test_decision.is_registered is False

        # Register new class and check
        Decision.register("MockedDecision", mocked_decision_class)
        test_decision = mocked_decision_class()
        assert test_decision.is_registered is True

        # Ensure we cannot register objects that are not :class:`.Decision` sub-classes
        with pytest.raises(TypeError):
            Decision.register("MockedDecision", [2, 2])

    def testCreation(self):
        """Test creating a Decision Object."""
        with pytest.raises(TypeError):
            Decision()  # pylint: disable=abstract-class-instantiated

    def testDecisionCall(self, mocked_decision_class):
        """Test the call function of the Decision base class."""
        reward_matrix = asarray([[10, 1.1, 0], [4, 15.9, 1], [2.1, 3, 11]])
        decision = mocked_decision_class()
        decision(reward_matrix)


class TestMyopicNaiveGreedyDecision(BaseTestCase):
    """Test the MyopicNaiveGreedyDecision class of the decisions module."""

    def testMyopicRegistry(self):
        """Test registering the Myopic decision is registered."""
        myopic = MyopicNaiveGreedyDecision()
        assert myopic.is_registered is True

    def testBasicDecision(self):
        """Test the call function of the MyopicNaiveGreedyDecision class."""
        myopic_decision = MyopicNaiveGreedyDecision()
        # Create example reward matrix & expected decision matrix
        reward_matrix = asarray([[10, 1.1, 0], [4, 15.9, 11], [2.1, 3, 1]])
        expected = [[True, False, False], [False, True, True], [False, False, False]]

        # Perform decision making, test expected
        decision = myopic_decision(reward_matrix)
        assert array_equal(decision, expected)
        # Assert constraint that single sensor cannot be tasked more than once
        tasked_sensors = nonzero(decision)[1]
        assert array_equal(unique(tasked_sensors), sort(tasked_sensors))

    def testNegativeDecision(self):
        """Test the call function of the MyopicNaiveGreedyDecision class."""
        myopic_decision = MyopicNaiveGreedyDecision()
        # Create example reward matrix & expected decision matrix
        reward_matrix = -1 * asarray([[10, 1.1, 0], [4, 15.9, 11], [2.1, 3, 1]])
        expected = [[False, False, False], [False, False, False], [False, False, False]]

        # Perform decision making, test expected
        decision = myopic_decision(reward_matrix)
        assert array_equal(decision, expected)
        # Assert constraint that single sensor cannot be tasked more than once
        tasked_sensors = nonzero(decision)[1]
        assert array_equal(unique(tasked_sensors), sort(tasked_sensors))

    def testEqualDecision(self):
        """Test the call function of the MyopicNaiveGreedyDecision class."""
        myopic_decision = MyopicNaiveGreedyDecision()
        # Create example reward matrix & expected decision matrix
        reward_matrix = full((3, 3), 10)
        expected = [[True, True, True], [False, False, False], [False, False, False]]

        # Perform decision making, test expected
        decision = myopic_decision(reward_matrix)
        assert array_equal(decision, expected)
        # Assert constraint that single sensor cannot be tasked more than once
        tasked_sensors = nonzero(decision)[1]
        assert array_equal(unique(tasked_sensors), sort(tasked_sensors))

    def testNullDecision(self):
        """Test the call function of the MyopicNaiveGreedyDecision class."""
        myopic_decision = MyopicNaiveGreedyDecision()
        # Create example null reward matrix
        reward_matrix = asarray([[0, 0, 0], [0, 0, 0], [0, 0, 0]])

        # Perform decision making, test expected null-tasking
        assert not np_any(myopic_decision(reward_matrix))


class TestMunkresDecision(BaseTestCase):
    """Test the MunkresDecision class of the decisions module."""

    def testMunkresRegistry(self):
        """Test registering the munkres decision is registered."""
        munkres = MunkresDecision()
        assert munkres.is_registered is True

    def testBasicDecision(self):
        """Test the call function of the MunkresDecision class."""
        munkres_decision = MunkresDecision()
        # Create example reward matrix & expected decision matrix
        reward_matrix = asarray([[1.1, 10, 12], [4, 15.9, 1], [2.1, 3, 11]])
        expected = [[False, False, True], [False, True, False], [True, False, False]]

        # Perform decision making, test expected
        decision = munkres_decision(reward_matrix)
        assert array_equal(decision, expected)
        # Assert constraint that single sensor cannot be tasked more than once
        tasked_sensors = nonzero(decision)[1]
        assert array_equal(unique(tasked_sensors), sort(tasked_sensors))

    def testNegativeDecision(self):
        """Test the call function of the MunkresDecision class."""
        munkres_decision = MunkresDecision()
        # Create example reward matrix & expected decision matrix
        reward_matrix = -1 * asarray([[1.1, 10, 12], [4, 15.9, 1], [2.1, 3, 11]])
        expected = [[False, False, False], [False, False, False], [False, False, False]]

        # Perform decision making, test expected
        decision = munkres_decision(reward_matrix)
        assert array_equal(decision, expected)
        # Assert constraint that single sensor cannot be tasked more than once
        tasked_sensors = nonzero(decision)[1]
        assert array_equal(unique(tasked_sensors), sort(tasked_sensors))

    def testEqualDecision(self):
        """Test the call function of the MunkresDecision class."""
        munkres_decision = MunkresDecision()
        # Create example reward matrix & expected decision matrix
        reward_matrix = full((3, 3), 10)
        expected = [[True, False, False], [False, True, False], [False, False, True]]

        # Perform decision making, test expected
        decision = munkres_decision(reward_matrix)
        assert array_equal(decision, expected)
        # Assert constraint that single sensor cannot be tasked more than once
        tasked_sensors = nonzero(decision)[1]
        assert array_equal(unique(tasked_sensors), sort(tasked_sensors))

    def testNullDecision(self):
        """Test the call function of the MunkresDecision class."""
        munkres_decision = MunkresDecision()
        # Create example null reward matrix
        reward_matrix = asarray([[0, 0, 0], [0, 0, 0], [0, 0, 0]])

        # Perform decision making, test expected null-tasking
        assert not np_any(munkres_decision(reward_matrix))


class TestRandomDecision(BaseTestCase):
    """Test the RandomDecision class of the decisions module."""

    def testMunkresRegistry(self):
        """Test registering the munkres decision is registered."""
        random = RandomDecision(None)
        assert random.is_registered is True

    def testBasicDecision(self):
        """Test the call function of the RandomDecision class."""
        random_decision = RandomDecision(20000)
        # Create example reward matrix & expected decision matrix
        reward_matrix = asarray([[1.1, 10, 12], [4, 15.9, 1], [2.1, 3, 11]])
        expected = [[False, False, False], [False, True, False], [True, False, True]]

        # Perform decision making, test expected
        decision = random_decision(reward_matrix)
        assert array_equal(decision, expected)
        # Assert constraint that single sensor cannot be tasked more than once
        tasked_sensors = nonzero(decision)[1]
        assert array_equal(unique(tasked_sensors), sort(tasked_sensors))

    def testNonVizDecision(self):
        """Test the call function of the RandomDecision class."""
        random_decision = RandomDecision(129281)
        # Create example reward matrix & expected decision matrix
        reward_matrix = asarray([[0, 10, 12], [4, 15.9, 0], [2.1, 3, 11]])
        expected = [[False, False, True], [True, False, False], [False, True, False]]

        # Perform decision making, test expected
        decision = random_decision(reward_matrix)
        assert array_equal(decision, expected)
        # Assert constraint that single sensor cannot be tasked more than once
        tasked_sensors = nonzero(decision)[1]
        assert array_equal(unique(tasked_sensors), sort(tasked_sensors))

    def testNullDecision(self):
        """Test the call function of the RandomDecision class."""
        random_decision = RandomDecision(1202102120)
        # Create example null reward matrix
        reward_matrix = asarray([[0, 0, 0], [0, 0, 0], [0, 0, 0]])

        # Perform decision making, test expected null-tasking
        assert not np_any(random_decision(reward_matrix))


class TestAllVisibleDecision(BaseTestCase):
    """Test the AllVisibleDecision class of the decisions module."""

    def testAllVisibleRegistry(self):
        """Test registering the AllVisible decision is registered."""
        all_visible = AllVisibleDecision()
        assert all_visible.is_registered is True

    def testBasicDecision(self):
        """Test the call function of the AllVisibleDecision class."""
        all_visible_decision = AllVisibleDecision()
        # Create example reward matrix & expected decision matrix
        reward_matrix = asarray([[1.1, 0.0, 12], [0.0, 15.9, 1], [2.1, 3, 11]])
        expected = [[True, False, True], [False, True, True], [True, True, True]]

        # Perform decision making, test expected
        decision = all_visible_decision(reward_matrix)
        assert array_equal(decision, expected)

    def testNegativeDecision(self):
        """Test the call function of the AllVisibleDecision class."""
        all_visible_decision = AllVisibleDecision()
        # Create example reward matrix & expected decision matrix
        reward_matrix = -1 * asarray([[1.1, 10, 12], [4, 15.9, 1], [2.1, 3, 11]])
        expected = [[False, False, False], [False, False, False], [False, False, False]]

        # Perform decision making, test expected
        decision = all_visible_decision(reward_matrix)
        assert array_equal(decision, expected)

    def testEqualDecision(self):
        """Test the call function of the AllVisibleDecision class."""
        all_visible_decision = AllVisibleDecision()
        # Create example reward matrix & expected decision matrix
        reward_matrix = full((3, 3), 10)
        expected = [[True, True, True], [True, True, True], [True, True, True]]

        # Perform decision making, test expected
        decision = all_visible_decision(reward_matrix)
        assert array_equal(decision, expected)

    def testNullDecision(self):
        """Test the call function of the AllVisibleDecision class."""
        all_visible_decision = AllVisibleDecision()
        # Create example null reward matrix
        reward_matrix = asarray([[0, 0, 0], [0, 0, 0], [0, 0, 0]])

        # Perform decision making, test expected null-tasking
        assert not np_any(all_visible_decision(reward_matrix))
