#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""

Metadata archive integrating class.
Author: Kelbling, M., Jose V.

"""

import json
import sys
import importlib

from pathlib import Path
from enum import Enum
from typing import Optional, Union

from . import exporter as ex
from .AParser import Parser
from .Decompressor import Decompressor


class Archivist():

    def __init__(self,
                 config: Union[dict, str],
                 archive: Path,
                 parser: Parser,
                 verbose: Optional[bool] = True,
                 rm_dc_dir: Optional[bool] = False):
        """init

        :param config: path to config file as str or config as dict
        :param archive: path to archive (str)
        :param verbose: print verbose information (bool)
        :returns: None

        """
        self.verbose = verbose

        if self.verbose:
            print('''\n----- Archivist -----''')

        # get config
        if isinstance(config, str):
            self._load_config(config)
        elif isinstance(config, dict):
            self.config = config

        # check config
        self._check_config()

        # set decompressor
        self.decompressor = Decompressor(archive, self.config)

        # set parser
        self.parser = parser

        # check and get paths and types
        # self.archive_path, self.archive_type = dc.check_archive(archive)
        self.dc_dir_path = self._check_dir(self.config["extraction_directory"],
                                           allow_existing=False)
        self.out_dir_path = self._check_dir(self.config["output_directory"],
                                            allow_existing=True)
        self.checked_format = ex.check_format(self.config["output_format"])

        self.mode = self.config["parsing_rules"]["mode"].lower()

        if self.mode == "standard":
            self.module_path = None
        else:
            assert self.mode == "overwrite"
            assert isinstance(self.config["parsing_rules"]["module"], str)
            self.module_path = Path(self.config["parsing_rules"]["module"])
            assert self.module_path.is_file(
            ) and self.module_path.suffix == ".py"
            # TODO: implement checksum for security check against malicious code

        self.rm_dc_dir = rm_dc_dir

    def _check_config(self):
        """
        check if configuration contains required information
        if not exit

        :returns: None

        """
        req_config_keys_and_types = {
            "extraction_directory": str,
            "output_directory": str,
            "output_format": str,
            "metdata": str,
            "parsing_rules": dict
        }
        if self.verbose:
            print('Config:')
        for kk, vv in req_config_keys_and_types.items():
            if kk not in self.config.keys():
                print(f'The config is expected to contain the key: {kk}')
                sys.exit()
            if not isinstance(self.config[kk], vv):
                print(
                    f'The value of {kk} is expected to be of type {vv.__name__}'
                )
                sys.exit()
            if self.verbose:
                print(f'    {kk}: {self.config[kk].__str__()}')

    def _load_config(self, config_path: str):
        """
        Checks path to configuration file and attempts to load it.

        Args:
            config_path: String path to configuration file.

        Returns:
            None
        """

        path = Path(config_path)

        assert path.is_file and path.suffix == ".json"

        with path.open() as f:
            self.config = json.load(f)

    def _check_dir(self, dir_path: str, allow_existing: bool = False) -> Path:
        """
        Checks directory path.
        If a directory with the same name already exists then continue.
        If a directory in the specified path cannot be created then execution is
        stopped.

        Args:
            dir_path: String path to output directory.
            allow_existing: Control boolean to allow the use of existing folders.

        Returns:
            Path object to output directory.
        """

        path = Path(dir_path)

        if dir_path != "":
            exists = path.exists()
            if not allow_existing:
                assert not exists, f"Directory already exists: {dir_path}"
            elif exists:
                assert path.is_dir(), f"Incorrect path to directory: {path}"
                return path

            try:
                path.mkdir()
            except FileNotFoundError as e:
                # This exception is raised if a nested path is given and intermediate directories do not exist
                print(f"Incorrect path to directory: {e.args}")
                sys.exit()

        return path

    def extract(self):
        if self.verbose:
            print(f'''
Extracting:
Output path: {self.out_dir_path}
Extraction path: {self.dc_dir_path}
Remove extracted: {self.rm_dc_dir}''')

        self.decompressor.output_files_pattern = self.parser.input_file_pattern

        self.decompressor.decompress()

        for file_path in self.decompressor.files:
            self.parser.parse(file_path)
