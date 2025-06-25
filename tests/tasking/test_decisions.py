from __future__ import annotations

# Third Party Imports
import pytest
from numpy import any as np_any
from numpy import array_equal, asarray, full, nonzero, sort, unique

# RESONAATE Imports
from resonaate.tasking.decisions.decision_base import Decision
from resonaate.tasking.decisions.decisions import (
    AllVisibleDecision,
    MunkresDecision,
    MyopicNaiveGreedyDecision,
    RandomDecision,
)


@pytest.fixture(name="mocked_decision_class")
def mockedDecisionClass() -> Decision:
    """Return reference to a minimal :class:`.Decision` class."""

    class MockedDecision(Decision):
        def _calculate(self, reward_matrix, visibility_matrix):
            return 3

    return MockedDecision


class TestDecisionBase:
    """Test the base class of the decisions module."""

    def testCreation(self):
        """Test creating a Decision Object."""
        with pytest.raises(TypeError):
            Decision()

    def testDecisionCall(self, mocked_decision_class: Decision):
        """Test the call function of the Decision base class."""
        reward_matrix = asarray([[10, 1.1, 0], [4, 15.9, 1], [2.1, 3, 11]])
        visibility_matrix = asarray(
            [[True, False, False], [False, True, False], [False, False, True]],
        )
        decision = mocked_decision_class()
        decision.calculate(reward_matrix, visibility_matrix)


class TestMyopicNaiveGreedyDecision:
    """Test the MyopicNaiveGreedyDecision class of the decisions module."""

    def testBasicDecision(self):
        """Test the call function of the MyopicNaiveGreedyDecision class."""
        myopic_decision = MyopicNaiveGreedyDecision()
        # Create example reward matrix & expected decision matrix
        reward_matrix = asarray([[10, 1.1, 0], [4, 15.9, 11], [2.1, 3, 1]])
        visibility_matrix = asarray(
            [[True, False, False], [False, True, True], [False, False, False]],
        )

        # Perform decision making, test expected
        decision = myopic_decision.calculate(reward_matrix, visibility_matrix)
        expected = [[True, False, False], [False, True, True], [False, False, False]]
        assert array_equal(decision, expected)
        # Assert constraint that single sensor cannot be tasked more than once
        tasked_sensors = nonzero(decision)[1]
        assert array_equal(unique(tasked_sensors), sort(tasked_sensors))

    def testNegativeDecision(self):
        """Test the call function of the MyopicNaiveGreedyDecision class."""
        myopic_decision = MyopicNaiveGreedyDecision()
        # Create example reward matrix & expected decision matrix
        reward_matrix = -1 * asarray([[10, 1.1, 0], [4, 15.9, 11], [2.1, 3, 1]])
        visibility_matrix = full((3, 3), False)
        expected = full((3, 3), False)

        # Perform decision making, test expected
        decision = myopic_decision.calculate(reward_matrix, visibility_matrix)
        decision = decision & visibility_matrix
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
        visibility_matrix = asarray(
            [[True, True, True], [False, False, False], [False, False, False]],
        )
        # Perform decision making, test expected
        decision = myopic_decision.calculate(reward_matrix, visibility_matrix)
        assert array_equal(decision, expected)
        # Assert constraint that single sensor cannot be tasked more than once
        tasked_sensors = nonzero(decision)[1]
        assert array_equal(unique(tasked_sensors), sort(tasked_sensors))

    def testNullDecision(self):
        """Test the call function of the MyopicNaiveGreedyDecision class."""
        myopic_decision = MyopicNaiveGreedyDecision()
        # Create example null reward matrix
        reward_matrix = asarray([[0, 0, 0], [0, 0, 0], [0, 0, 0]])
        visibility_matrix = full((3, 3), False)
        # Perform decision making, test expected null-tasking
        decision = myopic_decision.calculate(reward_matrix, visibility_matrix) & visibility_matrix
        assert not np_any(decision)


