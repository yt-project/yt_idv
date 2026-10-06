import logging
import os

if hasattr(logging, "getLevelNamesMapping"):
    _LOG_LEVEL_MAPPING = logging.getLevelNamesMapping()
else:
    # getLevelNamesMapping introduced in python 3.11
    _LOG_LEVEL_MAPPING = {
        "CRITICAL": 50,
        "FATAL": 50,
        "ERROR": 40,
        "WARNING": 30,
        "WARN": 30,
        "INFO": 20,
        "DEBUG": 10,
        "NOTSET": 0,
    }


ytidv_log = logging.getLogger("yt_idv")

_formatter = logging.Formatter("%(name)s : [%(levelname)s ] %(asctime)s:  %(message)s")


def _valid_level(level: int | str):
    if isinstance(level, str):
        level = level.upper()
    return level in _LOG_LEVEL_MAPPING or level in _LOG_LEVEL_MAPPING.values()


def set_log_level(level: int | str) -> None:
    """
    Set the minimum level of messages that yt_idv will log.

    Parameters
    ----------
    level: int or str
        A standard logging level, e.g. 10 or "debug", 20 or "info",
        30 or "warning", 40 or "error", 50 or "critical". "all" is a
        non-standard alias for 1 (everything).
    """
    if not _valid_level(level):
        raise ValueError(
            f"{level} must be a valid log level string or integer: {_LOG_LEVEL_MAPPING}"
        )
    ytidv_log.setLevel(level)
    ytidv_log.debug("Set log level to %s", level)


if not ytidv_log.handlers:
    _stream_handler = logging.StreamHandler()
    _stream_handler.setFormatter(_formatter)
    ytidv_log.addHandler(_stream_handler)
    ytidv_log.propagate = False
    _env_level = os.environ.get("YT_IDV_LOG_LEVEL", "INFO")
    try:
        set_log_level(_env_level)
    except ValueError:
        set_log_level(logging.INFO)
        ytidv_log.warning(
            "Ignoring invalid YT_IDV_LOG_LEVEL=%r, using INFO", _env_level
        )
