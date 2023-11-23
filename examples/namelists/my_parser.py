#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""

Parser and Extractor instances examples.
Authors: Matthias K., Jose V.

"""

from metadata_archivist import AParser, Formatter
import f90nml

NML_SCHEMA = {}


class nml_extractor(AParser):

    def __init__(self):
        super().__init__(name='nml_extractor', input_file_pattern='.*\.nml', schema=NML_SCHEMA)

    def parse(self, f):
        nml = f90nml.read(f)
        return nml.todict()


my_parser = Formatter(parsers=[nml_extractor()])

# xx = nml_extractor()

# with open('metadata_archive/mhm.nml') as ff:
#     yy = xx.extract(ff)
# print(yy)
