#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""

Archive decompressor.
Authors: Jose V., Matthias K.

"""

import re
import zipfile
import tarfile

from pathlib import Path
from collections.abc import Callable
from typing import Optional, List, Tuple, NoReturn

from .Logger import LOG

class Decompressor():
    """
    Class containing all methods around processing compressed archives

    Main purposes in the framework:
    - receive list of re.patterns
    - send path to decompression directories and paths to decompressed files
    """

    def __init__(self,
                 archive_path: Path,
                 config: dict) -> None:
        
        # Protected
        self._archive_path, self._decompress = self._check_archive(archive_path)

        # Public
        self.config = config

    @property
    def archive_path(self) -> Path:
        """Returns path to archive (Path)."""
        return self._archive_path

    @archive_path.setter
    def archive_path(self, archive_path: Path) -> None:
        """Sets new archive path after checking."""
        self._archive_path, self._decompress = self._check_archive(archive_path)

    @property
    def decompress(self) -> Callable:
        """Returns appropriate decompress function wrt. archive format."""
        return self._decompress
    
    @decompress.setter
    def decompress(self, _) -> NoReturn:
        """
        Forbidden setter for decompress attribute.
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
            raise NotImplementedError("ZIP decompressor not yet implemented")
        elif tarfile.is_tarfile(file_path):
            decompressor = self._decompress_tar
        else:
            raise RuntimeError(f'Unknown archive format: {file_path.name}')

        # Returning file path is used for protected set method of internal _archive_path attribute.
        return file_path, decompressor

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
            archive_path = self._archive_path
        if extraction_path is None:
            extraction_path = Path(self.config["extraction_directory"])
        LOG.info(f"Decompression of archive: {archive_path.name}")

        archive_name = archive_path.stem.split(".")[0]
        decompress_path = extraction_path.joinpath(archive_name)
        decompressed_dirs = [decompress_path]
        decompressed_files = []

        with tarfile.open(archive_path) as t:
            item = t.next()
            while item is not None:
                LOG.info(f"    processing file: {item.name}")
                item_path = decompress_path.joinpath(item.name)
                if any(item.name.endswith(format)
                        for format in ['tgz', 'tar']):
                    t.extract(item, path=decompress_path)
                    _, new_decompressed_dirs, new_decompressed_files = self._decompress_tar(output_file_patterns,
                                                       archive_path=item_path,
                                                       extraction_path=decompress_path)
                    # Reverse ordering of dirs to correctly remove them
                    new_decompressed_dirs.extend(decompressed_dirs)
                    decompressed_dirs = new_decompressed_dirs
                    decompressed_files.extend(new_decompressed_files)
                    item_path.unlink()

                # TODO: think about precompiling patterns to optimize regex match time
                elif any(re.fullmatch(f'.*/{pat}', item.name)
                        for pat in output_file_patterns):
                    t.extract(item, path=decompress_path)
                    decompressed_files.append(item_path)
                elif item.isdir():
                    # TODO: Deal with empty dirs
                    decompressed_dirs.insert(0, item_path)
                item = t.next()

        # Returned paths are used for parsing and automatic clean-up.
        return decompress_path, decompressed_dirs, decompressed_files
