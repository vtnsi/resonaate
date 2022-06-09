# Pylint and flake8 ignores only included b/c they are examples
# pylint: disable=attribute-defined-outside-init
# Standard Library Imports
# Third Party Imports
import pytest


@pytest.fixture(scope="class", autouse=True)
def exampleClassFixture(test_logger):
    """Shows a fixture called at the class scope.

    Automatically invoked without declaring a function argument.

    See Also:
        https://docs.pytest.org/en/latest/fixture.html

    Args:
        testLogger (`logging.Logger`): unit test logger defined in conftest.py
    """
    print("")
    test_logger.warning("Executed before running any tests in a class")
    yield
    print("")
    test_logger.warning("Executed after running any tests a class")


@pytest.fixture(autouse=True)
def exampleFunctionFixture(test_logger):
    """Shows a fixture called at the function scope.

    Automatically invoked without declaring a function argument.

    See Also:
        https://docs.pytest.org/en/latest/fixture.html

    Args:
        testLogger (`logging.Logger`): unit test logger defined in conftest.py
    """
    print("")
    test_logger.info("Executed before a test function")
    yield
    print("")
    test_logger.info("Executed after a test function")


class TestExampleUnitTest:
    """Example unit test class."""

    def testExamplePass(self, test_logger):
        """Example unit test that passes.

        Args:
            test_logger (:class:'logging.Logger`): logger fixture defined in `conftest.py`
        """
        assert True
        test_logger.info("Successfully ran a unit test!")

    def testExampleFail(self, test_logger):
        """Example unit test that fails.

        Args:
            test_logger (:class:'logging.Logger`): logger fixture defined in `conftest.py`
        """
        test_logger.info("This unit test is will fail!")
        assert False

    @pytest.mark.xfail()
    def testExampleExpectedFail(self, test_logger):
        """Example unit test that is an expected fail.

        Args:
            test_logger (:class:'logging.Logger`): logger fixture defined in `conftest.py`
        """
        test_logger.info("This unit test is expected to fail!")
        assert False

    @pytest.mark.skip(reason="Demonstration for how to skip tests.")
    def testExampleSkip(self, test_logger):
        """Example unit test that is skipped.

        Args:
            test_logger (:class:'logging.Logger`): logger fixture defined in `conftest.py`
        """
        test_logger.info("This unit test is skipped!")
        assert True
