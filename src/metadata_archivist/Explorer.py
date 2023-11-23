#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""

Explorer class for retrieving files from compressed archives or directories.
Authors: Jose V., Matthias K.

"""

import zipfile
import tarfile

from pathlib import Path
from collections.abc import Callable
from typing import Optional, List, Tuple, NoReturn, Union

from .Logger import LOG
from .helper_functions import _pattern_parts_match

class Explorer():
    """
    Class containing all methods around processing compressed archives

    Main purposes in the framework:
    - receive list of re.patterns
    - send path to decompression directories and paths to decompressed files
    """

    def __init__(self,
                 path: Path,
                 config: dict) -> None:
        # Private
        self._path_is_archive = False

        # Public
        self.path = path
        self.config = config

    @property
    def path_is_archive(self) -> Callable:
        """Returns true if defined path points to archive."""
        return self._path_is_archive
    
    @path_is_archive.setter
    def explore(self, _) -> NoReturn:
        """
        Forbidden setter for is_archive attribute.
        (pythonic indirection for protected attributes)
        """
        raise AttributeError("is_archive property can only be set through archive path checking")

    @property
    def path(self) -> Path:
        """Returns path to archive (Path)."""
        return self._path

    @path.setter
    def path(self, file_path: Union[str, Path]) -> None:
        """Sets new archive path after checking."""

        if isinstance(file_path, str):
            file_path = Path(file_path)
        elif not isinstance(file_path, Path):
            raise TypeError(f"Incorrect type format for file path: {file_path!r}")
        
        if file_path.is_dir():
            self._path, self._explore = file_path, self._dir_explore
            self._path_is_archive = False
        else:
            self._path, self._explore = self._check_archive(file_path)
            self._path_is_archive = True

    @property
    def explore(self) -> Callable:
        """Returns appropriate explore function wrt. path type."""
        return self._explore
    
    @explore.setter
    def explore(self, _) -> NoReturn:
        """
        Forbidden setter for explore attribute.
        (pythonic indirection for protected attributes)
        """
        raise AttributeError("decompress method can only be set through archive path checking")

    def _check_archive(self, file_path: Path) -> Tuple[Path, Callable]:
        """
        Internal method to check archive format.
        If archive is in correct format then path to archive and decompression method are returned.
        """

        if not file_path.is_file():
            raise FileNotFoundError(f"Incorrect path to file: {file_path}")

        if zipfile.is_zipfile(file_path):
            raise NotImplementedError("ZIP extractor not yet implemented")
        elif tarfile.is_tarfile(file_path):
            extractor = self._decompress_tar
        else:
            raise RuntimeError(f'Unknown archive format: {file_path.name}')

        # Returning file path is used for protected set method of internal _archive_path attribute.
        return file_path, extractor

    def _decompress_tar(self,
                        output_file_patterns: List[str],
                        archive_path: Optional[Path] = None,
                        extraction_path: Optional[Path] = None) -> Tuple[Path, List[Path], List[Path]]:
        """
        Decompresses files of archive in members list.
        If another archive is found then operation is called on it.
        Paths are assumed to be checked before call.

        Args:
        """
        if archive_path is None:
            archive_path = self._path
        if extraction_path is None:
            extraction_path = Path(self.config["extraction_directory"])
        LOG.info(f"Decompression of archive: {archive_path.name}")

        archive_name = archive_path.stem.split(".")[0]
        directory_path = extraction_path.joinpath(archive_name)
        explored_dirs = [directory_path]
        explored_files = []

        with tarfile.open(archive_path) as t:
            item = t.next()
            while item is not None:
                if item.isfile():
                    LOG.info(f"    processing file: {item.name}")
                    item_path = directory_path.joinpath(item.name)
                    if any(item.name.endswith(format)
                            for format in ['tgz', 'tar']):
                        t.extract(item, path=directory_path)
                        _, new_explored_dirs, new_explored_files = self._decompress_tar(output_file_patterns,
                                                        archive_path=item_path,
                                                        extraction_path=directory_path)
                        # Reverse ordering of dirs to correctly remove them
                        explored_dirs.extend(new_explored_dirs)
                        explored_files.extend(new_explored_files)
                        item_path.unlink()

                    # TODO: think about precompiling patterns to optimize regex match time
                    elif any(_pattern_parts_match(list(reversed(pat.split("/"))),
                                                list(reversed(item.name.split("/"))))
                            for pat in output_file_patterns):
                        t.extract(item, path=directory_path)
                        explored_files.append(item_path)
                        explored_dirs.append(item_path.parent)
                item = t.next()

        # Returned paths are used for parsing and automatic clean-up.
        return directory_path, explored_dirs, explored_files

    def _dir_explore(self,
                        output_file_patterns: List[str],
                        directory_path: Optional[Path] = None) -> Tuple[Path, List[Path], List[Path]]:
        """
        Explores given directory while matching files and recursing over sub-directories
        Paths are assumed to be checked before call.

        Args:
        """
        if directory_path is None:
            directory_path = self._path
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
                _, new_explored_dirs, new_explored_files = self._dir_explore(output_file_patterns, item_path)
                # Reverse ordering of dirs to correctly remove them
                explored_dirs.extend(new_explored_dirs)
                explored_files.extend(new_explored_files)

        # Returned paths are used for parsing and automatic clean-up.
        return directory_path, explored_dirs, explored_files
