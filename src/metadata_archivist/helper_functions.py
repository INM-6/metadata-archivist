#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""

Module containing collection of convenience functions internally used.

exports:
    check_dir: Checks string path to directory, if none exists in destination then creates new.
    update_dict_with_parts: Inserts value in depth of nested dictionary using a sequence of keys to follow.
    merge_dicts: Merges two different dictionary in depth.
    filter_dict: Filters nested dictionary using sequence of keys to retrieve deep values.
    deep_get_from_schema: Retrieves deep values from schema while skipping known container keys.
    pattern_parts_match: Matches sequence of patterns to sequence of strings.
    unpack_nested_value: Retrieves value from depth of nested single-width dictionary.
    math_check: Check mathematical expression with possible variable name replacement.
    filter_metadata: Filters metadata dictionary by matching patterns of sequences of keys.
    add_info_from_schema: Retrieves information from schema and annotates metadata with it.
    remove_directives_from_schema: Recursively removes custom interpreting directives from schema.

Authors: Jose V., Matthias K.

"""

from json import dumps
from re import fullmatch
from pathlib import Path
from copy import deepcopy
from collections.abc import Iterable
from typing import Optional, Any, Tuple

from metadata_archivist.logger import LOG, is_debug


# List of ignored JSON schema iterable keys
IGNORED_ITERABLE_KEYWORDS = [
    "additionalProperties",
    "allOf",
    "anyOf",
    "contains",
    "contentSchema",
    "dependentRequired",
    "dependentSchemas",
    "else",
    "enum",
    "examples",
    "if",
    "items",
    "not",
    "oneOf",
    "prefixItems",
    "propertyNames",
    "required",
    "then",
    "type",
    "unevaluatedItems",
    "unevaluatedProperties",
]


# List of known iterable keywords in schema
KNOWN_ITERABLE_KEYWORDS = sorted(
    IGNORED_ITERABLE_KEYWORDS + ["properties", "patternProperties"]
)


def check_dir(dir_path: str, allow_existing: bool = False) -> Tuple[Path, bool]:
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
                LOG.debug("directory path '%s'", str(path))
                raise RuntimeError("Directory already exists.")
            if not path.is_dir():
                LOG.debug("found path '%s'", str(path))
                raise NotADirectoryError("Incorrect path to directory.")
        else:
            path.mkdir(parents=True)
            return path, True

    return path, False


def update_dict_with_parts(target_dict: dict, value: Any, parts: list) -> None:
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
            if is_debug():
                LOG.debug(
                    "key %s\nrelative root = %s",
                    part,
                    dumps(relative_root, indent=4, default=vars),
                )
            raise RuntimeError(
                "Duplicate key with incorrect found while updating tree with path hierarchy."
            )
        relative_root = relative_root[part]
    relative_root[parts[-1]] = value


def merge_dicts(dict1: dict, dict2: dict) -> dict:
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
            if isinstance(val1, type(val2)):
                if isinstance(val1, Iterable):
                    if isinstance(val1, dict):
                        merged_dict[key] = merge_dicts(val1, val2)
                    elif isinstance(val1, list):
                        merged_dict[key] = val1 + val2
                    elif isinstance(val1, set):
                        merged_dict[key] = val1 | val2
                    elif isinstance(val1, tuple):
                        merged_dict[key] = tuple(list(val1) + list(val2))
                    elif isinstance(val1, frozenset):
                        merged_dict[key] = frozenset(list(val1) + list(val2))
                    else:
                        LOG.debug("Unknown iterable type '%s'", str(type(val1)))
                        raise RuntimeError("Unknown Iterable type.")
                else:
                    if val1 == val2:
                        merged_dict[key] = val1
                    else:
                        merged_dict[key] = [val1, val2]
            else:
                LOG.debug(
                    "val1 type '%s', val2 type '%s'", str(type(val1)), str(type(val2))
                )
                raise TypeError("Type mismatch while merge dictionaries.")
        else:
            merged_dict[key] = dict1[key]
    for key in keys2:
        merged_dict[key] = dict2[key]

    return merged_dict


def filter_dict(input_dict: dict, filter_keys: list, _level: int = 0) -> dict:
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
                    new_dict[k] = filter_dict(input_dict[k], filter_keys, _level + 1)
                else:
                    new_dict[k] = deepcopy(input_dict[k])
    return new_dict


def deep_get_from_schema(schema: dict, keys: list) -> Any:
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
                return deep_get_from_schema(schema[key], keys)
            return schema[key]

        for k in schema:
            if k in KNOWN_ITERABLE_KEYWORDS:
                try:
                    return deep_get_from_schema(schema[k], keys)
                except StopIteration:
                    pass

        if is_debug():
            LOG.debug("schema = %s", dumps(schema, indent=4, default=vars))
            LOG.debug("keys = %s", dumps(keys, indent=4, default=vars))
        raise StopIteration(
            "Iterated through schema without finding corresponding keys."
        )

    if is_debug():
        LOG.debug("schema = %s", dumps(schema, indent=4, default=vars))
        LOG.debug("keys = %s", dumps(keys, indent=4, default=vars))
    raise StopIteration("No key found for corresponding schema.")


def pattern_parts_match(
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
                if is_debug():
                    LOG.debug("context = %s", dumps(context, indent=4, default=vars))
                raise RuntimeError("Badly structured context for pattern matching.")

            # Match against same index element in file path
            if not fullmatch(
                part.format(**{context["!varname"]: context["regexp"]}), actual_parts[i]
            ):
                LOG.debug(
                    "pattern '%s' did not match against '%s'", part, actual_parts[i]
                )
                break

        # Else literal matching
        elif not fullmatch(part, actual_parts[i]):
            LOG.debug("pattern '%s' did not match against '%s'", part, actual_parts[i])
            break

    # Everything matched in the for loop i.e. no breakpoint reached
    else:
        is_match = True

    return is_match


def unpack_nested_value(iterable: Any, level: Optional[int] = None) -> Any:
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
            if is_debug():
                LOG.debug(
                    "level %i\niterable = %s",
                    level,
                    dumps(iterable, indent=4, default=vars),
                )
            raise RuntimeError("Cannot further unpack iterable.")
        return iterable

    if len(iterable) > 1 and (level is None or level > 0):
        if is_debug():
            LOG.debug(
                "level %i\niterable = %s",
                level,
                dumps(iterable, indent=4, default=vars),
            )
        raise IndexError("Multiple branching possible when unpacking nested value.")

    if level is not None:
        if level > 0:
            level -= 1
        else:
            return iterable

    if isinstance(iterable, dict):
        return unpack_nested_value(next(iter(iterable.values())), level)
    return unpack_nested_value(next(iter(iterable)), level)


def math_check(expression: str) -> Tuple[bool, set]:
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
            valid expression boolean.
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
            if state in (-1, 1):  # start => par_count += 1 || operand => par_count += 1
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
            if state in (-1, 1):  # start -> variable || operand -> variable
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
            if state in (
                -1,
                1,
                3,
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

    if state == 3:  # number => new_var = True & -> end
        if fullmatch(r"\d+.?\d*", trace):
            trace = ""
            state = 0
            new_vals = True
        else:
            return False, None

    if par_count != 0 or trace != "" or state != 0 or len(variables) == 0:
        return False, None
    return True, variables


def filter_metadata(metadata: dict, keys: list) -> dict:
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

    new_dict = {}
    for k in keys:
        LOG.debug("Filtering key '%s'", k)
        new_dict = merge_dicts(new_dict, filter_dict(metadata, k.split("/")))
    return new_dict


def add_info_from_schema(
    metadata: dict,
    schema: dict,
    add_description: bool,
    add_type: bool,
    key_list: list = None,
) -> None:
    """
    Adds additional information from input schema to parsed metadata inplace.

    Arguments:
        metadata: dictionary to add information to.
        add_description: control boolean to enable addition of description information.
        add_type: control boolean to enable addition of type information.
        key_list: recursion list containing visited dictionary keys.
    """

    if not (add_description or add_type):
        return

    if key_list is None:
        key_list = []
    keys = list(metadata.keys())
    for key in keys:
        value = metadata[key]
        if isinstance(value, dict):
            add_info_from_schema(
                value, schema, add_description, add_type, key_list + [key]
            )
        else:
            new_value = {"value": value}
            schema_entry = None
            try:
                schema_entry = deep_get_from_schema(schema, key_list + [key])
            except StopIteration:
                LOG.warning("No schema entry found for metadata value '%s'", key)
                if is_debug():
                    LOG.debug(
                        "key '%s' , value '%s'\nmetadata = %s\nschema = %s",
                        str(key),
                        str(value),
                        dumps(metadata, indent=4, default=vars),
                        dumps(schema, indent=4, default=vars),
                    )
            if schema_entry is not None:
                if add_description:
                    new_value["description"] = schema_entry["description"]
                if add_type:
                    new_value["type"] = schema_entry["type"]
                metadata[key] = new_value


def remove_directives_from_schema(schema: dict) -> dict:
    """
    Recursively removes custom interpreting directives from schema.
    Directives are keywords starting with '!'

    Arguments:
        schema: formatter schema potentially with directives to remove.

    Returns partial copy of schema dictionary without directives.
    """

    new_schema = {}
    for key, value in schema.items():
        if not key.startswith("!"):
            if not isinstance(value, dict):
                new_schema[key] = value
            else:
                new_schema[key] = remove_directives_from_schema(value)

    return new_schema
