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

from .formatter import Formatter
from .parser import AParser
from .explorer import Explorer
from .exporter import Exporter
from .archivist import Archivist, DEFAULT_CONFIG
