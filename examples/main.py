#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""

Metadata extraction, collection and save pipeline example.
Tested with Python 3.8.10
Author: Jose V.

"""

from metadata_archivist import Archivist, AExtractor, Parser
import re
import f90nml


class my_extractor1(AExtractor):

    def __init__(self):
        self._input_file_pattern = re.compile('mhm.nml')
        self._extracted_metadata = None
        self._schema = None

    def extract(self, data):
        parser = f90nml.Parser()
        a_nml = parser.reads(data.read())
        nml_dict = {}

        for nml_name, nml in a_nml.items():
            nml_dict[nml_name] = nml.todict()

        return nml_dict


my_parser = Parser(schema={}, extractors=[my_extractor1()])

arch = Archivist(config='config.json',
                 archive='test_namelist.tgz',
                 parser=my_parser)

arch.extract()
