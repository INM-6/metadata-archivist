#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""

Archivist class for orchestrating Explorer, Formatter, and Exporter classes.

exports:
    Archivist class
    DEFAULT_CONFIG dictionary

Authors: Matthias K., Jose V.

"""

import logging

from shutil import rmtree
from copy import deepcopy
from typing import Union, Iterable, Optional

from metadata_archivist.parser import AParser
from metadata_archivist.exporter import Exporter
from metadata_archivist.explorer import Explorer
from metadata_archivist.formatter import Formatter


LOG = logging.getLogger(__name__)

# Default configuration parameters for the Archivist class:
# "extraction_directory": string path to extraction directory (not used if exploring a directory). Default "." .
# "output_directory": string path to output directory. Default "." .
# "output_file": string name of resulting metadata file. Default "metadata.json" .
# "lazy_load": control boolean to enable parser lazy loading. Needs compilation after parsing. Default False .
# "overwrite": control boolean to allow overwriting existing metadata file. Default True .
# "auto_cleanup": control boolean to clean up after generating metadata.
#                   Deletes extracted files and parsed files if lazy loading. Default True .
# "add_description": control boolean to add schema description attributes to resulting metadata. Default True .
# "add_type": control boolean to add schema type attributes to resulting metadata. Default False .
# "output_format": "string value of metadata file output format. Default "JSON" .
DEFAULT_CONFIG = {
    "extraction_directory": ".",
    "output_directory": ".",
    "output_file": "metadata.json",
    "lazy_load": False,
    "overwrite": True,
    "auto_cleanup": True,
    "add_description": False,
    "add_type": False,
    "output_format": "JSON",
}


class Archivist:
    """
    Convenience class for orchestrating the Explorer, Exporter, and Formatter.

    Attributes:
        config: Dictionary containing configuration parameters.

    Methods:
        parse: procedure that orchestrates exploration and parsing.
        get_metadata: procedure that orchestrates structuring and metadata compiling.
        export: procedure that triggers export method.
    """

    def __init__(
        self,
        path: str,
        parsers: Union[AParser, Iterable[AParser]],
        schema: Optional[Union[dict, str]] = None,
        **kwargs,
    ) -> None:
        """
        Constructor of Archivist class.

        Arguments:
            path: string of path pointing to exploration target.
            parsers: Parser or iterable sequence of parsers to be used.
            schema: Optional. Dictionary containing structuring schema.
                    If string is provided, assumes string path to file containing dictionary.

        Keyword arguments:
            key (as string), value pairs used for configuration, see _init_config method.
        """

        # Initialize configuration
        self.config = {}
        self._init_config(**kwargs)

        # Operational memory
        self._cache = {}

        # Set explorer
        self._explorer = Explorer(path, self.config)
        self._cache["extraction"] = self._explorer.path_is_archive

        # Set formatter
        self._formatter = Formatter(parsers, schema, self.config)

        # Set exporter
        self._exporter = Exporter(self.config)

    def _init_config(self, **kwargs) -> None:
        """
        Method used to initialise configuration dictionary from keyword arguments passed to class constructor.
        If no appropriate arguments found then initializes with default values.

        Keyword arguments: new values for _DEFAULT_CONFIG dict copy.
        """

        self.config = deepcopy(DEFAULT_CONFIG)
        key_list = list(self.config.keys())

        # Init rest of config params
        for key, value in kwargs.items():
            if key in self.config:
                if isinstance(value, type(self.config[key])):
                    self.config[key] = value
                    key_list.remove(key)
                else:
                    LOG.warning("Incorrect type for argument '%s' ignoring value", key)
            else:
                LOG.warning("Unused argument '%s'", key)

        for key in key_list:
            LOG.debug(
                "No argument found for '%s' initializing by default '%s'",
                key,
                str(self.config[key]),
            )

    def parse(self) -> None:
        """
        Coordinates exploration and metadata parsing with internal Explorer and Formatter.
        Generates internal cache of returned objects.
        """

        explored_path, explored_dirs, explored_files = self._explorer.explore(self._formatter.input_file_patterns)

        meta_files = self._formatter.parse_files(explored_path, explored_files)

        self._cache["explored_path"] = explored_path
        self._cache["explored_files"] = explored_files
        self._cache["explored_dirs"] = explored_dirs
        self._cache["meta_files"] = meta_files
        self._cache["compile_metadata"] = True

    def get_metadata(self) -> dict:
        """
        Fetches generated metadata.
        If needed, uses Formatter once to compile metadata.

        Returns:
            dictionary of parsed metadata.
        """

        if self._cache["compile_metadata"]:
            self._cache["compile_metadata"] = False
            self._cache["metadata"] = self._formatter.compile_metadata()
            self._clean_up()

        return self._cache["metadata"]

    def get_formatted_schema(self) -> dict:
        """Returns schema from Formatter."""
        return self._formatter.export_schema()

    def export(self) -> None:
        """Exports generated metadata to file using internal Exporter."""
        self._exporter.export(self.get_metadata())

    def _clean_up(self) -> None:
        """
        Cleanup method automatically called in get_metadata,
        deletes extraction directory (if extraction happened) and meta files (if lazy loading).
        """

        if self.config["auto_cleanup"]:
            if self._cache["extraction"]:
                root_extraction_path = self._cache["explored_dirs"][0]
                LOG.info("Cleaning extraction directory '%s'", str(root_extraction_path))
                try:
                    rmtree(root_extraction_path)
                except OSError as e:
                    LOG.warning(
                        "error cleaning '%s' - '%s'",
                        str(root_extraction_path),
                        e.message if hasattr(e, "message") else str(e),
                    )

            elif len(self._cache["meta_files"]) > 0:
                for fp in self._cache["meta_files"]:
                    LOG.info("Cleaning meta file '%s'", str(fp))
                    try:
                        fp.unlink()
                    except FileNotFoundError as e:
                        LOG.warning(
                            "error cleaning '%s' - '%s'",
                            str(fp),
                            e.message if hasattr(e, "message") else str(e),
                        )
            else:
                LOG.info("Nothing to clean.")
                return

            LOG.info("Done!")
