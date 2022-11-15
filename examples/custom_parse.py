#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""

Custom parsing rules example.
Tested with Python 3.8.10
Author: Jose V.

"""

from pathlib import Path
from functools import partial


def head_rest_double_split_line(line: str,
                                first_split: str,
                                second_split: str,
                                head_index: int = 0,
                                clean=None) -> dict:
    """
    Head rest split method for lines:
    A first split is used to determine head of line and then the rest of the
    line is splitted a second time with a different value

    Args:
        line: String line to be splitted.
        head_index: Int index in split for head.
        first_split: String value used to split the line between head and rest.
        second_split: String value used to split the rest.
        clean: Optional callable clean the lines by.

    Returns:
        Dictionary with line split.
    """

    if clean is not None:
        line = clean(line)

    line_split = line.split(first_split)
    rest_start = head_index + 1
    rest = line_split[rest_start:]
    last_index = len(rest) - 1

    return {
        line_split[head_index].strip():
        str().join([
            i.strip() + (" " if c < last_index else "")
            for c, i in enumerate(rest)
        ]).split(second_split)
    }


def head_rest_double_split_parser(fp: Path,
                                  first_split: str,
                                  second_split: str,
                                  clean=None) -> dict:
    """
    Parses file information splitting line by value and using
    the head rest double split method.

    Args:
        fp: Path object to metadata file.
        first_split: String value used to split the line between head and rest.
        second_split: String value used to split the rest.
        clean: Optional callable clean the lines by.

    Returns:
        Dictionary with file data.
    """

    data = {}

    with fp.open("r") as f:
        for line in f:
            if line != "\n":
                data.update(
                    head_rest_double_split_line(line,
                                                first_split,
                                                second_split,
                                                clean=clean))

    return data


RULES = {
    'env-vars.out':
    partial(head_rest_double_split_parser, first_split="=", second_split=":"),
}
