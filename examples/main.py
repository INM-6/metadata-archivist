#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""

Metadata extraction, collection and save pipeline example.
Tested with Python 3.8.10
Author: Jose V.

"""

from metadata_archivist import Archivist, AExtractor, Parser
from pathlib import Path
import f90nml
import json


class nml_extractor(AExtractor):

    def __init__(self):
        self.name = 'nml_extractor'
        self._input_file_pattern = '*.nml'
        self._extracted_metadata = {}

        with open('nml_schema.json') as f:
            nml_schema = json.load(f)

        self._schema = nml_schema

    def extract(self, data):
        parser = f90nml.Parser()
        a_nml = parser.reads(data.read())
        nml_dict = {}

        for nml_name, nml in a_nml.items():
            nml_dict[nml_name] = nml.todict()

        return nml_dict


def head_rest_split_line(line: str,
                         head_index: int = 0,
                         split_val: str = ":",
                         clean=None) -> dict:
    if clean is not None:
        line = clean(line)

    line_split = line.split(split_val)
    rest_start = head_index + 1
    rest = line_split[rest_start:]
    last_index = len(rest) - 1

    return {
        line_split[head_index].strip():
        str().join([
            i.strip() + (" " if c < last_index else "")
            for c, i in enumerate(rest)
        ])
    }


class meminfo_extractor(AExtractor):

    def __init__(self):
        self.name = 'meminfo_extractor'
        self._input_file_pattern = 'meminfo.out'
        self._extracted_metadata = {}

        with open('mem_schema.json') as f:
            mem_schema = json.load(f)

        self._schema = mem_schema

    def extract(self, f):
        out = {}
        for line in f:
            if line != "\n":
                out.update(
                    head_rest_split_line(line, split_val=":", clean=None))
        return out


my_parser = Parser(extractors=[nml_extractor(), meminfo_extractor()])

arch = Archivist(config='config.json',
                 archive=Path('test_namelist.tgz'),
                 parser=my_parser)

arch.extract()
arch.export()
