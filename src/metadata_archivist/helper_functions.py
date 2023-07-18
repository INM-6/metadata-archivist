#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""

Additional helper functions.

Authors: Jose V., Matthias K.

"""

from collections.abc import Iterable
from typing import Optional
from functools import reduce


def defs2dict(defs, search_dict: Optional[dict] = None):
    sep = '/'
    if sep not in defs and search_dict is None:
        return defs
    elif sep not in defs and search_dict:
        return search_dict[defs]
    key, val = defs.split(sep, 1)
    if search_dict is None:
        return {key: defs2dict(val, None)}
    else:
        return {key: defs2dict(val, search_dict[key])}


def deep_get(dictionary, *keys):
    return reduce(lambda d, key: d.get(key) if d else None, keys, dictionary)


def _merge_dicts(dict1: dict, dict2: dict) -> dict:
    """
    Recursively merges dictionaries going in depth for nested structures.
    """
    keys1 = list(dict1.keys())
    keys2 = list(dict2.keys())
    merged_dict = {}
    for key in keys1:
        if key in keys2:
            keys2.remove(key)
            val1 = dict1[key]
            val2 = dict2[key]
            # TODO: behavior needs to be validated
            if type(val1) == type(val2):
                if isinstance(val1, Iterable):
                    if isinstance(val1, dict):
                        merged_dict[key] = _merge_dicts(val1, val2)
                    elif isinstance(val1, list):
                        merged_dict[key] = val1 + val2
                    elif isinstance(val1, set):
                        merged_dict[key] = val1 | val2
                    elif isinstance(val1, tuple):
                        merged_dict[key] = tuple(list(val1) + list(val2))
                    elif isinstance(val1, frozenset):
                        merged_dict[key] = frozenset(
                            list(val1) + list(val2))
                    else:
                        raise RuntimeError(
                            f"Unknown Iterable type: {type(val1)}")
                else:
                    if val1 == val2:
                        merged_dict[key] = val1
                    else:
                        merged_dict[key] = [val1, val2]
            else:
                raise TypeError
        else:
            merged_dict[key] = dict1[key]
    for key in keys2:
        merged_dict[key] = dict2[key]

    return merged_dict
