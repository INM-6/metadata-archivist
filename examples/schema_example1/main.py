#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""

Minimal orchestration of metadata parsing, formatting, and exporting example.
Uses custom schema to do simple structuring of output.

Requires PyYAML.

Authors: Matthias K., Jose V.

"""

from metadata_archivist import Archivist
from my_parsers import time_parser, yml_parser
from pathlib import Path
from json import dumps, dump


my_schema = {
    '$schema': 'https://abc',
    '$id': 'https://abc.json',
    'description': 'my example schema',
    'type': 'object',
    'properties': {
        'metadata_archive': {
            'type': 'object',
            'properties': {
                'program_execution': {
                    'type': 'object',
                    'properties': {
                        'time_info': {
                            '$ref': '#/$defs/time_parser'
                        },
                        'model_configuration': {
                            '$ref': '#/$defs/yml_parser'
                        },
                    }
                },
            },
        },
    }
}


if __name__ == "__main__":
    arch = Archivist(path='metadata_archive.tar',
                    parsers=[time_parser(), yml_parser()],
                    schema=my_schema,
                    extraction_directory='tmp',
                    output_directory="./",
                    output_file="metadata.json",
                    overwrite=True,
                    auto_cleanup=True,
                    verbose='info')

    arch.parse()
    arch.export()

    print("\nResulting schema:")
    formatted_schema = arch.get_formatted_schema()
    print(dumps(formatted_schema, indent=4))
    with Path("schema.json").open("w") as f:
        dump(formatted_schema, f, indent=4)

    print("\nResulting metadata:")
    print(dumps(arch.get_metadata(), indent=4))
