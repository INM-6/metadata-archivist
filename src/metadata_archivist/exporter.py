#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""

Exporter class to save formatted metadata to file.
Currently only available export format is JSON.

exports:
    Exporter class

Authors: Jose V., Matthias K.

"""

from typing import Callable

from metadata_archivist.logger import LOG
from metadata_archivist.helper_functions import check_dir
from metadata_archivist.export_rules import EXPORT_RULES


class Exporter:
    """
    Convenience class for handling different export formats.

    Class attributes:
        RULES: dictionary containing export rules. Used for registering new rules too.

    Instance attributes:
        config: Dictionary containing configuration parameters.

    Methods:
        export: exporting procedure corresponding to output format in configuration.
        register_rule: method to add new rule to RULES dictionary. All rules should have same signature.
    """

    RULES = EXPORT_RULES

    @classmethod
    def register_rule(cls, format_name: str, rule: Callable) -> None:
        """
        Class method to register new rules in RULES dictionary.

        Arguments:
            format_name: string name of format to export.
            rule: callable rule to export to new format.
        """

        if format_name in cls.RULES:
            LOG.warning("Replacing current export rule for %s", format_name)

        cls.RULES[format_name] = rule

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
        if export_format not in Exporter.RULES:
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

        Exporter.RULES[export_format](metadata, export_file)

        LOG.info("Done!")
