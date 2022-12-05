#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Decompressor class
Originally:

Metadata archive extractor example.
Tested with Python 3.8.10
Author: Jose V., Kelbling, M.
"""

import sys

from typing import Optional
from pathlib import Path
import zipfile
import tarfile
from re import Pattern


class Decompressor():
    '''
    class containing all methods around processing compressed archives

    main purposes in the framework:
    - receive list of re.patterns
    - send a list of tuples (path/to/file/in/archive, IOBase object)
    '''

    def __init__(self,
                 archive: str,
                 config: dict,
                 verbose: Optional[bool] = True):

        self.verbose = verbose
        if self.verbose:
            print('''\n    - Decompressor:''')

        self.current_file = (None, None)

        self._archive = None

        self.archive = Path(archive)

        self._output_files_pattern = None

        self.files = None

    @property
    def output_files_pattern(self):
        return self._output_files_pattern

    @output_files_pattern.setter
    def output_files_pattern(self, file_pattern: list[Pattern]):
        self._output_files_pattern = file_pattern

    @property
    def archive(self):
        return self._archive

    @archive.setter
    def archive(self, file_path: Path):

        assert file_path.is_file(), f"Incorrect path to archive {file_path}"

        if zipfile.is_zipfile(file_path):
            raise NotImplementedError("ZIP decompressor not yet implemented")
        elif tarfile.is_tarfile(file_path):
            self._archive = tarfile.open(file_path)
            self.decompress = self._decompress_tar
            self.next_file = self._next_tar_file
        else:
            print(f'Unknown archive format: {file_path.name}')
            sys.exit()

        print(f'''\n    archive: {file_path}''')
        self._archive_path = file_path

    def _next_tar_file(self,
                       archive_path: Path,
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
        archive_name = archive_path.stem.split(".")[0]
        new_path = dc_dir_path.joinpath(archive_name)

        item = self._archive.next()
        while item is not None and not any(
            [pat.match(item.name)
             for pat in self.output_files_pattern]) and not item.isfile():
            item = self._archive.next()
        return (self._archive.extractfile(item))

    def _decompress_tar(self,
                        archive_path: Optional[Path] = None,
                        dc_dir_path: Optional[Path] = None):
        """
        Decompresses files of archive in members list.
        If another archive is found then operation is called on it.
        Members are assumed to be files, if members are archives they will
        NOT be unpacked.
        Paths are assumed to be checked before call.

        Args:
        """
        if archive_path is None:
            archive_path = self._archive_path
        if dc_dir_path is None:
            dc_dir_path = self.config["extraction_directory"]

        archive_name = archive_path.stem.split(".")[0]
        new_path = dc_dir_path.joinpath(archive_name)

        with tarfile.open(archive_path) as t:
            item = t.next()
            while item is not None:
                if any(
                        pat.match(item.name)
                        for pat in self.output_files_pattern):
                    t.extract(item, path=new_path)
                elif any(
                        item.name.endswith(format)
                        for format in ['tgz', 'tar']):
                    t.extract(item, path=new_path)
                    new_archive = new_path.joinpath(item.name)
                    self._decompress_tar(new_archive, new_archive.parent)
                    new_archive.unlink()
                item = t.next()

    @property
    def files(self):
        files = set([
            sorted(self._archive_path.glob(pat.pattern))
            for pat in self.output_files_pattern
        ])
        return files
