#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""

Log manager.
Initializes logger from logging module
Authors: Jose V., Matthias K.

"""

import logging


class Formatter(logging.Formatter):
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


HANDLER = logging.StreamHandler()
HANDLER.setFormatter(Formatter())
logging.basicConfig(handlers=[HANDLER], level=logging.WARNING)
LOG = logging.getLogger()
LOG.addHandler(HANDLER)


def set_verbose() -> None:
    """Function used to set LOG object logging level to INFO"""
    LOG.setLevel(logging.INFO)


def set_debug() -> None:
    """Function used to set LOG object logging level to INFO"""
    LOG.setLevel(logging.DEBUG)
