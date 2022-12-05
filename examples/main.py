#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""

Metadata extraction, collection and save pipeline example.
Tested with Python 3.8.10
Author: Jose V.

"""

from metadata_archivist import Archivist
from my_parsers import custom_parser

my_parser = custom_parser()

arch = Archivist(config='config.json',
                 archive='test_namelist.tgz',
                 parser=my_parser)

arch.extract()
