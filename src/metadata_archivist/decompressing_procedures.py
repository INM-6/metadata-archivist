#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""

Metadata archive extraction rules example.
Tested with Python 3.8.10
Author: Jose V.

"""

import zipfile
import tarfile

from pathlib import Path


def is_archive(file_path: Path) -> str:
    """
    Evaluates if file in path is an archive in correct ARCHIVE_FORMATS.
    Returns even if file is in incorrect format.

    Args:
        file_path: Path object to file.

    Returns:
        String type of archive, None if not an archive.
    """

    if file_path.is_file():
        is_z = zipfile.is_zipfile(file_path)
        is_t = tarfile.is_tarfile(file_path)

        if is_z or is_t:
            return "zip" if is_z else "tar"
    else:
        return None


def decompress_directory_nested(directory_path: Path):
    """
    Iterates over directory recursively and decompresses archive files inside
    tree Paths are assumed to be checked before call.

    Args:
        directory_path: Path object to directory.
    """

    for child in directory_path.iterdir():
        if child.is_dir():
            decompress_directory_nested(child)
        else:
            arch_type = is_archive(child)
            if arch_type is not None:
                PROCEDURES[arch_type](child, directory_path)
                child.unlink()


def decompress_tar_nested(archive_path: Path, dc_dir_path: Path):
    """
    Recursively unpacks nested archive in the decompression directory.
    Paths are assumed to be checked before call.

    Args:
        archive_path: Path object to archive.
        dc_dir_path: Path object to decompression directory.
    """

    archive_name = archive_path.stem.split(".")[0]
    new_path = dc_dir_path.joinpath(archive_name)

    with tarfile.open(archive_path) as t:
        t.extractall(path=new_path)

    assert new_path.is_dir(), f'''Error during extraction: {new_path} is not a
directory containing extracted archive.'''

    decompress_directory_nested(new_path)


def decompress_tar_members(archive_path: Path, dc_dir_path: Path,
                           members: list):
    """
    Decompresses files of archive in members list.
    If another archive is found then operation is called on it.
    Members are assumed to be files, if members are archives they will
    NOT be unpacked.
    Paths are assumed to be checked before call.

    Args:
        archive_path: Path object to archive.
        dc_dir_path: Path object to decompression directory.
        members: list of members of archive to extract, None if extract all.
    """

    archive_name = archive_path.stem.split(".")[0]
    new_path = dc_dir_path.joinpath(archive_name)

    with tarfile.open(archive_path) as t:
        item = t.next()
        while item is not None:
            if any(name in item.name for name in members):
                t.extract(item, path=new_path)
            # TODO: Find better way to infer if a TarInfo object is an archive
            elif any(item.name.endswith(format) for format in TAR_FORMATS):
                t.extract(item, path=new_path)
                new_archive = new_path.joinpath(item.name)
                decompress_tar_members(new_archive, new_archive.parent,
                                       members)
                new_archive.unlink()

            item = t.next()


def decompress_tar(archive_path: Path,
                   dc_dir_path: Path,
                   members: list = None):
    """
    Decompresses tar archive.
    If no members list is given then a recursive extraction of
    all files is done.

    Args:
        archive_path: Path object to archive.
        dc_dir_path: Path object to decompression directory.
        members: list of members of archive to extract, None if extract all.
    """

    if members is None:
        decompress_tar_nested(archive_path, dc_dir_path)
    else:
        decompress_tar_members(archive_path, dc_dir_path, members)


def decompress_zip(*_, **__):
    raise NotImplementedError("ZIP decompressor not yet implemented")


PROCEDURES = {"zip": decompress_zip, "tar": decompress_tar}
