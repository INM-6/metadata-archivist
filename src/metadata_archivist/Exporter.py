#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""

Metadata to file exporter.
Authors: Jose V., Matthias K.

"""

from json import dump
from pathlib import Path


class Exporter():

    def __init__(self, format: str) -> None:
        if format.upper() == "JSON":
            self.export = self._export_json
        else:
            raise RuntimeError("Unknown export format type.")


    def _export_json(self, metadata: dict, outfile: Path, verb: bool = False) -> None:
        """
        Saves metadata to file as JSON.

        Args:
            metadata: Dictionary containing metadata.
            outfile: Path object to target file.
            form: String target form.
            verb: Boolean to control verbose output.
        """

        if verb:
            print(f"Saving metadata to file: {outfile}")

        with outfile.open("w") as f:
            dump(metadata, f, indent=4)

        if verb:
            print("Saved metadata file.")
