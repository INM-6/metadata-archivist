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
from typing import Optional, Any, Tuple

from .logger import _LOG, _is_debug


# List of known property names in schema
_KNOWN_PROPERTIES = [
    "properties",
    "unevaluatedProperties",
    "additionalProperties",
    "patternProperties",
]


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

    if str(path) != ".":
        if path.exists():
            if not allow_existing:
                _LOG.debug("directory path: %s", str(path))
                raise RuntimeError("Directory already exists.")
            if not path.is_dir():
                _LOG.debug("found path: %s", str(path))
                raise NotADirectoryError("Incorrect path to directory.")
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
    for part in parts[: len(parts) - 1]:
        if part not in relative_root:
            relative_root[part] = {}
        elif not isinstance(relative_root[part], dict):
            if _is_debug():
                _LOG.debug(
                    "key: %s\nrelative root: %s",
                    part,
                    dumps(relative_root, indent=4, default=vars),
                )
            raise RuntimeError(
                "Duplicate key with incorrect found while updating tree with path hierarchy."
            )
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
                        merged_dict[key] = frozenset(list(val1) + list(val2))
                    else:
                        _LOG.debug("Unknown iterable type: %s", str(type(val1)))
                        raise RuntimeError("Unknown Iterable type.")
                else:
                    if val1 == val2:
                        merged_dict[key] = val1
                    else:
                        merged_dict[key] = [val1, val2]
            else:
                _LOG.debug(
                    "val1 type: %s, val2 type: %s", str(type(val1)), str(type(val2))
                )
                raise TypeError("Type mismatch while merge dictionaries.")
        else:
            merged_dict[key] = dict1[key]
    for key in keys2:
        merged_dict[key] = dict2[key]

    return merged_dict


def _filter_dict(input_dict: dict, filter_keys: list, _level: int = 0) -> dict:
    """
    Recursively filters input dictionary by providing filtering keys.
    Keys can be exact or defined as regular expression.
    Filtering operation is done by copy of input.

    Arguments:
        input_dict: input dictionary to filter.
        filter_keys: list of keys as strings to filter by.
        _level: recursion level tracking integer.

    Returns
        filtered dictionary (copy).
    """
    new_dict = {}
    if _level >= len(filter_keys):
        new_dict = deepcopy(input_dict)
    else:
        for k in input_dict:
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

    key_count = len(keys)
    if key_count > 0:

        key = keys[0]
        if key in schema:
            if key_count - 1 > 0:
                keys.pop(0)
                return _deep_get_from_schema(schema[key], keys)
            return schema[key]

        for k in schema:
            if k in _KNOWN_PROPERTIES:
                try:
                    return _deep_get_from_schema(schema[k], keys)
                except StopIteration:
                    pass

        if _is_debug():
            _LOG.debug("schema: %s", dumps(schema, indent=4, default=vars))
            _LOG.debug("keys: %s", dumps(keys, indent=4, default=vars))
        raise StopIteration(
            "Iterated through schema without finding corresponding keys."
        )

    else:
        if _is_debug:
            _LOG.debug("schema: %s", dumps(schema, indent=4, default=vars))
            _LOG.debug("keys: %s", dumps(keys, indent=4, default=vars))
        raise StopIteration("No key found for corresponding schema.")


def _pattern_parts_match(
    pattern_parts: list, actual_parts: list, context: Optional[dict] = None
) -> bool:
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
        if fullmatch(r"\{\w+\}", part) and context is not None:
            # !varname and regexp should always be in context in this case
            if "!varname" not in context or "regexp" not in context:
                if _is_debug():
                    _LOG.debug("context: %s", dumps(context, indent=4, default=vars))
                raise RuntimeError("Badly structured context for pattern matching.")

            # Match against same index element in file path
            if not fullmatch(
                part.format(**{context["!varname"]: context["regexp"]}), actual_parts[i]
            ):
                _LOG.debug(
                    "pattern: '%s' did not match against '%s'", part, actual_parts[i]
                )
                break

        # Else literal matching
        elif not fullmatch(part, actual_parts[i]):
            _LOG.debug(
                "pattern: '%s' did not match against '%s'", part, actual_parts[i]
            )
            break

    # Everything matched in the for loop i.e. no breakpoint reached
    else:
        is_match = True

    return is_match


