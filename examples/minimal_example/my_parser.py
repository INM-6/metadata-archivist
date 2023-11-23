#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""

Parser and Extractor instances examples.
Authors: Matthias K., Jose V.

"""

from metadata_archivist import AParser, Formatter
import yaml


def key_val_split(string, split_char):
    string = string.strip()
    out = string.split(split_char)
    return {out[0].strip(): out[1].strip()}


class time_extractor(AParser):

    def __init__(self) -> None:
        super().__init__(name='time_extractor', input_file_pattern='time\.txt', schema={})

    def parse(self, file_path) -> dict:
        out = {}
        with file_path.open("r") as fp:
            for line in fp:
                if line != '\n':
                    out.update(key_val_split(line, '\t'))
        return out


class yml_extractor(AParser):

    def __init__(self) -> None:
        super().__init__(name='yml_extractor', input_file_pattern='.*\.yml', schema={})

    def parse(self, file_path) -> dict:
        out = {}
        with file_path.open("r") as fp:
            out = yaml.safe_load(fp)
        return out


my_parser = Formatter(parsers=[time_extractor(), yml_extractor()], lazy_load=True)
