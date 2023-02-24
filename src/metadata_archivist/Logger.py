#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""

Custom Formatter class.
Initializes logger from logging module
Author: Kelbling, M., Jose V.

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
