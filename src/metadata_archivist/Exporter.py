#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""

Metadata to file exporter.
Authors: Jose V., Matthias K.

"""

from json import dump
from pathlib import Path

from .Logger import LOG

class Exporter():
    """
    Convinience class for handling different export formats.
    Currently only available export format is JSON.
    """

    def __init__(self, format: str) -> None:
        if format.upper() == "JSON":
            self.export = self._export_json
        else:
            raise RuntimeError("Unknown export format type.")


    def _export_json(self, metadata: dict, outfile: Path) -> None:
        """
        Saves metadata to file as JSON.

        Args:
            metadata: Dictionary containing metadata.
            outfile: Path object to target file.
            form: String target form.
            verb: Boolean to control verbose output.
        """

        LOG.info(f"Saving metadata to file: {outfile}")

        with outfile.open("w") as f:
            dump(metadata, f, indent=4)

        LOG.info("Saved metadata file.")
