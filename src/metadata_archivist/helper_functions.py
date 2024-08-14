#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""

Module containing collection of convenience functions internally used.

Authors: Jose V., Matthias K.

"""

from json import dumps
from re import fullmatch
from pathlib import Path
from copy import deepcopy
from collections.abc import Iterable
from typing import Optional, Union, Any, Tuple

from .logger import _LOG


def _check_dir(dir_path: str, allow_existing: bool = False) -> Tuple[Path, bool]:
    """
    Checks directory path.
    If a directory with the same name already exists then continue.

    Arguments:
        dir_path: String path to output directory.

    Keyword arguments:
        allow_existing: Control boolean to allow the use of existing folders. Default: False.

    Returns:
        tuple of Path object to output directory and state boolean indicating directory creation.
    """

    path = Path(dir_path)

    if str(path) != '.':
        if path.exists():
            if not allow_existing:
                raise RuntimeError(f"Directory already exists: {path}")
            if not path.is_dir():
                raise NotADirectoryError(
                    f"Incorrect path to directory: {path}")
        else:
            path.mkdir(parents=True)
            return path, True

    return path, False


def _update_dict_with_parts(target_dict: dict, value: Any, parts: list) -> None:
    """
    In place, deep dictionary update.
    Generates and dynamically fills the target dictionary tree following a key sequence.

    Arguments:
        target_dict: dictionary where update takes place.
        value: object to insert.
        parts: list of keys used to sequentially nest the tree. Last part is always used as key of value.
    """
    
    # Get the parts of the relative path
    relative_root = target_dict
    for part in parts[:len(parts) - 1]:
        if part not in relative_root:
            relative_root[part] = {}
        elif not isinstance(relative_root[part], dict):
            _LOG.debug(f"key: {part}\nrelative root:\n{dumps(relative_root, indent=4, default=vars)}")
            raise RuntimeError("Duplicate key with incorrect found while updating tree with path hierarchy.")
        relative_root = relative_root[part]
    else:
        relative_root[parts[-1]] = value


def _merge_dicts(dict1: dict, dict2: dict) -> dict:
    """
    Recursively merges dictionaries going in depth for nested structures.

    Arguments:
        dict1: base dictionary.
        dict2: dictionary to merge with.

    Returns:
        dictionary combining both inputs.
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


def _filter_dict(input_dict: dict, filter_keys: list, _level: int = 0) -> dict:
    """
    Recursively filters input dictionary by providing filtering keys.
    Keys can be exact or defined as regular expression.

    Arguments:
        input_dict: input dictionary to filter.
        filter_keys: list of keys as strings to filter by.
        _level: recursion level tracking integer.

    Returns
        filtered dictionary.
    """
    new_dict = {}
    if _level >= len(filter_keys):
        new_dict = deepcopy(input_dict)
    else:
        for k in input_dict.keys():
            if fullmatch(filter_keys[_level], k):
                if isinstance(input_dict[k], dict):
                    new_dict[k] = _filter_dict(input_dict[k], filter_keys, _level + 1)
                else:
                    new_dict[k] = deepcopy(input_dict[k])
    return new_dict


def _deep_get_from_schema(schema: dict, keys: list) -> Any:
    """
    Fetches value located in depth of the schema.
    Uses a sequence of keys to navigate tree.

    Arguments:
        schema: schema dictionary (possibly with nested Properties).
        keys: list of keys to follow in schema. Last key is used to retrieve value directly.

    Returns:
        object found at last key position in schema.
    """

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


def _pattern_parts_match(pattern_parts: list, actual_parts: list, context: Optional[dict] = None) -> bool:
    """
    Path parts pattern matching.
    A tree branch parts or a regex path are needed to compare with an actual path.
    Both provided paths need to come as a list of parts in reverse order.
    A context can be provided to process !varname instructions.

    Arguments:
        pattern_pars: list of regex pattern parts.
        actual_parts: list of parts to compare with.
        context: Optional context dictionary.

    Returns:
        True if all parts of the pattern matched False otherwise.
    """

    is_match = False
    # We match through looping over the regex path in reverse order
    for i, part in enumerate(pattern_parts):
        # Match against varname
        if fullmatch(r'\{\w+\}', part) and context is not None:
            # !varname and regexp should always be in context in this case
            if "!varname" not in context or "regexp" not in context:
                _LOG.debug(dumps(context, indent=4, default=vars))
                raise RuntimeError("Badly structured context for pattern matching")

            # Match against same index element in file path
            if not fullmatch(part.format(**{context["!varname"]: context["regexp"]}), actual_parts[i]):
                _LOG.debug(f"{part} did not match against {actual_parts[i]}")
                break

        # Else literal matching
        elif not fullmatch(part, actual_parts[i]):
            _LOG.debug(f"{part} did not match against {actual_parts[i]}")
            break
    
    # Everything matched in the for loop i.e. no breakpoint reached
    else:
        is_match = True

    return is_match


