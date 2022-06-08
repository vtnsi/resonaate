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

        @param name \b string -- Name of the the logger instance
        @param level \b logging.LOG_LEVEL --  Determines what level of log messages are published
        @param path \b string -- Path to where the log file will be stored
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
                    print("Path did not exist: '{0}'. Creating path...".format(path))
                    makedirs(path)

                # Set the timestamp for the file name, and construct the entire filename
                now = datetime.now()
                time_tup = now.timetuple()
                timestamp = "{0}{1}{2}_{3}{4}{5}".format(
                    time_tup[0],
                    time_tup[1],
                    time_tup[2],
                    time_tup[3],
                    time_tup[4],
                    time_tup[5]
                )
                log_name = "{0}_{1}.log".format(name, timestamp)
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
