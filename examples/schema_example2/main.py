#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""

Minimal orchestration of metadata parsing, formatting, and exporting example.
Uses custom schema to do patternProperties structuring of output.

Requires PyYAML.

Authors: Matthias K., Jose V.

"""

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


arg_parser = ArgumentParser()
arg_parser.add_argument("--verbosity", type=str, default="info")
args = arg_parser.parse_args()


my_schema = {
    "$schema": "https://abc",
    "$id": "https://abc.json",
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


if __name__ == "__main__":
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
        verbose=args.verbosity,
        add_description=True,
        add_type=True,
    )

    arch.parse()
    arch.export()

    print("\nResulting schema:")
    formatted_schema = arch.get_formatted_schema()
    print(dumps(formatted_schema, indent=4))
    with Path("schema.json").open("w") as f:
        dump(formatted_schema, f, indent=4)

    print("\nResulting metadata:")
    print(dumps(arch.get_metadata(), indent=4))
