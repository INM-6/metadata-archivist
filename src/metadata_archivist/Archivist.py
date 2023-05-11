#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""

Metadata archive integrating class.
Authors: Matthias K., Jose V.

"""

from pathlib import Path

from .Exporter import Exporter
from .Parser import Parser
from .Decompressor import Decompressor
from .Logger import LOG, set_verbose, set_debug


class Archivist():

    def __init__(self, archive_path: Path, parser: Parser, **kwargs) -> None:
        """
        Initialization method of Archivist class.

        :param config: path to config file as str or config as dict
        :param archive: path to archive (str)
        :param verbose: print verbose information (bool)
        """

        # Initialize configuration
        self.config = {}
        self._init_config(**kwargs)

        # Set decompressor
        self.decompressor = Decompressor(archive_path, self.config)

        # Set parser
        self.parser = parser

        # Check and get paths for internal handling
        self._dc_dir_path = self._check_dir(
            self.config["extraction_directory"], allow_existing=False)
        self._out_dir_path = self._check_dir(self.config["output_directory"],
                                             allow_existing=True)

        # Set exporter
        f_format = self.config["output_file"][self.config["output_file"].
                                              find(".") + 1:]
        self.exporter = Exporter(f_format)
        self.metadata_output_file = self._out_dir_path / Path(
            self.config["output_file"])
        if self.metadata_output_file.exists():
            if self.config["overwrite"]:
                if self.metadata_output_file.is_file():
                    LOG.warning(
                        f"Metadata output file exists: '{self.metadata_output_file}', overwriting."
                    )
                else:
                    raise RuntimeError(
                        f"Metadata output file exists: '{self.metadata_output_file}' cannot overwrite."
                    )
            else:
                raise RuntimeError(
                    f"Metadata output file exists: '{self.metadata_output_file}' overwrite not allowed."
                )

        # Operational memory
        self._cache = {}

    def _init_config(self, **kwargs) -> None:
        """
        Method used to initialise configuration dictionary from keyword arguments passed to class constructor.
        If no appropriate arguments found then initializes with default values.
        """
        self.config = {
            "extraction_directory": ".",
            "output_directory": ".",
            "output_file": "metadata.json",
            "overwrite":
            True,  # TODO: change to False after development phase is done. 
            "auto_cleanup": True,
            "verbose":
            'debug',  # TODO: change to None after development phase is done.
            'add_description': True,
            'add_type': False
        }
        key_list = list(self.config.keys())

        # Init logger object with verbose configuration
        if "verbose" in kwargs:
            if kwargs["verbose"] is not None and kwargs["verbose"] not in [
                    'debug', 'info'
            ]:
                raise RuntimeError(
                    f"Incorrect value for argument: verbose, expected None, debug or info"
                )
            self.config["verbose"] = kwargs["verbose"]
            key_list.remove("verbose")
            kwargs.pop("verbose", None)

        if self.config["verbose"] == 'info':
            set_verbose()
        elif self.config["verbose"] == 'debug':
            set_debug()

        # Init rest of config params
        for key in kwargs:
            if key in self.config:
                if type(kwargs[key]) == type(self.config[key]):
                    self.config[key] = kwargs[key]
                    key_list.remove(key)
                else:
                    raise RuntimeError(f"Incorrect value for argument: {key}")
            else:
                LOG.info(f"Unused argument: {key}")

        if self.config["verbose"] in ['debug', 'info']:
            for key in key_list:
                LOG.info(
                    f"No argument found for: '{key}' initializing by default: '{self.config[key]}'"
                )

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
                    raise NotADirectoryError(
                        f"Incorrect path to directory: {path}")
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
        LOG.info(f'''Extracting:
    Output path: {self._out_dir_path}
    Extraction path: {self._dc_dir_path}
    Remove extracted: {self.config["auto_cleanup"]}''')

        LOG.info("Unpacking archive...")
        LOG.debug(f'    using patterns: {self.parser.input_file_patterns}')

        decompress_path, decompressed_files, decompressed_dirs = self.decompressor.decompress(
            self.parser.input_file_patterns)

        LOG.info(f'''Done!\nparsing files ...''')

        meta_files = self.parser.parse_files(decompress_path,
                                             decompressed_files)

        LOG.info(f'''Done!''')

        self._cache["decompress_path"] = decompress_path
        self._cache["decompressed_files"] = decompressed_files
        self._cache["decompressed_dirs"] = decompressed_dirs
        self._cache["meta_files"] = meta_files
        self._cache["compile_metadata"] = True

        if len(self._cache["meta_files"]) == 0:
            metadata = self.get_metadata()
        else:
            raise NotImplementedError()
            # metadata = None

        return metadata

    def get_metadata(self, **kwargs) -> dict:
        """
        Returns generated metadata as a dictionary.
        If needed, uses parser to first compile metadata.
        """
        if self._cache["compile_metadata"]:
            LOG.info(f'''Compiling metadata...''')
            self._cache["compile_metadata"] = False
            metadata = self.parser.compile_metadata(**kwargs)
            self._cache["metadata"] = metadata
            LOG.info("Done!")
            self._clean_up()

        return self._cache["metadata"]

    def export(self) -> Path:
        """
        Exports generated metadata to file using internal Exporter object.
        Returns path to exported file.
        """
        metadata = self.get_metadata()
        LOG.info(f'''Exporting metadata...''')
        self.exporter.export(metadata,
                             self.metadata_output_file,
                             verb=(self.config["verbose"] in ['debug',
                                                              'info']))
        LOG.info("Done!")

        return self.metadata_output_file

    def _clean_up(self) -> None:
        """Cleanup method automatically called after metadata extraction (or compilation if lazy_loading)"""
        if self.config["auto_cleanup"]:
            LOG.info("Cleaning extraction directory...")
            errors = []
            files = self._cache["decompressed_files"] + self._cache[
                "meta_files"]
            dirs = self._cache["decompressed_dirs"]
            if str(self._dc_dir_path) != '.':
                dirs.append(self._dc_dir_path)

            LOG.info(f"    cleaning files:")
            for f in files:
                LOG.info(f"        {str(f)}")

            for file in files:
                try:
                    file.unlink()
                except Exception as e:
                    errors.append(
                        (str(file),
                         e.message if hasattr(e, "message") else str(e)))

            LOG.info(f"    cleaning directories:")
            for d in dirs:
                LOG.info(f"        {str(d)}")

            for dir in dirs:
                try:
                    dir.rmdir()
                except Exception as e:
                    errors.append(
                        (str(dir),
                         e.message if hasattr(e, "message") else str(e)))

            if len(errors) > 0:
                for e in errors:
                    LOG.warning(
                        f"    error cleaning:\n        {e[0]} -- {e[1]}")

            LOG.info("Done!")
