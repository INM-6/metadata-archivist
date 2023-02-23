#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Decompressor class
Originally:

Metadata archive extractor example.
Tested with Python 3.8.10
Author: Jose V., Kelbling, M.
"""

import re
import zipfile
import tarfile

from pathlib import Path
from collections.abc import Callable
from typing import Optional, List

class Decompressor():
    '''
    class containing all methods around processing compressed archives

    main purposes in the framework:
    - receive list of re.patterns
    - send a list of tuples (path/to/file/in/archive, IOBase object)
    '''

    def __init__(self,
                 archive_path: Path,
                 config: dict,
                 verbose: Optional[bool] = True):
        
        # Protected
        self._archive_path, self._decompress = self._check_archive(archive_path)

        self.config = config
        self.verbose = verbose

    @property
    def archive_path(self) -> Path:
        """Getter for _archive_path"""
        return self._archive_path

    @archive_path.setter
    def archive_path(self, archive_path: Path):
        """Set new archive path after checking"""
        self._archive_path, self._decompress = self._check_archive(archive_path)

    @property
    def decompress(self) -> Callable:
        """Getter for _decompress"""
        return self._decompress
    
    @decompress.setter
    def decompress(self, _):
        raise AttributeError("decompress method can only be set through archive path checking")

    def _check_archive(self, file_path: Path):
        """Internal method to check archive consistency"""

        if not file_path.is_file():
            raise FileNotFoundError(f"Incorrect path to file: {file_path}")

        if zipfile.is_zipfile(file_path):
            raise NotImplementedError("ZIP decompressor not yet implemented")
        elif tarfile.is_tarfile(file_path):
            decompressor = self._decompress_tar
        else:
            raise RuntimeError(f'Unknown archive format: {file_path.name}')

        return file_path, decompressor

    def _decompress_tar(self,
                        output_file_patterns: List[str],
                        archive_path: Optional[Path] = None,
                        extraction_path: Optional[Path] = None):
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
        if self.verbose:
            print(f"Decompression of archive: {archive_path.name}")

        archive_name = archive_path.stem.split(".")[0]
        decompress_path = extraction_path.joinpath(archive_name)
        decompressed_dirs = [decompress_path]
        decompressed_files = []

        with tarfile.open(archive_path) as t:
            item = t.next()
            while item is not None:
                if self.verbose:
                    print(f"    processing file: {item.name}")

                if any(item.name.endswith(format)
                        for format in ['tgz', 'tar']):
                    t.extract(item, path=decompress_path)
                    new_archive = decompress_path.joinpath(item.name)
                    _, ndd, ndf = self._decompress_tar(output_file_patterns,
                                                       archive_path=new_archive,
                                                       extraction_path=decompress_path)
                    ndd.extend(decompressed_dirs)
                    decompressed_dirs = ndd
                    decompressed_files.extend(ndf)
                    new_archive.unlink()

                elif any(re.fullmatch(f'.*/{pat}', item.name)
                        for pat in output_file_patterns):
                    t.extract(item, path=decompress_path)
                    decompressed_files.append(decompress_path.joinpath(item.name))
                elif item.isdir():
                    # TODO: Deal with empty dirs
                    decompressed_dirs.insert(0, decompress_path.joinpath(item.name))
                item = t.next()

        return decompress_path, decompressed_dirs, decompressed_files
