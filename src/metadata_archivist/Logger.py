#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Log manager.
Initializes logger from logging module
and sets custom message formatter.

exports:
    LOG: logger object, default logging level: warning
    set_level: function to change logging level of LOG object
    is_debug: function to test DEBUG level of LOG object

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
logging.basicConfig(handlers=[_HANDLER], level=logging.WARNING)
LOG = logging.getLogger()
LOG.addHandler(_HANDLER)

def set_level(level: str) -> None:
    """
    Function used to set LOG object logging level.

    Arguments:
        level: logging level as string, available levels: info, debug
    """
    if level == "info":
        LOG.setLevel(logging.INFO)
    elif level == "debug":
        LOG.setLevel(logging.DEBUG)
    else:
        LOG.warning(f"Incorrect logging level: {level}")


def is_debug() -> bool:
    """Status function which returns true if logging level is defined to DEBUG"""
    return LOG.level == logging.DEBUG
