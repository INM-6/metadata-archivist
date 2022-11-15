#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""

Metadata directory collector example.
Tested with Python 3.8.10
Author: Jose V.

"""

from pathlib import Path

from . import parsing_procedures as pprc


def formats() -> list:
    """
    Get function for parsable metadata files.

    Returns:
        List of parsable metadata file.
    """

    return list(pprc.PROCEDURES.keys())


def parse_file(file_path: Path,
               mode: str,
               module=None,
               rm: bool = False,
               verb: bool = False) -> dict:
    """
    Gets file data through parsing rules.

    Args:
        file_path: Path object to extracted file.
        mode: String of parsing rules mode. Either "standard" or "overwrite".
        module: Module containing parsing rules to be used in "overwrite" mode. None if "standard" mode.
        rm: Boolean to control delete operation.
        verb: Boolean to control verbose output.

    Returns:
        Dictionary with file data.
    """

    assert file_path.is_file(
    ), f"Error collecting data, incorrect path: {file_path}"
    if mode == "standard":
        assert file_path.name in pprc.PROCEDURES, f"Error collecting metadata, unknown file type: {file_path}"
    else:
        assert file_path.name in pprc.PROCEDURES or file_path.name in module.RULES

    if verb:
        print(f"Collecting metadata from file: {file_path.name}")

    standard_parse = True
    if mode == "overwrite":
        if file_path.name in module.RULES:
            res = module.RULES[file_path.name](fp=file_path)
            standard_parse = False

    if standard_parse:
        res = pprc.PROCEDURES[file_path.name](fp=file_path)
        #res = crl.file_ref_parser(file_path)

    if rm:
        file_path.unlink()

    return res


def parse_data(dc_dir_path: Path,
               data_dict: dict,
               mode: str,
               module=None,
               rm: bool = False,
               verb: bool = False) -> dict:
    """
    Recursively creates a nested dictionary containing parsed data in archive.

    Args:
        dc_dir_path: Path object to decompressed archive directory.
        data_dict: Dictionary containing data in archive.
        mode: String of parsing rules mode. Either "standard" or "overwrite".
        module: Module containing parsing rules to be used in "overwrite" mode.
                None if "standard" mode.
        rm: Boolean to control delete operation.
        verb: Boolean to control verbose output.
    """

    assert dc_dir_path.is_dir(
    ), f"Error collecting metadata, incorrect path: {dc_dir_path}"

    if verb:
        print(f"Collecting metadata from directory: {dc_dir_path}")

    for child in dc_dir_path.iterdir():
        if child.is_dir():
            new_data = {}
            parse_data(child, new_data, mode, module, rm=rm, verb=verb)
            data_dict[child.stem.split(".")[0]] = new_data
        else:
            data_dict[child.name] = parse_file(child,
                                               mode,
                                               module,
                                               rm=rm,
                                               verb=verb)

    if rm:
        dc_dir_path.rmdir()
