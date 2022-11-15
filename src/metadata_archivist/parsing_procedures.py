#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""

Metadata collection rules example.
Tested with Python 3.8.10
Author: Jose V.

"""

from pathlib import Path
from functools import partial
from re import sub
import f90nml


def index_line_parser(fp: Path) -> dict:
    """
    Parses file information by line index and value.

    Args:
        fp: Path object to metadata file.

    Returns:
        Dictionary with file data.
    """

    data = {}

    with fp.open("r") as f:
        for index, line in enumerate(f):
            data[index] = line

    return data


def head_rest_split_line(line: str,
                         head_index: int = 0,
                         split_val: str = ":",
                         clean=None) -> dict:
    """
    Head rest split method for lines:
    the first value in split array as head and the rest of the values are
    concatenated.

    Args:
        line: String line to be splitted.
        head_index: Int index in split for head.
        split_val: String value used to split the line.
        clean: Optional callable clean the lines by.

    Returns:
        Dictionary with line split.
    """

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


def head_rest_split_parser(fp: Path, split_val: str = ":", clean=None) -> dict:
    """
    Parses file information splitting line by value and using
    the head rest split method.

    Args:
        fp: Path object to metadata file.
        split_val: String value used to split the line.
        clean: Optional callable clean the lines by.

    Returns:
        Dictionary with file data.
    """

    data = {}

    with fp.open("r") as f:
        for line in f:
            if line != "\n":
                data.update(
                    head_rest_split_line(line,
                                         split_val=split_val,
                                         clean=clean))

    return data


def content_to_string_parser(fp: Path, clean=None) -> dict:
    """
    Parses file information by transforming the content to a single string.

    WARNING do not use with very large files (>100MB),
    reading the whole file at once might cause memory errors.

    Args:
        fp: Path object to metadata file.
        clean: Optional callable clean the lines by.

    Returns:
        Dictionary with one key value pair containing file data.
    """

    data = str()

    with fp.open("r") as f:
        for line in f:
            if clean is not None:
                line = clean(line)
            data += line

    return {"content": data}


def file_ref_parser(fp: Path) -> dict:
    """
    Creates reference of file in path.

    TODO: create proper mongoDB acceptable reference.

    Args:
        fp: Path object to metadata file.

    Returns:
        Dictionary with one key value pair containing file name.
    """

    return {"ref": str(fp)}


def custom_rule_ipl(fp: Path) -> dict:
    """
    Custom rule for ip-l.out file.

    Args:
        fp: Path object to metadata file.

    Returns:
        Dictionary with file data.
    """

    string = content_to_string_parser(fp)["content"]
    string = sub(r"\s{2,}", " ", string)
    strings = string.split("\n")

    data = {}
    for s in strings:
        if s != "":
            data.update(head_rest_split_line(s, head_index=1))

    return data


def fortran_namelist_parser(fp: Path) -> dict:
    """
    parse information from fortran namelist.

    Args:
        fp: Path object to metadata file.

    Returns:
        Dictionary with file data.
    """
    a_nml = f90nml.read(fp)
    data = {}

    for nml_name, nml in a_nml.items():
        data[nml_name] = nml.todict()

    return data


PROCEDURES = {
    'ldd-nest.err':
    partial(head_rest_split_parser),
    'hwloc-info.out':
    partial(head_rest_split_parser),
    'dmidecode.out':
    content_to_string_parser,
    'ldd-nest.out':
    file_ref_parser,
    'stderr':
    file_ref_parser,
    'false.out':
    file_ref_parser,
    'getconf.out':
    partial(head_rest_split_parser,
            split_val=" ",
            clean=lambda x: sub(r"  +", " ", x)),
    'ip-l.out':
    custom_rule_ipl,
    'lspci.out':
    file_ref_parser,
    'hwloc-ls.out':
    file_ref_parser,
    'hostname.out':
    content_to_string_parser,
    'ulimit.out':
    partial(head_rest_split_parser,
            split_val="\t",
            clean=lambda x: sub(r"  +", r"\t", x)),
    'ip-r.out':
    file_ref_parser,
    'nproc.out':
    content_to_string_parser,
    'date.out':
    content_to_string_parser,
    'dmidecode.err':
    partial(head_rest_split_parser),
    'meminfo.out':
    partial(head_rest_split_parser),
    'lshw.err':
    partial(head_rest_split_parser),
    'cpuinfo.out':
    partial(head_rest_split_parser),
    'lshw.out':
    file_ref_parser,
    'env-vars.out':
    partial(head_rest_split_parser, split_val="="),
    'mhm.nml':
    fortran_namelist_parser,
    'mhm_parameter.nml':
    fortran_namelist_parser,
    'mhm_outputs.nml':
    fortran_namelist_parser,
    'mrm_outputs.nml':
    fortran_namelist_parser,
}
