#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""

Metadata file saver example.
Tested with Python 3.8.10
Author: Jose V., Matthias K.

"""
import json
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
            json.dump(metadata, f, indent=4)

        if verb:
            print("Saved metadata file.")
