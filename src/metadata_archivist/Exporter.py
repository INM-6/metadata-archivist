#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""

Metadata to file exporter.
Currently only available export format is JSON.

exports:
    Exporter class

Authors: Jose V., Matthias K.

"""

from json import dump
from pathlib import Path

from .Logger import _LOG
from .helper_functions import _check_dir


class Exporter:
    """
    Convenience class for handling different export formats.

    Attributes:
        config: Dictionary containing configuration parameters.

    Methods:
        export: exporting procedure corresponding to output format in configuration.
    """

    def __init__(self, config) -> None:
        """
        Constructor of Exporter class.

        Arguments:
            config: dictionary containing configuration parameters.
        """

        self.config = config

    def export(self, metadata: dict) -> None:
        """
        Exports given metadata dictionary to file.
        Uses configuration parameters inside of internal dictionary.

        Arguments:
            metadata: dictionary to export.
        """


        export_format = self.config["output_format"].upper()
        if export_format not in _KNOWN_FORMATS:
            raise RuntimeError(f"Unknown export format type: {export_format}")
        export_directory = _check_dir(self.config["output_directory"], allow_existing=True)
        export_file = export_directory / self.config["output_file"]

        if export_file.exists():
            if export_file.is_file():
                if self.config["overwrite"]:
                    _LOG.warning(
                        f"Metadata output file exists: '{export_file}', overwriting."
                    )
                else:
                    raise RuntimeError(
                        f"Metadata output file exists: '{export_file}', overwriting not allowed."
                    )
            else:
                raise RuntimeError(
                    f"'{export_file}' exists and is not a file, cannot overwrite."
                )
            
        _KNOWN_FORMATS[export_format](metadata, export_file)


def _export_json(json_object: dict, outfile: Path) -> None:
    """
    Exports JSON object to file.
    
    Arguments:
        object: JSON object to export.
        outfile: Path object to target file.
    """

    _LOG.info(f"Saving metadata to file: {outfile}")

    with outfile.open("w") as f:
        dump(json_object, f, indent=4)

    _LOG.info("Saved metadata file.")


_KNOWN_FORMATS = {
    "JSON": _export_json
}
