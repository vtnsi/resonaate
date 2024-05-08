from __future__ import annotations

# Standard Library Imports
import logging
import os

# Third Party Imports
import pytest

# RESONAATE Imports
from resonaate.common.logger import Logger

# Local Imports
from .. import FIXTURE_DATA_DIR


def getLines(stdout_buff: str) -> str:
    r"""Return each separate line in a string buffer.

    Args:
        stdout_buff (str): stdout string buffer

    Yields:
        str: single line captured in string buffer, delimited by `\\n`
    """
    lines = stdout_buff.split("\n")

    for line in lines:
        if line:
            yield line


CORRECT_OUTPUT: list[list[str | int]] = [
    ["test", logging.DEBUG, "This is a debug message."],
    ["test", logging.INFO, "This is an info message."],
    ["test", logging.WARNING, "This is a warning message."],
    ["test", logging.ERROR, "This is an error message."],
    ["test", logging.CRITICAL, "This is a critical message."],
]

CORRECT_FILE_OUTPUT: list[list[str | int]] = [
    ["test_logger", "DEBUG", "This is a debug message.\n"],
    ["test_logger", "INFO", "This is an info message.\n"],
    ["test_logger", "WARNING", "This is a warning message.\n"],
    ["test_logger", "ERROR", "This is an error message.\n"],
    ["test_logger", "CRITICAL", "This is a critical message.\n"],
]


def testStdout(caplog: pytest.LogCaptureFixturep):
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
        assert record_tuple == tuple(CORRECT_OUTPUT[item])
        line_count += 1

    assert line_count == 5


@pytest.mark.datafiles(FIXTURE_DATA_DIR)
def testLogfile(datafiles: str):
    """Test the logger's output to a logfile."""
    saved_cwd = os.getcwd()
    os.chdir(datafiles)
    file_logger = Logger("logfile-test", path="logs/")

    file_logger.debug("This is a debug message.")
    file_logger.info("This is an info message.")
    file_logger.warning("This is a warning message.")
    file_logger.error("This is an error message.")
    file_logger.critical("This is a critical message.")

    with open(file_logger.filename, encoding="utf-8") as logfile:
        line_count = 0
        for item, line in enumerate(logfile):
            assert line.split(" - ")[1:] == CORRECT_FILE_OUTPUT[item]
            line_count += 1

        assert line_count == 5

    os.chdir(saved_cwd)
