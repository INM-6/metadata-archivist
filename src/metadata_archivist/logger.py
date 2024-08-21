#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""

Internally used logging class extension.

Initializes logger from logging module.
Sets custom message formatter.

exports:
    LOG: logging object.
    set_level: function to change logging level via strings.
    is_debug: function to test if logging object is in debug level.

Authors: Jose V., Matthias K.

"""

import logging


class _LogFormatter(logging.Formatter):
    """
    Specialization of logging module Formatter class.
    Designed to have a specific format style depending on record level.
    """

    def format(self, record) -> str:
        if record.levelno == logging.INFO:
            self._style._fmt = "%(message)s"
        elif record.levelno == logging.DEBUG:
            self._style._fmt = "%(levelname)s: %(message)s"
        else:
            self._style._fmt = "\n%(levelname)s: %(message)s\n"
        return super().format(record)


_HANDLER = logging.StreamHandler()
_HANDLER.setFormatter(_LogFormatter())
logging.basicConfig(handlers=[_HANDLER], level=logging.INFO)
LOG = logging.getLogger()
LOG.addHandler(_HANDLER)


def set_level(level: str) -> bool:
    """
    Function used to set LOG object logging level.

    Arguments:
        level: logging level as string, available levels: warning, info, debug.

    Returns:
        success boolean.
    """
    if level == "warning":
        LOG.setLevel(logging.WARNING)
    elif level == "info":
        LOG.setLevel(logging.INFO)
    elif level == "debug":
        LOG.setLevel(logging.DEBUG)
    else:
        LOG.warning(
            "Trying to set incorrect logging level: %s, staying at current level.",
            level,
        )
        return False

    return True


def is_debug() -> bool:
    """Status function which returns true if logging level is defined to DEBUG."""
    return LOG.level == logging.DEBUG
