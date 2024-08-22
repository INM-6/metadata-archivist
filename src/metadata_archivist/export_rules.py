#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""

Module containing collection of rules as functions to export structured metadata.

Export rules defined for the Exporter,
rules can be customized or added through
the INTERPRETATION_RULES dictionary.

All rule functions must have the same arguments.

Arguments:
    object: dict object to export.
    outfile: Path object to target file.

exports:
    EXPORT_RULES: dictionary mapping format to export rule.

Authors: Jose V., Matthias K.

"""

from pathlib import Path
from json import dump as j_dump
from pickle import dump as p_dump, HIGHEST_PROTOCOL

from metadata_archivist.logger import LOG

try:
    from yaml import dump as y_dump
except ImportError:

    def y_dump(*args, **kwargs):
        """Mock yaml dump function when PyYAML not found."""
        raise ModuleNotFoundError("PyYAML package was not found in environment.")


def _export_yaml(object: dict, outfile: Path) -> None:
    """
    Exports YAML object to file.

    Arguments:
        object: dict object to export.
        outfile: Path object to target file.
    """

    LOG.debug("   exporting YAML to file: %s", str(outfile))

    with outfile.open("w", encoding="utf-8") as f:
        y_dump(object, f, sort_keys=False)


def _export_pickle(object: dict, outfile: Path) -> None:
    """
    Pickles object to file.

    Arguments:
        object: dict object to export.
        outfile: Path object to target file.
    """

    LOG.debug("   exporting pickle to file: %s", str(outfile))

    with outfile.open("wb", encoding=None) as f:
        p_dump(object, f, protocol=HIGHEST_PROTOCOL)


def _export_json(object: dict, outfile: Path) -> None:
    """
    Exports JSON object to file.

    Arguments:
        object: dict object to export.
        outfile: Path object to target file.
    """

    LOG.debug("   exporting JSON to file: %s", str(outfile))

    with outfile.open("w", encoding="utf-8") as f:
        j_dump(object, f, indent=4)


EXPORT_RULES = {
    "JSON": _export_json,
    "PICKLE": _export_pickle,
    "YAML": _export_yaml,
    }
