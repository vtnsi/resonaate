from __future__ import annotations

# Standard Library Imports
from typing import TYPE_CHECKING

# Third Party Imports
import pytest

# Type Checking Imports
if TYPE_CHECKING:
    # RESONAATE Imports
    from resonaate.common.logger import Logger


@pytest.fixture(scope="module", autouse=True)
def exampleModuleFixture(test_logger: Logger):
    """Shows a fixture called at the module scope.

    Automatically invoked without declaring a function argument.

    See Also:
        https://docs.pytest.org/en/latest/fixture.html

    Args:
        test_logger (`logging.Logger`): unit test logger defined in conftest.py
    """
    print("")
    test_logger.warning("Executed before running any tests in a module")
    yield
    print("")
    test_logger.warning("Executed after running any tests a module")


@pytest.fixture(autouse=True)
def exampleFunctionFixture(test_logger: Logger):
    """Shows a fixture called at the function scope.

    Automatically invoked without declaring a function argument.

    See Also:
        https://docs.pytest.org/en/latest/fixture.html

    Args:
        test_logger (`logging.Logger`): unit test logger defined in conftest.py
    """
    print("")
    test_logger.info("Executed before a test function")
    yield
    print("")
    test_logger.info("Executed after a test function")


def testExamplePass(test_logger: Logger):
    """Example unit test that passes.

    Args:
        test_logger (:class:'logging.Logger`): logger fixture defined in `conftest.py`
    """
    assert True
    test_logger.info("Successfully ran a unit test!")


def testExampleFail(test_logger: Logger):
    """Example unit test that fails.

    Args:
        test_logger (:class:'logging.Logger`): logger fixture defined in `conftest.py`
    """
    test_logger.info("This unit test is will fail!")
    assert False


@pytest.mark.xfail()
def testExampleExpectedFail(test_logger: Logger):
    """Example unit test that is an expected fail.

    Args:
        test_logger (:class:'logging.Logger`): logger fixture defined in `conftest.py`
    """
    test_logger.info("This unit test is expected to fail!")
    assert False


@pytest.mark.skip(reason="Demonstration for how to skip tests.")
def testExampleSkip(test_logger: Logger):
    """Example unit test that is skipped.

    Args:
        test_logger (:class:'logging.Logger`): logger fixture defined in `conftest.py`
    """
    test_logger.info("This unit test is skipped!")
    assert True
