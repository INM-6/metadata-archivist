#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""

Orchestration of metadata parsing, formatting, and exporting example,
with more complex metadata.

Requires f90nml.

Authors: Matthias K., Jose V.

"""

from pathlib import Path
from json import load, dumps
from argparse import ArgumentParser

from metadata_archivist import Archivist
from my_parser import nml_parser


arg_parser = ArgumentParser()
arg_parser.add_argument("--verbosity", type=str, default="info")
args = arg_parser.parse_args()


if __name__ == "__main__":
    config_path = Path(__file__).parent.resolve() / "config.json"
    if not config_path.is_file():
        raise FileNotFoundError(f"No config file at: {config_path}")

    with config_path.open("r") as f:
        config = load(f)
    config["verbose"] = args.verbosity

    arch = Archivist(path="metadata_archive.tar", parsers=nml_parser(), **config)

    arch.parse()
    arch.export()

    print("\nResulting metadata:")
    print(dumps(arch.get_metadata(), indent=4))
