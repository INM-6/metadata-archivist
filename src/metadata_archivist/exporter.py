#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""

Exporter class to save formatted metadata to file.
Currently only available export format is JSON.

exports:
    Exporter class

Authors: Jose V., Matthias K.

"""

from json import dump
from pathlib import Path

from metadata_archivist.logger import LOG
from metadata_archivist.helper_functions import check_dir


class Exporter:
    """
    Convenience class for handling different export formats.

    Attributes:
        config: Dictionary containing configuration parameters.

    Methods:
        export: exporting procedure corresponding to output format in configuration.
    """

    def __init__(self, config: dict) -> None:
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

        LOG.info("Exporting metadata ...")

        export_format = self.config["output_format"].upper()
        if export_format not in _KNOWN_FORMATS:
            LOG.debug("Export format type: %s", export_format)
            raise RuntimeError("Unknown export format type.")
        export_directory = check_dir(
            self.config["output_directory"], allow_existing=True
        )[0]
        export_file = export_directory / self.config["output_file"]

        if export_file.exists():
            if export_file.is_file():
                if self.config["overwrite"]:
                    LOG.warning(
                        "Metadata output file exists: '%s', overwriting.",
                        str(export_file),
                    )
                else:
                    LOG.debug("Metadata export file path: %s", str(export_file))
                    raise RuntimeError(
                        "Metadata output file exists; overwriting not allowed."
                    )
            else:
                LOG.debug("Metadata export file path: %s not a file", str(export_file))
                raise RuntimeError(
                    "Conflicting path to metadata output file; cannot overwrite."
                )

        _KNOWN_FORMATS[export_format](metadata, export_file)

        LOG.info("Done!")


def _export_json(json_object: dict, outfile: Path) -> None:
    """
    Exports JSON object to file.

    Arguments:
        object: JSON object to export.
        outfile: Path object to target file.
    """

    LOG.debug("   exporting JSON to file: %s", str(outfile))

    with outfile.open("w") as f:
        dump(json_object, f, indent=4)


_KNOWN_FORMATS = {"JSON": _export_json}
