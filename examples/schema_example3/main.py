#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""

Minimal orchestration of metadata parsing, formatting, and exporting example.
Uses custom schema to do patternProperties with nested properties structuring of output.

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
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "description": "my example schema 3",
    "type": "object",
    "properties": {
        "metadata_archive": {
            "type": "object",
            "patternProperties": {
                "^basin_.*": {
                    "type": "object",
                    "properties": {
                        "basin_characteristics": {"$ref": "#/$defs/basin_character_parser"},
                        "simulation": {
                            "type": "object",
                            "properties": {
                                "time_info": {"$ref": "#/$defs/time_parser"},
                                "model_configuration": {"$ref": "#/$defs/yml_parser"},
                            },
                        },
                    },
                },
                "^station_.*": {
                    "type": "object",
                    "properties": {
                        "basin_characteristics": {"$ref": "#/$defs/station_character_parser"},
                        "simulation": {
                            "type": "object",
                            "properties": {
                                "time_info": {"$ref": "#/$defs/time_parser"},
                                "model_configuration": {"$ref": "#/$defs/yml_parser"},
                            },
                        },
                    },
                },
            },
        },
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
        verbosity=args.verbosity,
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
