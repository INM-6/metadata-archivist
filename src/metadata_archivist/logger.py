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

import sys
import logging

_stderr = logging.StreamHandler(stream=sys.stderr)

_simple_format = logging.Formatter("%(levelname)s : %(message)s")
_info_format = logging.Formatter("%(levelname)s : %(module)s : %(message)s")
_full_format = logging.Formatter(
    "\n%(name)s | %(asctime)s | %(levelname)s : %(levelno)s | %(filename)s : %(funcName)s : %(lineno)s | %(processName)s : %(process)d | %(message)s\n"
)

LOG = logging.getLogger(__name__)
LOG.addHandler(_stderr)
LOG.setLevel(logging.INFO)


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
        _stderr.setFormatter(_simple_format)
    elif level == "info":
        LOG.setLevel(logging.INFO)
        _stderr.setFormatter(_info_format)
    elif level == "debug":
        LOG.setLevel(logging.DEBUG)
        _stderr.setFormatter(_full_format)
    else:
        LOG.warning(
            "Trying to set incorrect logging level '%s', staying at current level.",
            level,
        )
        return False

    return True


def is_debug() -> bool:
    """Status function which returns true if logging level is defined to DEBUG."""
    return LOG.level == logging.DEBUG
