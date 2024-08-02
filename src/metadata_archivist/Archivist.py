#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Metadata archive integrating class.

exports:
    Archivist class

Authors: Matthias K., Jose V.
"""

from pathlib import Path
from typing import Union
from shutil import rmtree

from .Formatter import Formatter
from .Exporter import Exporter
from .Explorer import Explorer
from .Logger import LOG, set_level, is_debug


class Archivist():
    """
    Convenience class for orchestrating the Explorer, Exporter, Formatter.
    Automatically instantiates Explorer and Exporter,
    these can be configured through keyword arguments passed through
    the class constructor.

    Methods:
        parse
        get_metadata
        export
    """

    def __init__(self, path: Union[str, Path], formatter: Formatter, **kwargs) -> None:
        """
        Constructor of Archivist class.

        Arguments:
            path: string or Path object pointing to exploration target
            formatter: Formatter object containing parsers and schema (optional)
        
        Keyword arguments:
            key (as string), value pairs used for configuration, see _init_config method.
        """

        # Initialize configuration
        self.config = {}
        self._init_config(**kwargs)

        # Check and get paths for internal handling
        self._dc_dir_path = self._check_dir(
            self.config["extraction_directory"], allow_existing=False)
        self._out_dir_path = self._check_dir(self.config["output_directory"],
                                             allow_existing=True)

        self.metadata_output_file = self._out_dir_path / Path(
            self.config["output_file"])
        if self.metadata_output_file.exists():
            if self.metadata_output_file.is_file():
                if self.config["overwrite"]:
                    LOG.warning(
                        f"Metadata output file exists: '{self.metadata_output_file}', overwriting."
                    )
                else:
                    raise RuntimeError(
                        f"Metadata output file exists: '{self.metadata_output_file}', overwriting not allowed"
                    )
            else:
                raise RuntimeError(
                    f"'{self.metadata_output_file}' exists and is not a file, cannot overwrite"
                )

        # Operational memory
        self._cache = {}

        # Set explorer
        self.explorer = Explorer(path, self.config)
        self._cache["decompression"] = self.explorer.path_is_archive

        # Set formatter
        self.formatter = formatter

        # Set exporter
        # TODO: use output format for better handling?
        f_format = self.config["output_file"][self.config["output_file"].find(".") + 1:]
        self.exporter = Exporter(f_format)


    def _init_config(self, **kwargs) -> None:
        """
        Method used to initialise configuration dictionary from keyword arguments passed to class constructor.
        If no appropriate arguments found then initializes with default values.
        """
        self.config = {
            "extraction_directory": ".",
            "output_directory": ".",
            "output_file": "metadata.json",
            "overwrite": True,
            "auto_cleanup": True,
            "verbose": 'info',  # TODO: change to None after development phase is done.
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

        set_level(self.config["verbose"])

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

        if is_debug():
            for key in key_list:
                LOG.debug(
                    f"No argument found for: '{key}' initializing by default: '{self.config[key]}'"
                )

    def _check_dir(self, dir_path: str, allow_existing: bool = False) -> Path:
        """
        Checks directory path.
        If a directory with the same name already exists then continue.

        Arguments:
            dir_path: String path to output directory.

        Keyword arguments:
            allow_existing: Control boolean to allow the use of existing folders. Default: False.

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

    def parse(self) -> dict:
        """
        Coordinates decompression and metadata parsing with internal
        Formatter and Explorer objects.
        Generates internal cache of returned objects by Parser and Explorer methods.

        Returns:
            parsed metadata as dictionary or None if lazy loading is enabled.
        """

        LOG.info(f'''Extracting:
        Output path: {self._out_dir_path}
        Extraction path: {self._dc_dir_path}
        Remove extracted: {self.config["auto_cleanup"]}''')

        LOG.info("Unpacking archive...")
        LOG.debug(f'    using patterns: {self.formatter.input_file_patterns}')

        decompress_path, decompressed_dirs, decompressed_files = self.explorer.explore(
            self.formatter.input_file_patterns)

        LOG.info(f'''Done!\nparsing files ...''')

        meta_files = self.formatter.parse_files(decompress_path,
                                             decompressed_files)

        LOG.info(f'''Done!''')

        self._cache["decompress_path"] = decompress_path
        self._cache["decompressed_files"] = decompressed_files
        self._cache["decompressed_dirs"] = decompressed_dirs
        self._cache["meta_files"] = meta_files
        self._cache["compile_metadata"] = True

        if len(self._cache["meta_files"]) == 0:
            metadata = self.get_metadata(**self.config)
        else:
            metadata = None

        return metadata

    def get_metadata(self, **kwargs) -> dict:
        """
        Fetches generated metadata as dictionary.
        If needed, uses parser to first compile metadata.

        Returns:
            parsed metadata as dictionary.
        """
        if self._cache["compile_metadata"]:
            LOG.info(f'''Compiling metadata...''')
            self._cache["compile_metadata"] = False
            self._cache["metadata"] = self.formatter.compile_metadata(**kwargs)
            LOG.info("Done!")
            self._clean_up()

        return self._cache["metadata"]

    def export(self) -> Path:
        """
        Exports generated metadata to file using internal Exporter object.

        Returns:
            Path object pointing to exported file.
        """
        LOG.info(f'''Exporting metadata...''')
        self.exporter.export(self.get_metadata(),
                             self.metadata_output_file)
        LOG.info("Done!")

        return self.metadata_output_file

    def _clean_up(self) -> None:
        """Cleanup method automatically called after metadata parsing (or compilation if lazy_loading)"""
        if self.config["auto_cleanup"]:
            if self._cache["decompression"]:
                dirs = self._cache["decompressed_dirs"]
                if str(self._dc_dir_path) != '.':
                    dirs.insert(0, self._dc_dir_path)
                LOG.info(f"Cleaning extraction directory: {str(dirs[0])}")
                try:
                    rmtree(dirs[0])
                except Exception as e:
                        LOG.warning(
                            f"error cleaning {str(dirs[0])}: {e.message if hasattr(e, 'message') else str(e)}")

            elif len(self._cache["meta_files"]) > 0:
                for fp in self._cache["meta_files"]:
                    LOG.info(f"Cleaning meta file: {str(fp)}")
                    try:
                        fp.unlink()
                    except Exception as e:
                        LOG.warning(f"error cleaning {str(fp)}: {e.message if hasattr(e, 'message') else str(e)}")
            else:
                return

            LOG.info("Done!")
