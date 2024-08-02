#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Explorer class for retrieving files from compressed archives or directories.

exports:
    Explorer class

Authors: Jose V., Matthias K.
"""

from pathlib import Path
from functools import partial
from zipfile import is_zipfile
from collections.abc import Callable
from tarfile import is_tarfile, open as t_open
from typing import Optional, List, Tuple, NoReturn, Union

from .Logger import LOG
from .helper_functions import _pattern_parts_match


# Accepted archive file formats
_ACCEPTED_FORMATS = [
    "tgz",
    "tar",
    "tar.gz"
]


class Explorer:
    """
    Class for exploring an archive or directory and filtering out files needed for parsing.
    Filtering is based on target file patterns provided by parser objects.
    If exploring an archive, targets are decompressed in a temporary director,
    path to temp files are returned as exploration results and Archivist class automatically
    cleans them up.

    Attributes:
        path_is_archive: True if exploration target is an archive type.
        path: string of path to exploration target.
        config: Dictionary containing configuration parameters

    Methods:
        explore: exploration procedure on either archive or directory
    """

    def __init__(self,
                 path: str,
                 config: dict) -> None:
        self.path = path
        self.config = config

    @property
    def path(self) -> Path:
        """Returns path to archive."""
        return self._path

    @path.setter
    def path(self, path: str) -> None:
        """Sets new archive path after checking type."""

        if not isinstance(path, str):
            raise TypeError(f"Incorrect type format for file path: {path!r}")

        path = Path(path)
        
        if path.is_dir():
            self.explore = partial(_dir_explore, directory_path=path)
            self.path_is_archive = False
        else:
            self.explore = _check_archive(path, self.config["extraction_directory"])
            self.path_is_archive = True

        self._path = path


def _check_archive(file_path: Path, extraction_path: Path) -> Tuple[Path, Callable]:
    """
    Internal method to check archive format.
    If archive is in correct format then path to archive and decompression method are returned.

    Arguments:
        file_path: Path object to file.
        extraction_path: Path object to extraction directory.

    Returns:
        callable method to decompress corresponding archive type.
    """

    if not file_path.is_file():
        raise FileNotFoundError(f"Incorrect path to file: {file_path}")

    if is_zipfile(file_path):
        raise NotImplementedError("ZIP extractor not yet implemented")
    elif is_tarfile(file_path):
        decompress_method = partial(_decompress_tar, archive_path=file_path, extraction_path=extraction_path)
    else:
        raise RuntimeError(f'Unknown archive format: {file_path.name}')

    # Returning file path is used for protected set method of internal _archive_path attribute.
    return decompress_method


def _decompress_tar(output_file_patterns: List[str],
                    archive_path: Path,
                    extraction_path: Path) -> Tuple[Path, List[Path], List[Path]]:
    """
    Decompresses files found in archive pointed by self.path.
    If an archive is found inside then operation is recursively called on it.

    Arguments:
        output_file_patterns: list of string of patterns of files to decompress.
        archive_path: Path object of archive to decompress.
        extraction_path: Path object of extraction directory.

    Returns:
        triplet containing:
            0. Path object of root decompression directory (extraction directory / archive name).
            1. list of Path objects of decompressed directories.
            2. list of Path objects of decompressed files.
    """

    LOG.info(f"Decompression of archive: {archive_path.name}")

    archive_name = archive_path.stem.split(".")[0]
    directory_path = extraction_path.joinpath(archive_name)
    explored_dirs = [directory_path]
    explored_files = []

    with t_open(archive_path) as t:
        item = t.next()
        while item is not None:
            if item.isfile():
                LOG.info(f"    processing file: {item.name}")
                item_path = directory_path.joinpath(item.name)
                if any(item.name.endswith(format)
                        for format in _ACCEPTED_FORMATS):
                    t.extract(item, path=directory_path)
                    _, new_explored_dirs, new_explored_files = _decompress_tar(output_file_patterns,
                                                    archive_path=item_path,
                                                    extraction_path=directory_path)
                    # Reverse ordering of dirs to correctly remove them
                    explored_dirs.extend(new_explored_dirs)
                    explored_files.extend(new_explored_files)
                    item_path.unlink()

                elif any(_pattern_parts_match(list(reversed(pat.split("/"))),
                                            list(reversed(item.name.split("/"))))
                        for pat in output_file_patterns):
                    t.extract(item, path=directory_path)
                    explored_files.append(item_path)
                    explored_dirs.append(item_path.parent)
            item = t.next()

    # Returned paths are used for parsing and automatic clean-up.
    return directory_path, explored_dirs, explored_files


def _dir_explore(output_file_patterns: List[str],
                 directory_path: Path) -> Tuple[Path, List[Path], List[Path]]:
    """
    Explores given directory while matching files and recursing over sub-directories
    Paths are assumed to be checked before call.

    Arguments:
        output_file_patterns: list of string of patterns of files to decompress.
        directory_path: Path object of exploration directory.

    Returns:
        triplet containing:
            0. Path object of explored directory.
            1. list of Path objects of explored directories.
            2. list of Path objects of explored files.
    """

    LOG.info(f"Exploration of directory: {directory_path.name}")

    explored_dirs = [directory_path]
    explored_files = []

    for item_path in directory_path.glob("*"):
        if item_path.is_file():
            LOG.info(f"    processing file: {item_path.name}")
            # TODO: think about precompiling patterns to optimize regex match time
            if any(_pattern_parts_match(list(reversed(pat.split("/"))),
                                        list(reversed(item_path.parts)))
                    for pat in output_file_patterns):
                explored_files.append(item_path)
                explored_dirs.append(item_path.parent)
        else:
            _, new_explored_dirs, new_explored_files = _dir_explore(output_file_patterns, item_path)
            # Reverse ordering of dirs to correctly remove them
            explored_dirs.extend(new_explored_dirs)
            explored_files.extend(new_explored_files)

    # Returned paths are used for parsing and automatic clean-up.
    return directory_path, explored_dirs, explored_files
