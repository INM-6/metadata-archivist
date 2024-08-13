#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""

Metadata parsing, collection and save pipeline example.
Authors: Matthias K., Jose V.

"""

from json import load, dumps, dump
from pathlib import Path

from my_parsers import time_parser, yml_parser
from metadata_archivist import Archivist


if __name__ == "__main__":
    config_path = Path(__file__).parent.resolve() / "config.json"
    if not config_path.is_file():
        raise FileNotFoundError(f"No config file at: {config_path}")

    with config_path.open("r") as f:
        config = load(f)

    arch = Archivist(path=Path('metadata_archive.tar'),
                    parsers=[time_parser(), yml_parser()],
                    **config)

    arch.parse()
    arch.export()

    print("\nResulting schema:")
    print(dumps(arch._formatter.schema, indent=4))
    with Path("schema.json").open("w") as f:
        dump(arch._formatter.schema, f, indent=4)

    print("\nResulting metadata:")
    print(dumps(arch.get_metadata(), indent=4))