class TestMunkresDecision:
    """Test the MunkresDecision class of the decisions module."""

    def testBasicDecision(self):
        """Test the call function of the MunkresDecision class."""
        munkres_decision = MunkresDecision()
        # Create example reward matrix & expected decision matrix
        reward_matrix = asarray([[1.1, 10, 12], [4, 15.9, 1], [2.1, 3, 11]])
        visibility_matrix = asarray(
            [[False, False, True], [False, True, False], [True, False, False]],
        )
        expected = [[False, False, True], [False, True, False], [True, False, False]]

        # Perform decision making, test expected
        decision = munkres_decision.calculate(reward_matrix, visibility_matrix)
        assert array_equal(decision, expected)
        # Assert constraint that single sensor cannot be tasked more than once
        tasked_sensors = nonzero(decision)[1]
        assert array_equal(unique(tasked_sensors), sort(tasked_sensors))

    def testNegativeDecision(self):
        """Test the call function of the MunkresDecision class."""
        munkres_decision = MunkresDecision()
        # Create example reward matrix & expected decision matrix
        reward_matrix = -1 * asarray([[1.1, 10, 12], [4, 15.9, 1], [2.1, 3, 11]])
        visibility_matrix = full((3, 3), False)
        expected = full((3, 3), False)

        # Perform decision making, test expected
        decision = munkres_decision.calculate(reward_matrix, visibility_matrix) & visibility_matrix
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
        visibility_matrix = asarray(
            [[True, False, False], [False, True, False], [False, False, True]],
        )

        # Perform decision making, test expected
        decision = munkres_decision.calculate(reward_matrix, visibility_matrix) & visibility_matrix
        assert array_equal(decision, expected)
        # Assert constraint that single sensor cannot be tasked more than once
        tasked_sensors = nonzero(decision)[1]
        assert array_equal(unique(tasked_sensors), sort(tasked_sensors))


class TestRandomDecision:
    """Test the RandomDecision class of the decisions module."""

    def testBasicDecision(self):
        """Test the call function of the RandomDecision class."""
        random_decision = RandomDecision(20000)
        # Create example reward matrix & expected decision matrix
        reward_matrix = asarray([[1.1, 10, 12], [4, 15.9, 1], [2.1, 3, 11]])
        visibility_matrix = full((3, 3), True)
        expected = [[False, False, False], [False, True, False], [True, False, True]]

        # Perform decision making, test expected
        decision = random_decision.calculate(reward_matrix, visibility_matrix)
        assert array_equal(decision, expected)
        # Assert constraint that single sensor cannot be tasked more than once
        tasked_sensors = nonzero(decision)[1]
        assert array_equal(unique(tasked_sensors), sort(tasked_sensors))

    def testNonVizDecision(self):
        """Test the call function of the RandomDecision class."""
        random_decision = RandomDecision(129281)
        # Create example reward matrix & expected decision matrix
        reward_matrix = asarray([[0, 10, 12], [4, 15.9, 0], [2.1, 3, 11]])
        visibility_matrix = asarray(
            [[False, False, True], [True, False, False], [False, True, False]],
        )
        expected = [[False, False, True], [True, False, False], [False, True, False]]

        # Perform decision making, test expected
        decision = random_decision.calculate(reward_matrix, visibility_matrix)
        assert array_equal(decision, expected)
        # Assert constraint that single sensor cannot be tasked more than once
        tasked_sensors = nonzero(decision)[1]
        assert array_equal(unique(tasked_sensors), sort(tasked_sensors))

    def testNullDecision(self):
        """Test the call function of the RandomDecision class."""
        random_decision = RandomDecision(1202102120)
        # Create example null reward matrix
        visibility_matrix = full((3, 3), False)
        reward_matrix = asarray([[0, 0, 0], [0, 0, 0], [0, 0, 0]])

        # Perform decision making, test expected null-tasking
        assert not np_any(random_decision.calculate(reward_matrix, visibility_matrix))


class TestAllVisibleDecision:
    """Test the AllVisibleDecision class of the decisions module."""

    def testBasicDecision(self):
        """Test the call function of the AllVisibleDecision class."""
        all_visible_decision = AllVisibleDecision()
        # Create example reward matrix & expected decision matrix
        reward_matrix = full((3, 3), False)
        visibility_matrix = asarray([[True, False, True], [False, True, True], [True, True, True]])
        expected = [[True, False, True], [False, True, True], [True, True, True]]

        # Perform decision making, test expected
        decision = all_visible_decision.calculate(reward_matrix, visibility_matrix)
        assert array_equal(decision, expected)
