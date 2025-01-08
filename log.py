from copy import deepcopy
from enum import auto, Enum
from inspect import currentframe as f
from pathlib import Path
import datetime as dt
import json


class Level(Enum):
    """Enum represnting log level"""

    Error = auto()  # red
    Warning = auto()  # yellow
    Log = auto()  # white
    Info = auto()  # blue
    Debug = auto()  # purple


def _ensure_level(level):
    """convert a `str` or `Level` to a `Level`

    Args:
        level (str | Level): level to convert

    Raises:
        ValueError: when invalid `level` is encountered

    Returns:
        Level: `Level` represented by `level`
    """
    if isinstance(level, str):
        try:
            level = {
                "error": Level.Error,
                "warning": Level.Warning,
                "log": Level.Log,
                "info": Level.Info,
                "debug": Level.Debug,
            }[level]
        except KeyError:
            raise ValueError(f"Invalid level name: {level}")
    return level


# ansii color codes used by stdout_formatter
_colors = {
    Level.Error: "\x1b[31m",
    Level.Warning: "\x1b[33m",
    Level.Log: "\x1b[32m",
    Level.Info: "\x1b[34m",
    Level.Debug: "\x1b[35m",
}
_reset = "\x1b[0m"


# declare the global logger
# NOTE: this is overwritten later in the file with the default global logger
_LOG = None


def json_formatter(record):
    """format record as ASCII JSON

    Args:
        record (dict): record to format

    Returns:
        str: formatted str
    """
    record = deepcopy(record)
    record["time"] = record["time"].isoformat()
    record["level"] = record["level"].value
    return json.dumps(record, ensure_ascii=True)


def stdout_formatter(record):
    """format record in human-readable format

    Args:
        record (dict): record to format

    Returns:
        str: formatted str
    """
    time = record["time"]
    level = record["level"]
    message = record["message"]
    level_str = f"{_colors[level]}{level.name.lower()}{_reset}"
    return f"{time} - {level_str} - {message}"