def _unpack_nested_value(iterable: Any, level: Optional[int] = None) -> Any:
    """
    Helper function to unpack any type of nested value
    i.e. unpacking a nested container where each nesting level contains a single value,
    until a primitive is found or desired level reached.

    Arguments:
        iterable: iterable type of container to unpack.
        level: Optional recursion level to stop unpacking.

    Returns:
        primitive value found at last depth (or given level).
    """

    if not isinstance(iterable, Iterable):
        if level is not None and level > 0:
            if _is_debug():
                _LOG.debug(
                    "iterable: %s\nlevel: %i",
                    dumps(iterable, indent=4, default=vars),
                    level,
                )
            raise RuntimeError("Cannot further unpack iterable.")
        return iterable

    if len(iterable) > 1 and (level is None or level > 0):
        if _is_debug():
            _LOG.debug(
                "iterable: %s\nlevel: %i",
                dumps(iterable, indent=4, default=vars),
                level,
            )
        raise IndexError("Multiple branching possible when unpacking nested value.")

    if level is not None:
        if level > 0:
            level -= 1
        else:
            return iterable

    if isinstance(iterable, dict):
        return _unpack_nested_value(next(iter(iterable.values())), level)
    else:
        return _unpack_nested_value(next(iter(iterable)), level)


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

    state = (
        -1
    )  # -1: start, 0: blank|stop, 1: read operand, 2: compiling variable, 3: compiling number
    par_count = 0
    variables = set()
    new_vals = True
    trace = ""
    for s in expression:
        if s == "(":
            if (
                state == -1 or state == 1
            ):  # start => par_count += 1 || operand => par_count += 1
                par_count += 1
            else:
                return False, None
        elif s == ")":
            if state == 3:  # number => new_var = True & par_count -= 1 & -> blank
                if fullmatch(r"\d+.?\d*", trace):
                    trace = ""
                    state = 0
                    par_count -= 1
                    new_vals = True
                else:
                    return False, None
            elif (
                state == 0 and new_vals
            ):  # blank -> IF new_var THEN new_var = False & par_count -= 1
                par_count -= 1
                new_vals = False
            else:
                return False, None
        elif s == "{":
            if state == -1 or state == 1:  # start -> variable || operand -> variable
                state = 2
            else:
                return False, None
        elif s == "}":
            if state == 2:  # variable => new_var = True & -> blank
                if fullmatch(r"\w+", trace):
                    variables.add(trace)
                    trace = ""
                    state = 0
                    new_vals = True
                else:
                    return False, None
            else:
                return False, None
        elif s == ".":
            if state == 3:  # number -> number
                trace += s
            else:
                return False, None
        elif fullmatch(r"[+\-*/%]", s):
            if state == 3:  # number => new_var = True & -> operand
                if fullmatch(r"\d+.?\d*", trace):
                    trace = ""
                    state = 1
                    new_vals = True
                else:
                    return False, None
            elif (
                state == 0 and new_vals
            ):  # blank -> IF new_var THEN new_var = False & -> operand
                state = 1
                new_vals = False
            else:
                return False, None
        elif fullmatch(r"\d", s):
            if (
                state == -1 or state == 1 or state == 3
            ):  # start -> number || operand -> number || number -> number
                trace += s
                state = 3
            elif state == 2:  # variable -> variable
                trace += s
            else:
                return False, None
        elif fullmatch(r"\w", s):
            if state == 2:  # variable -> variable
                trace += s
            else:
                return False, None
        else:
            return False, None
    else:
        if state == 3:  # number => new_var = True & -> end
            if fullmatch(r"\d+.?\d*", trace):
                trace = ""
                state = 0
                new_vals = True
            else:
                return False, None

    if par_count != 0 or trace != "" or state != 0 or len(variables) == 0:
        return False, None
    else:
        return True, variables


def _filter_metadata(metadata: dict, keys: list, **kwargs) -> dict:
    """
    Filters parsed metadata by providing keys corresponding to metadata attributes.
    If metadata is a nested dictionary then keys can be shaped as UNIX paths,
    where each path part corresponding to a nested attribute.

    Arguments:
        metadata: dictionary to filter.
        keys: list of keys to filter with.

    Returns:
        filtered dictionary.
    """

    add_description = False
    if "add_description" in kwargs:
        add_description = kwargs["add_description"]

    add_type = False
    if "add_type" in kwargs:
        add_type = kwargs["add_type"]

    new_dict = {}
    for k in keys:
        _LOG.debug("Filtering key: %s", k)
        new_dict = _merge_dicts(new_dict, _filter_dict(metadata, k.split("/")))
    if add_description or add_type:
        if "schema" not in kwargs:
            raise RuntimeError(
                "Attempting to add description or type without input schema."
            )
        if _is_debug():
            _LOG.debug(
                "adding information from schema %s",
                dumps(kwargs["schema"], indent=4, default=vars),
            )
        _add_info_from_schema(new_dict, kwargs["schema"], add_description, add_type)
    return new_dict


def _add_info_from_schema(
    metadata: dict,
    schema: dict,
    add_description: bool,
    add_type: bool,
    key_list: list = None,
) -> list:
    """
    WIP
    Adds additional information from input schema to parsed metadata inplace.

    Arguments:
        metadata: dictionary to add information to.
        add_description: control boolean to enable addition of description information.
        add_type: control boolean to enable addition of type information.
        key_list: recursion list containing visited dictionary keys.
    """

    if key_list is None:
        key_list = []
    keys = list(metadata.keys())
    for key in keys:
        value = metadata[key]
        if isinstance(value, dict):
            _add_info_from_schema(
                value, schema, add_description, add_type, key_list + [key]
            )
        else:
            new_value = {"value": value}
            schema_entry = None
            try:
                schema_entry = _deep_get_from_schema(schema, key_list + [key])
            except StopIteration:
                _LOG.warning("No schema entry found for metadata value: %s", key)
                if _is_debug():
                    _LOG.debug(
                        "key: %s\nvalue: %s\nmetadata: %s\nschema: %s",
                        str(key),
                        str(value),
                        dumps(metadata, indent=4, default=vars),
                        dumps(schema, indent=4, default=vars),
                    )
            if schema_entry is not None:
                new_value["description"] = schema_entry["description"]
                new_value["type"] = schema_entry["type"]
                metadata[key] = new_value
