#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""

Additional helper functions.

Authors: Jose V., Matthias K.

"""

from json import dumps
from pathlib import Path
from re import fullmatch
from collections.abc import Iterable

from .Logger import LOG


#def defs2dict(defs, search_dict: Optional[dict] = None):
#    sep = '/'
#    if sep not in defs and search_dict is None:
#        return defs
#    elif sep not in defs and search_dict:
#        return search_dict[defs]
#    key, val = defs.split(sep, 1)
#    if search_dict is None:
#        return {key: defs2dict(val, None)}
#    else:
#        return {key: defs2dict(val, search_dict[key])}
#
#
#def deep_get(dictionary, *keys):
#    return reduce(lambda d, key: d.get(key) if d else None, keys, dictionary)

def _update_dict_with_path_hierarchy(target_dict: dict, value: dict, relative_path: Path) -> None:
    """
    In place dict update.
    Generates and dynamically fills the metadata tree with path hierarchy.
    The hierarchy is based on decompressed directory.
    """
    # Get the parts of the relative path
    parts = list(relative_path.parts)
    relative_root = target_dict
    for part in parts[:len(parts) - 1]:
        if part not in relative_root:
            relative_root[part] = {}
        elif not isinstance(relative_root[part], dict):
            LOG.debug(f"key: {part}\n\nrelative root: {dumps(relative_root, indent=4, default=vars)}")
            raise RuntimeError("Duplicate key with incorrect found while updating tree with path hierarchy.")
        relative_root = relative_root[part]
    else:
        relative_root[parts[-1]] = value

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

def _deep_get_from_schema(schema, keys: list):
    # if len(keys) > 0:
    k = keys.pop(0)
    if len(keys) > 0:
        if k in schema.keys():
            _deep_get_from_schema(schema[k], keys)
        elif 'properties' in schema.keys() and keys[0] in schema['properties']:
            _deep_get_from_schema(schema['properties'][k], keys)
        elif 'additionalProperties' in schema.keys(
        ) and keys[0] in schema['additionalProperties']:
            _deep_get_from_schema(schema['additionalProperties'], keys)
        elif 'additionalProperties' in schema.keys(
        ) and 'properties' in schema['additionalProperties'] and keys[
                0] in schema['additionalProperties']['properties']:
            _deep_get_from_schema(schema['additionalProperties']['properties'],
                                 keys)
        elif 'patternProperties' in schema.keys() and any(
                fullmatch(x, k)
                for x in schema['patternProperties'].keys()):
            for kk in schema['patternProperties'].keys():
                if fullmatch(kk, k):
                    _deep_get_from_schema(schema['patternProperties'][kk], keys)
                    break
    else:
        print(schema[k])
        return schema[k]
