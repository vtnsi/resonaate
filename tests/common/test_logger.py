# pylint: disable=attribute-defined-outside-init, no-self-use
# Standard Library Imports
import logging
# Third Party Imports
# RESONAATE Imports
try:
    from resonaate.common.logger import Logger
except ImportError as error:
    raise Exception(
        "Please ensure you have appropriate packages installed:\n {0}".format(error)
    ) from error
# Testing Imports
from ..conftest import BaseTestCase


def getLines(stdout_buff):
    """Return each separate line in a string buffer.

    Args:
        stdout_buff (str): stdout string buffer

    Yields:
        str: single line captured in string buffer, delimited by `\\n`
    """
    lines = stdout_buff.split('\n')

    for line in lines:
        if line:
            yield line


class TestLogging(BaseTestCase):
    """Class to test :module:`.common.logging` module."""

    CORRECT_OUTPUT = [
        ["test", logging.DEBUG, "This is a debug message."],
        ["test", logging.INFO, "This is an info message."],
        ["test", logging.WARNING, "This is a warning message."],
        ["test", logging.ERROR, "This is an error message."],
        ["test", logging.CRITICAL, "This is a critical message."]
    ]

    CORRECT_FILE_OUTPUT = [
        ["test_logger", "DEBUG", "This is a debug message.\n"],
        ["test_logger", "INFO", "This is an info message.\n"],
        ["test_logger", "WARNING", "This is a warning message.\n"],
        ["test_logger", "ERROR", "This is an error message.\n"],
        ["test_logger", "CRITICAL", "This is a critical message.\n"]
    ]

    def testStdout(self, caplog):
        """Test the logger's output to `sys.stdout`."""
        logger = Logger("test")
        logger.debug("This is a debug message.")
        logger.info("This is an info message.")
        logger.warning("This is a warning message.")
        logger.error("This is an error message.")
        logger.critical("This is a critical message.")

        line_count = 0
        # Read captured stdout and stderr
        for item, record_tuple in enumerate(caplog.record_tuples):
            assert record_tuple == tuple(self.CORRECT_OUTPUT[item])
            line_count += 1

        assert line_count == 5

    def testLogfile(self):
        """Test the logger's output to a logfile."""
        file_logger = Logger("logfile-test", path="logs/")

        file_logger.debug("This is a debug message.")
        file_logger.info("This is an info message.")
        file_logger.warning("This is a warning message.")
        file_logger.error("This is an error message.")
        file_logger.critical("This is a critical message.")

        with open(file_logger.filename, 'r') as logfile:
            line_count = 0
            for item, line in enumerate(logfile):
                assert line.split(" - ")[1:] == self.CORRECT_FILE_OUTPUT[item]
                line_count += 1

            assert line_count == 5
