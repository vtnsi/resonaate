"""Defines the :class:`.Logger` class."""

from __future__ import annotations

# Standard Library Imports
import logging
import sys
from logging.handlers import RotatingFileHandler
from os import makedirs
from os.path import exists, join

# Local Imports
from . import pathSafeTime
from .config import RootConfig


class Logger:
    """Extended logger wraps the standard Python logging package.

    It also creates a standard file name and log format for any log files that are saved.
    """

    def __init__(self, name, level=None, path=None):
        """Configure the logging information for this Logger instance.

        Args:
            name (``string``): Name of the the logger instance
            level (``logging.LOG_LEVEL``): Determines what level of log messages are published
            path (``string``): Path to where the log file will be stored
        """
        root_cfg = RootConfig.LIB.inst()
        if not level:
            level = root_cfg.behavioral_config.logging_level.level()
        if not path:
            path = root_cfg.behavioral_config.logging_output_location
        # Grab the logger
        self.logger = logging.getLogger(name)
        if not self.logger.handlers:
            # Write logs to file if path was provided, otherwise write to stdout
            if path == "stdout":
                # Write logs to stdout
                self.filename = "stdout"
                handler = logging.StreamHandler(sys.stdout)

            else:
                # Create the path if it doesn't exist.
                if not exists(path):
                    self.logger.info(f"Path did not exist: {path!r}. Creating path...")
                    makedirs(path)

                # Set the timestamp for the file name, and construct the entire filename
                log_name = f"{name}_{pathSafeTime()}.log"
                self.filename = join(path, log_name)

                # Create the file handler based on the file name
                handler = RotatingFileHandler(
                    self.filename,
                    maxBytes=root_cfg.behavioral_config.logging_max_file_size,
                    backupCount=root_cfg.behavioral_config.logging_max_file_count,
                )

            # Set the logger's formatter
            formatter = logging.Formatter("%(asctime)s - %(module)s - %(levelname)s - %(message)s")
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
    The primary use case is for simple functions that need to log messages.

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
