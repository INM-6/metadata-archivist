#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""

Additional helper functions.

Authors: Jose V., Matthias K.

"""
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