def _unpack_singular_nested_value(iterable: Any, level: Optional[int] = None) -> Union[str, int, float, bool]:
    """
    Helper function to unpack any type of singular nested value
    i.e. unpacking a nested container where each nesting level contains a single value until a primitive is found.

    Arguments:
        iterable: iterable type of container to unpack.
        level: Optional recursion level to stop unpacking.

    Returns:
        primitive value found at last depth (or given level).
    """

    if isinstance(iterable, (str, int, float, bool)):
        if level is not None and level > 0:
            # TODO: Should we raise error?
            _LOG.warning(f"Finished unpacking before 0 level reached.")
        return iterable
    elif isinstance(iterable, Iterable):
        if len(iterable) > 1:
            raise IndexError(f"Multiple possible values found when unpacking singular nested value")
        if level is not None:
            if level > 0:
                level -= 1
            else:
                return iterable
        if isinstance(iterable, dict):
            return _unpack_singular_nested_value(next(iter(iterable.values())), level)
        else:
            return _unpack_singular_nested_value(next(iter(iterable)), level)


def _math_check(expression: str):
    """
    Stack machine for checking basic math expressions.
    transition rules:
        start -> variable
        start -> number
        start => par_count += 1
        blank -> end
        blank -> IF new_var THEN new_var = False & -> operand
        blank -> IF new_var THEN new_var = False & par_count -= 1
        variable -> variable
        variable => new_var = True & -> blank
        number -> number
        number => new_var = True & -> operand
        number => new_var = True & par_count -= 1 & -> blank
        number => new_var = True & -> end
        operand -> variable
        operand -> number
        operand => par_count += 1

    Arguments:
        expression: string expression to validate.
    
    Returns:
        tuple of:
            valid state boolean (True if par_count is 0 and state is blank and no malformed traces exists and number of variables found is above 0.).
            variables found in expression only if expression is correct otherwise None.
    """

    state = -1 # -1: start, 0: blank|stop, 1: read operand, 2: compiling variable, 3: compiling number
    par_count = 0
    variables = set()
    new_vals = True
    trace = ""
    for s in expression:
        if s == "(":
            if state == -1 or state == 1: # start => par_count += 1 || operand => par_count += 1
                par_count += 1
            else:
                return False, None
        elif s == ")":
            if state == 3: # number => new_var = True & par_count -= 1 & -> blank
                if fullmatch(r'\d+.?\d*', trace):
                    trace = ""
                    state = 0
                    par_count -= 1
                    new_vals = True
                else:
                    return False, None
            elif state == 0 and new_vals: # blank -> IF new_var THEN new_var = False & par_count -= 1
                    par_count -= 1
                    new_vals = False
            else:
                return False, None
        elif s == "{":
            if state == -1 or state == 1: # start -> variable || operand -> variable
                state = 2
            else:
                return False, None
        elif s == "}":
            if state == 2: # variable => new_var = True & -> blank
                if fullmatch(r'\w+', trace):
                    variables.add(trace)
                    trace = ""
                    state = 0
                    new_vals = True
                else:
                    return False, None
            else: 
                return False, None
        elif s == ".":
            if state == 3: # number -> number
                trace += s
            else:
                return False, None
        elif fullmatch(r"[+\-*/%]", s):
            if state == 3: # number => new_var = True & -> operand
                if fullmatch(r'\d+.?\d*', trace):
                    trace = ""
                    state = 1
                    new_vals = True
                else:
                    return False, None
            elif state == 0 and new_vals: # blank -> IF new_var THEN new_var = False & -> operand
                state = 1
                new_vals = False
            else:
                return False, None
        elif fullmatch(r"\d", s):
            if state == -1 or state == 1 or state == 3: # start -> number || operand -> number || number -> number
                trace += s
                state = 3
            elif state == 2: # variable -> variable
                trace += s
            else:
                return False, None
        elif fullmatch(r"\w", s):
            if state == 2: # variable -> variable
                trace += s
            else:
                return False, None
        else:
            return False, None
    else:
        if state == 3: # number => new_var = True & -> end
            if fullmatch(r'\d+.?\d*', trace):
                trace = ""
                state = 0
                new_vals = True
            else:
                return False, None

    if par_count != 0 or trace != "" or state != 0 or len(variables) == 0:
        return False, None
    else:
        return True, variables
