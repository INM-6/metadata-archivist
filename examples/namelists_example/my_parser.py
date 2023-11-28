#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""

Formatter and Parsers instances examples.
Authors: Matthias K., Jose V.

"""

from metadata_archivist import AParser, Formatter
import f90nml

NML_SCHEMA = {}


class nml_parser(AParser):

    def __init__(self):
        super().__init__(name='nml_parser', input_file_pattern='.*\.nml', schema=NML_SCHEMA)

    def parse(self, f):
        nml = f90nml.read(f)
        return nml.todict()


my_parser = Formatter(parsers=[nml_parser()])

# xx = nml_parser()

# with open('metadata_archive/mhm.nml') as ff:
#     yy = xx.parser(ff)
# print(yy)
