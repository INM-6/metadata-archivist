#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""

Metadata archive integrating class.
Author: Kelbling, M., Jose V.

"""

import json
import warnings

from pathlib import Path
from typing import Optional, Union

from .Exporter import Exporter
from .Parser import Parser
from .Decompressor import Decompressor


class Archivist():

    def __init__(self,
                 config: Union[dict, str],
                 archive_path: Path,
                 parser: Parser,
                 verbose: Optional[bool] = True,
                 auto_cleanup: Optional[bool] = True) -> None:
        """
        Initialization method of Archivist class.

        :param config: path to config file as str or config as dict
        :param archive: path to archive (str)
        :param verbose: print verbose information (bool)
        """
        self.verbose = verbose

        # get config
        if isinstance(config, str):
            self._load_config(config)
        elif isinstance(config, dict):
            self.config = config

        # check config
        self._check_config()

        # set decompressor
        self.decompressor = Decompressor(archive_path, self.config)

        # set parser
        self.parser = parser

        self.auto_cleanup = auto_cleanup

        # check and get paths for internal handling
        self._dc_dir_path = self._check_dir(self.config["extraction_directory"],
                                           allow_existing=False)
        self._out_dir_path = self._check_dir(self.config["output_directory"],
                                            allow_existing=True)
        if self._dc_dir_path == self._out_dir_path:
            warnings.warn("Decompression directory and output directory are the same, disabling automatic cleanup.", RuntimeWarning)
            self.auto_cleanup = False

        # set exporter
        self.exporter = Exporter(self.config["output_format"])
        self.metadata_output_file = self._out_dir_path / Path('metadata.json')

        # Operational memory
        self.cache = {}

    def _load_config(self, config_path: str) -> None:
        """
        Checks path to configuration file and attempts to load it.

        Args:
            config_path: String path to configuration file.

        Returns:
            None
        """

        path = Path(config_path)

        if not (path.is_file() and path.suffix == ".json"):
            raise RuntimeError(f"Could not load config file: {path}")

        with path.open() as f:
            self.config = json.load(f)

    def _check_config(self) -> None:
        """
        check if configuration contains required information
        if not exit

        :returns: None

        """
        req_config_keys_and_types = {
            "extraction_directory": str,
            "output_directory": str,
            "output_format": str,
            "metadata": str,
            "parsing_rules": dict
        }
        if self.verbose:
            print('Config:')
        for kk, vv in req_config_keys_and_types.items():
            if kk not in self.config.keys():
                raise RuntimeError(f'The config is expected to contain the key: {kk}')
            if not isinstance(self.config[kk], vv):
                raise RuntimeError(
                    f'The value of {kk} is expected to be of type {vv.__name__}'
                )
            if self.verbose:
                print(f'    {kk}: {self.config[kk].__str__()}')

    def _check_dir(self, dir_path: str, allow_existing: bool = False) -> Path:
        """
        Checks directory path.
        If a directory with the same name already exists then continue.

        Args:
            dir_path: String path to output directory.
            allow_existing: Control boolean to allow the use of existing folders.

        Returns:
            Path object to output directory.
        """

        path = Path(dir_path)

        if str(path) != '.':
            if path.exists():
                if not allow_existing:
                    raise RuntimeError(f"Directory already exists: {path}")
                if not path.is_dir():
                    raise NotADirectoryError(f"Incorrect path to directory: {path}")
            else:
                path.mkdir(parents=True)

        return path

    def extract(self) -> dict:
        """
        Coordinates decompression and metadata extraction with internal
        Parser and Decompressor objects.
        Generates cache of returned objects by Parser and Decompressor methods.
        Returns extracted metadata.
        """
        if self.verbose:
            print(f'''
Extracting:
Output path: {self._out_dir_path}
Extraction path: {self._dc_dir_path}
Remove extracted: {self.auto_cleanup}
unpacking archive ...''')
                  
        decompress_path, decompressed_files, decompressed_dirs = self.decompressor.decompress(self.parser.input_file_patterns)

        if self.verbose:
            print(f'''Done!
parsing files ...''')

        metadata, meta_files = self.parser.parse_files(decompress_path, decompressed_files)

        if self.verbose:
            print(f'''Done!
''')
                  
        self.cache["decompress_path"] = decompress_path
        self.cache["decompressed_files"] = decompressed_files
        self.cache["decompressed_dirs"] = decompressed_dirs
        self.cache["metadata"] = metadata
        self.cache["meta_files"] = meta_files
                  
        if len(self.cache["meta_files"]) == 0:
            self._clean_up()
        else:
            warnings.warn("Lazy loading enabled, cleanup will be executed after export call.", RuntimeWarning)
            self.cache["compile_metadata"] = True

        return metadata

    def export(self) -> Path:
        """
        Exports generated metadata to file using internal Exporter object.
        If needed, uses parser to first compile metadata.
        Returns path to exported file.
        """
        if self.verbose:
            print(f'''
Exporting metadata...''')
        if self.cache["compile_metadata"]:
            metadata = self.parser.compile_metadata()
            self.cache["metadata"] = metadata
            self._clean_up()
        self.exporter.export(self.cache["metadata"],
                             self.metadata_output_file,
                             verb=self.verbose)
        
        return self.metadata_output_file

    def _clean_up(self) -> None:
        """Cleanup method automatically called after metadata extraction (or compilation if lazy_loading)"""
        if self.auto_cleanup:
            if self.verbose:
                print("Cleaning extraction directory")

            errors = []
            files = self.cache["decompressed_files"] + self.cache["meta_files"]
            dirs = self.cache["decompressed_dirs"]
            if str(self._dc_dir_path) != '.':
                dirs.append(self._dc_dir_path)

            if self.verbose:
                print(f"    cleaning files:")
                for f in files:
                    print(f"        {str(f)}")

            for file in files:
                try:
                    file.unlink()
                except Exception as e:
                    errors.append((str(file), e.message))
            
            if self.verbose:
                print(f"    cleaning directories:")
                for d in dirs:
                    print(f"        {str(d)}")

            for dir in dirs:
                try:
                    dir.rmdir()
                except Exception as e:
                    errors.append((str(dir), e.message if hasattr(e, "message") else str(e)))

            if len(errors) > 0:
                for e in errors:
                    print(f"    error cleaning:\n        {e[0]} -- {e[1]}")
