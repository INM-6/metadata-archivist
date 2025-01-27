#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""

Orchestration of metadata parsing, formatting, and exporting example,
with more complex metadata.

Requires f90nml.

Authors: Matthias K., Jose V.

"""

import sys
import logging

from pathlib import Path
from json import load, dumps
from argparse import ArgumentParser

from metadata_archivist import Archivist
from my_parser import nml_parser


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
    config_path = Path(__file__).resolve().parent / "config.json"
    if not config_path.is_file():
        raise FileNotFoundError(f"No config file at: {config_path}")

    with config_path.open("r") as f:
        config = load(f)

    arch = Archivist(path="metadata_archive.tar", parsers=nml_parser(), **config)

    arch.parse()
    arch.export()

    LOG.info("Resulting metadata:\n%s", dumps(arch.get_metadata(), indent=4))
