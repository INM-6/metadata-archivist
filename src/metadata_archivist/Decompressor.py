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

        # Internal handling
        self._files = []
        self._output_file_patterns = None

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
    def decompress(self) -> function:
        """Getter for _decompress"""
        return self._decompress
    
    @decompress.setter
    def decompress(self, _):
        raise AttributeError("decompress method can only be set through archive path checking")
    
    @property
    def output_file_patterns(self):
        if self._output_file_patterns is None:
            raise AttributeError('output_files_patterns have not been set yet!')
        return self._output_file_patterns

    @output_file_patterns.setter
    def output_file_patterns(self, file_patterns: List[str]):
        self._output_file_patterns = file_patterns

    @property
    def files(self) -> List[str]:
        """Getter for _files"""
        return self._files
    
    @files.setter
    def files(self, _):
        raise AttributeError("files list can only be generated through archive decompressing")

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

        with tarfile.open(archive_path) as t:
            item = t.next()
            while item is not None:
                if self.verbose:
                    print(f"    processing file: {item.name}")

                if any(item.name.endswith(format)
                        for format in ['tgz', 'tar']):
                    t.extract(item, path=decompress_path)
                    new_archive = decompress_path.joinpath(item.name.split(".")[0])
                    self._decompress_tar(new_archive, decompress_path)
                    new_archive.unlink()

                elif any(re.fullmatch(f'.*/{pat}', item.name)
                        for pat in self.output_file_patterns):
                    t.extract(item, path=decompress_path)
                    self._files.append(decompress_path.joinpath(item.name))
                    
                item = t.next()

        return decompress_path
