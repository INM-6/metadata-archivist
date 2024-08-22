#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""

The Metadata Archivist, a framework to perform parsing,
and structuring operations on a collection of heterogeneous input files.

Users need only to extend the abstract Parser class,
and define their own parsing functions.

With the help of the Archivist convenience class,
the framework can orchestrate directory or archive exploration,
filter out files to parse, structure using a schema template,
and export to an output file.

See DEFAULT_CONFIG for configuration options.

Authors: Matthias K., Jose V.

"""

__all__ = ["formatter", "parser", "explorer", "exporter", "archivist"]

from metadata_archivist.formatter import Formatter
from metadata_archivist.parser import AParser
from metadata_archivist.explorer import Explorer
from metadata_archivist.exporter import Exporter
from metadata_archivist.archivist import Archivist, DEFAULT_CONFIG
from metadata_archivist.interpretation_rules import register_interpretation_rule
from metadata_archivist.formatting_rules import register_formatting_rule
from metadata_archivist.export_rules import register_export_rule
