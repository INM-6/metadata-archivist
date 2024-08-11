#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Log manager.
Initializes logger from logging module
and sets custom message formatter.

Only for internal use.

Authors: Jose V., Matthias K.
"""

import logging


class _LogFormatter(logging.Formatter):
    """
    Specialization of logging module Formatter class.
    Designed to have a specific format style depending on record level.
    """

    def format(self, record):
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
_LOG = logging.getLogger()
_LOG.addHandler(_HANDLER)


def _set_level(level: str) -> bool:
    """
    Function used to set LOG object logging level.

    Arguments:
        level: logging level as string, available levels: warning, info, debug

    Returns:
        success boolean
    """
    if level == "warning":
        _LOG.setLevel(logging.WARNING)
    elif level == "info":
        _LOG.setLevel(logging.INFO)
    elif level == "debug":
        _LOG.setLevel(logging.DEBUG)
    else:
        _LOG.warning(f"Trying to set incorrect logging level: {level}, staying at current level.")
        return False
    
    return True


def _is_debug() -> bool:
    """Status function which returns true if logging level is defined to DEBUG"""
    return _LOG.level == logging.DEBUG
