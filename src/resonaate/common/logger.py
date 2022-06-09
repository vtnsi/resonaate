"""Defines the :class:`.Logger` class."""
# Standard Library Imports
import logging
import sys
from os.path import join, exists
from os import makedirs
from datetime import datetime
# Third Party Imports
from concurrent_log_handler import ConcurrentRotatingFileHandler as FileHandler
# RESONAATE Imports
from .behavioral_config import BehavioralConfig


class Logger:
    """Extended logger wraps the standard Python logging package.

    It utilizes the `concurrent_log_handler` package to avoid dropping log files.
    It also creates a standard file name and log format for any log files that are saved.
    """

    def __init__(self, name, level=None, path=None, allow_multiple_handlers=None):
        """Configure the logging information for this Logger instance.

        Args:
            name (``string``): Name of the the logger instance
            level (``logging.LOG_LEVEL``): Determines what level of log messages are published
            path (``string``): Path to where the log file will be stored
        """
        if not level:
            level = BehavioralConfig.getConfig().logging.Level
        if not path:
            path = BehavioralConfig.getConfig().logging.OutputLocation
        if not allow_multiple_handlers:
            allow_multiple_handlers = BehavioralConfig.getConfig().logging.AllowMultipleHandlers
        # Grab the logger
        self.logger = logging.getLogger(name)
        if not self.logger.handlers or allow_multiple_handlers is True:
            # Write logs to file if path was provided, otherwise write to stdout
            if path == "stdout":
                # Write logs to stdout
                self.filename = "stdout"
                handler = logging.StreamHandler(sys.stdout)

            else:
                # Create the path if it doesn't exist.
                if not exists(path):
                    print(f"Path did not exist: '{path}'. Creating path...")
                    makedirs(path)

                # Set the timestamp for the file name, and construct the entire filename
                now = datetime.now()
                time_tup = now.timetuple()
                timestamp = f"{time_tup[0]}{time_tup[1]}{time_tup[2]}_{time_tup[3]}{time_tup[4]}{time_tup[5]}"
                log_name = f"{name}_{timestamp}.log"
                self.filename = join(path, log_name)

                # Create the file handler based on the file name
                handler = FileHandler(
                    self.filename,
                    maxBytes=BehavioralConfig.getConfig().logging.MaxFileSize,
                    backupCount=BehavioralConfig.getConfig().logging.MaxFileCount
                )

            # Set the logger's formatter
            formatter = logging.Formatter('%(asctime)s - %(module)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)

            # Configure the logger with the handler
            self.logger.setLevel(level)
            self.logger.addHandler(handler)

    def __getattr__(self, name):
        """."""
        return getattr(self.logger, name)


def _resonaateLog(message: str, level: int):
    """Log a message to the top-level log record.

    This provides a simple, easy one-liner that doesn't require pre-initializing a logger object.
    The primary usecase is for simple functions that need to log messages.

    Args:
        message (``str``): message to record with in the log.
        level (``int``): level at which to log this message, corresponding to `logging.LOG_LEVEL`.
    """
    logger = logging.getLogger("resonaate")
    logger.log(msg=message, level=level)


def resonaateLogCritical(message: str):
    """Log a CRITICAL message to the top-level log record.

    See Also:
        :func:`._resonaateLog`

    Args:
        message (``str``): message to record with in the log.
    """
    _resonaateLog(message, level=logging.CRITICAL)


def resonaateLogError(message: str):
    """Log a ERROR message to the top-level log record.

    See Also:
        :func:`._resonaateLog`

    Args:
        message (``str``): message to record with in the log.
    """
    _resonaateLog(message, level=logging.ERROR)


def resonaateLogWarning(message: str):
    """Log a WARNING message to the top-level log record.

    See Also:
        :func:`._resonaateLog`

    Args:
        message (``str``): message to record with in the log.
    """
    _resonaateLog(message, level=logging.WARNING)


def resonaateLogInfo(message: str):
    """Log a INFO message to the top-level log record.

    See Also:
        :func:`._resonaateLog`

    Args:
        message (``str``): message to record with in the log.
    """
    _resonaateLog(message, level=logging.INFO)


def resonaateLogDebug(message: str):
    """Log a DEBUG message to the top-level log record.

    See Also:
        :func:`._resonaateLog`

    Args:
        message (``str``): message to record with in the log.
    """
    _resonaateLog(message, level=logging.DEBUG)


def resonaateLogNotSet(message: str):
    """Log a NOTSET message to the top-level log record.

    See Also:
        :func:`._resonaateLog`

    Args:
        message (``str``): message to record with in the log.
    """
    _resonaateLog(message, level=logging.NOTSET)
