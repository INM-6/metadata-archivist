#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""

Module containing collection of rules as functions to export structured metadata.

Export rules defined for the Exporter,
rules can be customized or added through
the INTERPRETATION_RULES dictionary.

All rule functions must have the same arguments.

Arguments:
    export_object: dict object to export.
    outfile: Path object to target file.

exports:
    EXPORT_RULES: dictionary mapping format to export rule.

Authors: Jose V., Matthias K.

"""

import logging

from pathlib import Path
from typing import Callable
from json import dump as j_dump
from pickle import dump as p_dump, HIGHEST_PROTOCOL


LOG = logging.getLogger(__name__)

try:
    from yaml import dump as y_dump
except ImportError:

    def y_dump(*args, **kwargs):
        """Mock yaml dump function when PyYAML not found."""
        raise ModuleNotFoundError("PyYAML package was not found in environment.")


def _export_yaml(export_object: dict, outfile: Path) -> None:
    # Exports YAML object to file.

    LOG.debug("   exporting YAML to file '%s'", str(outfile))

    with outfile.open("w", encoding="utf-8") as f:
        y_dump(export_object, f, sort_keys=False)


def _export_pickle(export_object: dict, outfile: Path) -> None:
    # Pickles object to file.

    LOG.debug("   exporting pickle to file '%s'", str(outfile))

    with outfile.open("wb", encoding=None) as f:
        p_dump(export_object, f, protocol=HIGHEST_PROTOCOL)


def _export_json(export_object: dict, outfile: Path) -> None:
    # Exports JSON export_object to file.

    LOG.debug("   exporting JSON to file '%s'", str(outfile))

    with outfile.open("w", encoding="utf-8") as f:
        j_dump(export_object, f, indent=4)


EXPORT_RULES = {
    "JSON": _export_json,
    "PICKLE": _export_pickle,
    "YAML": _export_yaml,
}


def register_export_rule(format_name: str, rule: Callable) -> None:
    """
    Function to register new rules in the EXPORT_RULES dictionary.

    Arguments:
        format_name: string name of format to export.
        rule: callable rule to export to new format.
    """

    if format_name in EXPORT_RULES:
        raise KeyError("Export rule already exists")

    EXPORT_RULES[format_name] = rule
