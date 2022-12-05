#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""

Metadata archive extractor example.
Tested with Python 3.8.10
Author: Jose V.

"""

from pathlib import Path
from zipfile import is_zipfile
from tarfile import is_tarfile

from . import decompressing_procedures as dprc


def formats() -> list:
    """
    Get function acceptable archive formats.

    Returns:
        List of acceptable archive formats.
    """

    return list(dprc.PROCEDURES.keys())


def check_archive(file_path: str):
    """
    Checks if file in path is archive.
    Acceptable formats are stored in ARCHIVE_FORMATS.
    Stops execution if archive is in wrong format.

    Args:
        file_path: String path to archive.

    Returns:
        Path object to archive.
    """

    path = Path(file_path)

    assert path.is_file(), f"Incorrect path to archive {file_path}"

    is_z = is_zipfile(path)
    is_t = is_tarfile(path)

    assert is_z or is_t

    return path, "zip" if is_z else "tar"


def decompress(archive_path: Path,
               archive_type: str,
               dc_dir_path: Path,
               members: list = None,
               verb: bool = False):
    """
    Extracts archive using extraction rules.
    This function is called from the main python file where the check_archive
    was previously used.
    No additional check needed.

    Args:
        archive_path: Path object to archive.
        archive_type: String type of archive.
        dc_dir_path: Path object to decompression directory.
        members: list of members of archive to extract, None if extract all.
        verb: Boolean to control verbose output.
    """

    if verb:
        if members is not None:
            print(f"Decompressing files: {members}")
        else:
            print(f"Decompressing archive: {archive_path.name}")

    dprc.PROCEDURES[archive_type](archive_path, dc_dir_path, members)
