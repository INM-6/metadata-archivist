#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""

Metadata extraction, collection and save pipeline example.
Tested with Python 3.8.10
Author: Jose V.

"""

from metadata_archivist import Archivist
from my_parser import my_parser
from pathlib import Path

arch = Archivist(config='config.json',
                 archive=Path('metadata_archive.tar'),
                 parser=my_parser)

arch.extract()
arch.export()
