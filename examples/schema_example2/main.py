#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""

Minimal orchestration of metadata parsing, formatting, and exporting example.
Uses custom schema to do patternProperties structuring of output.

Requires PyYAML.

Authors: Matthias K., Jose V.

"""

import sys
import logging

from pathlib import Path
from json import dumps, dump
from argparse import ArgumentParser

from metadata_archivist import Archivist
from my_parsers import (
    time_parser,
    yml_parser,
    station_character_parser,
    basin_character_parser,
)


stderr = logging.StreamHandler(stream=sys.stderr)

simple_format = logging.Formatter("%(levelname)s : %(message)s")
info_format = logging.Formatter("%(levelname)s : %(module)s : %(message)s")
full_format = logging.Formatter(
    "\n%(name)s | %(asctime)s | %(levelname)s : %(levelno)s |"
    + " %(filename)s : %(funcName)s : %(lineno)s | %(processName)s : %(process)d | %(message)s\n"
)

LOG = logging.getLogger(__name__)

arg_parser = ArgumentParser()
arg_parser.add_argument("--verbosity", type=str, default="info")
args = arg_parser.parse_args()

my_schema = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "description": "my example schema 2",
    "type": "object",
    "properties": {
        "metadata_archive": {
            "type": "object",
            "patternProperties": {
                "^basin_.*": {
                    "!varname": "basin",
                    "type": "object",
                    "description": "some description",
                    "properties": {
                        "basin_information": {
                            "!parsing": {
                                "path": ".*/{basin}/basin.yml",
                                "keys": ["river", "size"],
                            },
                            "$ref": "#/$defs/basin_character_parser",
                        },
                    },
                },
                "^station_.*": {
                    "!varname": "station",
                    "type": "object",
                    "properties": {
                        "station_information": {
                            "!parsing": {
                                "path": ".*/{station}/station.yml",
                                "keys": ["river", "mean_disch"],
                            },
                            "$ref": "#/$defs/station_character_parser",
                        },
                    },
                },
            },
        }
    },
}


def set_level(level: str) -> None:
    """
    Function used to set LOG object logging level.

    Arguments:
        level: logging level as string, available levels: warning, info, debug.

    Returns:
        success boolean.
    """
    if level == "warning":
        stderr.setFormatter(simple_format)
        logging.basicConfig(level=logging.WARNING, handlers=(stderr,))
    elif level == "info":
        stderr.setFormatter(info_format)
        logging.basicConfig(level=logging.INFO, handlers=(stderr,))
    elif level == "debug":
        stderr.setFormatter(full_format)
        logging.basicConfig(level=logging.DEBUG, handlers=(stderr,))
    else:
        raise ValueError("Incorrect logging level %s", level)


if __name__ == "__main__":
    set_level(args.verbosity)
    arch = Archivist(
        path="metadata_archive.tar",
        parsers=[
            time_parser(),
            yml_parser(),
            station_character_parser(),
            basin_character_parser(),
        ],
        schema=my_schema,
        extraction_directory="tmp",
        output_directory="./",
        output_file="metadata.json",
        overwrite=True,
        auto_cleanup=True,
        add_description=True,
        add_type=True,
    )

    arch.parse()
    arch.export()

    formatted_schema = arch.get_formatted_schema()
    LOG.info("Resulting schema:\n%s", dumps(formatted_schema, indent=4))
    with Path("schema.json").open("w") as f:
        dump(formatted_schema, f, indent=4)

    LOG.info("Resulting metadata:\n%s", dumps(arch.get_metadata(), indent=4))
