#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""

Parser and Extractor instances examples.
Authors: Matthias K., Jose V.

"""

from metadata_archivist import AExtractor, Parser

NCDUMP_HS_SCHEMA = {}


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


def key_val_split(string, split_char):
    string = string.strip()
    out = string.split(split_char)
    return {out[0].strip(): out[1].strip()}


def key_val_split_rm_prefix(string, split_char, rm_prefix):
    string = string.strip()
    out = string.split(split_char)
    if isinstance(rm_prefix, str):
        out[0] = out[0].split(rm_prefix)[1]
    elif isinstance(rm_prefix, int):
        out[0] = out[0][rm_prefix:]
    return {out[0].strip(): out[1].strip()}


class ncdump_hs_extractor(AExtractor):

    def __init__(self):
        super().__init__(name='ncdump_hs_extractor',
                         input_file_pattern='ncdump_hs.out',
                         schema=NCDUMP_HS_SCHEMA)

    def extract(self, f):
        out = {}
        header = True
        blockname = None
        variable_name = None
        for line in f:
            if header:
                header = False
                out.update({'name': line[:-3]})
            elif line == '}\n':
                break
            elif line == 'dimensions:\n':
                blockname = 'dimensions'
                out.update({'dimensions': {}})
            elif line == 'variables:\n':
                blockname = 'variables'
                out.update({'variables': {}})
            elif line in [
                    '// global attributes::\n', '// global attributes:\n'
            ]:
                blockname = 'global_attributes'
                out.update({'global_attributes': {}})
            elif line == '\n':
                blockname = None
            elif blockname == 'dimensions':
                out['dimensions'].update(key_val_split(line[:-3], '='))
            elif blockname == 'variables':
                if '(' in line and '=' not in line:
                    tmp = line[:-3].strip().split(' ')
                    variable_type = tmp[0]
                    variable_name, first_dim = tmp[1].split('(')
                    if first_dim[-1] == ',':
                        dims = first_dim
                        for dim in tmp[2:]:
                            if dim[-1] == ')':
                                dims += dim[:-1]
                            else:
                                dims += dim
                        out['variables'][variable_name] = {
                            'name': variable_name,
                            'type': variable_type,
                            'dimensions': dims
                        }
                    elif first_dim[-1] == ')':
                        out['variables'][variable_name] = {
                            'name': variable_name,
                            'type': variable_type,
                            'dimensions': first_dim[:-1]
                        }
                    else:
                        raise RuntimeError('unknown format in ncdump output!')
                else:
                    out['variables'][variable_name].update(
                        key_val_split_rm_prefix(line[:-3], '=', ':'))
            elif blockname == 'global_attributes':
                out['global_attributes'].update(
                    key_val_split_rm_prefix(line[:-3], '=', 1))

        return out


my_parser = Parser(extractors=[ncdump_hs_extractor()])