class Log:
    """`Log` class representing a logger

    there is no need to construct a logger if you just want to log to stdout. Just call

    `log(message)`

    to use the default global logger
    """

    def __init__(
        self,
        *opaths,
        file_level=Level.Log,
        formatter=json_formatter,
        stdout=True,
        stdout_level=None,
        stdout_formatter=stdout_formatter,
    ):
        """`Log` class representing a logger

        Args:
            *opaths (str | Path | file-like): Files to output records to.
            stdout (bool, optional): Output records to stdout as well as the files. Defaults to True.
            level (Level, optional): Level to filter records. Record must have level <= level to be output. Defaults to Level.Log.
            stdout_level (Level, optional): Level to filter records for stdout. Record must have level <= level to be output. Defaults to level.
            format (): Formatter for records. Defaults to identity.
            stdout_format (): Formatter for records for stdout. Defaults to identity.
        """
        self._file_levels = [file_level]
        self._levels = [file_level] if stdout_level is None else [stdout_level]
        self._stdout = stdout
        self._opaths = list(opaths)
        self._ofiles = []
        self._formatter = formatter
        self._stdout_formatter = stdout_formatter
        for i, opath in enumerate(self._opaths):
            if isinstance(opath, str):
                self._opaths[i] = Path(opath)
                self._ofiles.append(open(self._opaths[i], "w"))
            elif isinstance(opath, Path):
                self._ofiles.append(open(self._opaths[i], "w"))
            else:
                self._ofiles.append(opath)

    def set_global(self) -> "Log":
        """make `self` the global logger

        Returns:
            Log: previous incumbent logger
        """
        global _LOG
        prev = _LOG
        _LOG = self
        return prev

    def file_level(self, new_level=None):
        """modify the file logging level stack

        `self.file_level()` to pop and return the last-pushed logging level
        `self.file_level(new_level)` to push a new logging level onto the stack

        Args:
            new_level (str | Level, optional): when pushing, the new level to push onto the stack. Defaults to None.

        Raises:
            ValueError: if popping when the stack len is <= 1 (stack must never be empty)

        Returns:
            Level | None: when popping, the last-pushed logging level
        """
        if new_level is None:
            if len(self._file_levels) < 2:
                raise ValueError
            return self._file_levels.pop()
        else:
            new_level = _ensure_level(new_level)
            self._file_levels.append(new_level)

    def level(self, new_level=None):
        """modify the stdout logging level stack

        `self.level()` to pop and return the last-pushed logging level
        `self.level(new_level)` to push a new logging level onto the stack

        Args:
            new_level (str | Level, optional): when pushing, the new level to push onto the stack. Defaults to None.

        Raises:
            ValueError: if popping when the stack len is <= 1 (stack must never be empty)

        Returns:
            Level | None: when popping, the last-pushed logging level
        """
        if new_level is None:
            if len(self._levels) < 2:
                raise ValueError
            return self._levels.pop()
        else:
            new_level = _ensure_level(new_level)
            self._levels.append(new_level)

    def log(self, message, level=Level.Log):
        """log a message

        Args:
            message (any): the message to log
            level (str | Level, optional): the level at which to log. Defaults to Level.Log.
        """
        record = {
            "time": dt.datetime.now().astimezone(dt.timezone.utc),
            "level": level,
            "message": message,
        }
        if self._file_levels[-1].value >= level.value:
            record_str = self._formatter(record)
            for ofile in self._ofiles:
                ofile.write(f"{record_str}\n")
        if self._stdout and self._levels[-1].value >= level.value:
            record_str = self._stdout_formatter(record)
            print(record_str)

    def error(self, message):
        """log a message as an error

        Args:
            message (any): the message to log
        """
        self.log(message, Level.Error)

    def warn(self, message):
        """log a message as a warning

        Args:
            message (any): the message to log
        """
        self.log(message, Level.Warning)

    def info(self, message):
        """log a message as info

        Args:
            message (any): the message to log
        """
        self.log(message, Level.Info)

    def debug(self, message):
        """log a message for debugging

        Args:
            message (any): the message to log
        """
        self.log(message, Level.Debug)

    def close(self):
        """close all file objects

        Raises:
            NotImplementedError: _description_
        """
        raise NotImplementedError


# set the default global logger to simply log to stdout
Log().set_global()


def file_level(level=None):
    """modify the file logging level stack of the global logger

    `self.file_level()` to pop and return the last-pushed logging level
    `self.file_level(new_level)` to push a new logging level onto the stack

    Args:
        new_level (str | Level, optional): when pushing, the new level to push onto the stack. Defaults to None.

    Raises:
        ValueError: if popping when the stack len is <= 1 (stack must never be empty)

    Returns:
        Level | None: when popping, the last-pushed logging level
    """
    if _LOG is not None:
        _LOG.file_level(level)


def level(level=None):
    """modify the stdout logging level stack of the global logger

    `self.level()` to pop and return the last-pushed logging level
    `self.level(new_level)` to push a new logging level onto the stack

    Args:
        new_level (str | Level, optional): when pushing, the new level to push onto the stack. Defaults to None.

    Raises:
        ValueError: if popping when the stack len is <= 1 (stack must never be empty)

    Returns:
        Level | None: when popping, the last-pushed logging level
    """
    if _LOG is not None:
        _LOG.level(level)


def log(message, level=Level.Log):
    """log a message with the global logger

    Args:
        message (any): the message to log
        level (str | Level, optional): the level at which to log. Defaults to Level.Log.
    """
    if _LOG is not None:
        _LOG.log(message, level)


def error(message):
    """log a message as an error with the global logger

    Args:
        message (any): the message to log
    """
    log(message, Level.Error)


def warn(message):
    """log a message as a warning with the global logger

    Args:
        message (any): the message to log
    """
    log(message, Level.Warning)


def info(message):
    """log a message as info with the global logger

    Args:
        message (any): the message to log
    """
    log(message, Level.Info)


def debug(message):
    """log a message for debugging with the global logger

    Args:
        message (any): the message to log
    """
    log(message, Level.Debug)
