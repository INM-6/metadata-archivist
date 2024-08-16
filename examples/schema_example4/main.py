#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""

Minimal orchestration of metadata parsing, formatting, and exporting example.
Uses custom schema to do calculate directive structuring of output.

Requires PyYAML.

Authors: Matthias K., Jose V.

"""

from metadata_archivist import Archivist
from my_parsers import time_parser, yml_parser
from pathlib import Path
from json import dumps, dump


my_schema = {
    "$schema": "https://abc",
    "$id": "https://abc.json",
    "description": "my example schema",
    "type": "object",
    "properties": {
        "real_time_factor": {
            "type": "number",
            "description": "ratio of wall clock time to simulation time",
            "!calculate": {
                "expression": "{val1} / {val2}",
                "variables": {
                    "val1": {
                        "!parsing": {"keys": ["real"], "unpack": 1},
                        "$ref": "#/$defs/time_parser",
                    },
                    "val2": {
                        "!parsing": {"keys": ["parameters/sim_time"], "unpack": 2},
                        "$ref": "#/$defs/yml_parser",
                    },
                },
            },
        },
        "model": {
            "!parsing": {"keys": ["parameters/scale"], "unpack": 1},
            "$ref": "#/$defs/yml_parser",
        },
        "virtual_processes": {
            "type": "number",
            "description": "total number of digital processing units i.e. #MPI * #threads",
            "!calculate": {
                "expression": "{val1} * {val2}",
                "variables": {
                    "val1": {
                        "!parsing": {"keys": ["parameters/num_procs"], "unpack": True},
                        "$ref": "#/$defs/yml_parser",
                    },
                    "val2": {
                        "!parsing": {
                            "keys": ["parameters/threads_per_proc"],
                            "unpack": True,
                        },
                        "$ref": "#/$defs/yml_parser",
                    },
                },
            },
        },
    },
}


if __name__ == "__main__":
    arch = Archivist(
        path="raw_metadata",
        parsers=[time_parser(), yml_parser()],
        schema=my_schema,
        output_directory="./",
        output_file="metadata.json",
        overwrite=True,
        lazy_load=True,
        auto_cleanup=True,
        verbose="info",
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
