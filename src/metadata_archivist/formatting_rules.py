#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""

Module containing collection of rules as functions to format according to interpreted schema.

Formatting rules defined for the Formatter
Rules can be customized or added through
the FORMATTING_RULES dictionary.

All rule functions must have the same arguments.

Arguments:
    formatter: instance of Formatter calling the rule.
    interpreted_schema: interpreted (context-rich) SchemaEntry on which rule is called.
    branch: list of keys used to structure rule output, where each index is equivalent to a depth level.
    value: item value of current formatting entry.

Keyword arguments:
    additional context provided to rule by formatter.

Returns:
    formatted item value according to rule.

Only for internal use.

Authors: Jose V., Matthias K.

"""

from json import dumps
from typing import Union

from .Formatter import Formatter

from .logger import _LOG
from .helper_classes import _SchemaEntry
from .helper_functions import (
    _pattern_parts_match,
    _update_dict_with_parts,
    _unpack_singular_nested_value,
)


def _format_parser_id_rule(
    formatter: Formatter,
    interpreted_schema: _SchemaEntry,
    branch: list,
    value: str,
    **kwargs,
) -> dict:
    # Formats metadata with parsing result.
    # As parsing results can be filtered by file name or file path,
    # file matching and dictionary branching are matched against existing filters in context.
    # Further value filtering can be done through key selection in !parsing directive.

    if not isinstance(value, str):
        raise TypeError(f"Incorrect value type for formatting parser id: {type(value)}")

    # Currently only one parser reference per entry is allowed
    # and if a reference exists it must be the only content in the entry
    if len(interpreted_schema.items()) > 1:
        _LOG.debug(dumps(interpreted_schema._content, indent=4, default=vars))
        raise RuntimeError(
            f"Invalid entry content {interpreted_schema.key}: {interpreted_schema._content}"
        )

    # Get context
    context = interpreted_schema.context

    # Get parser and its cache
    parser = formatter.get_parser(value)
    parser_cache = formatter._cache[value]

    # Parser may have processed multiple files
    parsed_metadata = None

    # For all cache entries
    for cache_entry in parser_cache:

        # If in a regex context match file path to branch position
        if "useRegex" in context:

            # Parsed metadata should be structured in a dictionary
            # where keys are filenames and values are metadata
            if parsed_metadata is None:
                parsed_metadata = {}
            elif not isinstance(parsed_metadata, dict):
                _LOG.debug(f"parsed metadata: {parsed_metadata}\ncontext: {context}")
                raise RuntimeError(
                    f"Incorrect parsed_metadata initialization type: {parsed_metadata}"
                )

            # We skip the last element as it represents the node name of the parsed metadata
            # not to be included in the path of the tree
            file_path_parts = list(reversed(cache_entry.rel_path.parent.parts))
            reversed_branch = list(reversed(branch[: len(branch) - 1]))

            # If there is a mismatch we skip the cache entry
            if not _pattern_parts_match(reversed_branch, file_path_parts):
                continue

        # If path information is present in parser directives match file path to given regex path
        if "!parsing" in context and "path" in context["!parsing"]:

            # Parsed metadata should be structured in a dictionary
            # where keys are filenames and values are metadata
            if parsed_metadata is None:
                parsed_metadata = {}
            elif not isinstance(parsed_metadata, dict):
                _LOG.debug(f"parsed metadata: {parsed_metadata}\ncontext: {context}")
                raise RuntimeError(
                    f"Incorrect parsed_metadata initialization type: {parsed_metadata}"
                )

            # In this case the name of the file should be taken into account in the context path
            file_path_parts = list(reversed(cache_entry.rel_path.parts))
            regex_path = context["!parsing"]["path"].split("/")
            regex_path.reverse()

            # If the match is negative then we skip the current cache entry
            if not _pattern_parts_match(regex_path, file_path_parts, context):
                continue

        # If not in a regex/path context then parsed metadata is structured
        # in a list and metadata is appended to it
        if parsed_metadata is None:
            parsed_metadata = []

        # Lazy loading handling
        metadata = cache_entry.load_metadata()

        # Compute additional directives if given
        if "!parsing" in context:
            if "keys" in context["!parsing"]:
                metadata = parser._filter_metadata(
                    metadata, context["!parsing"]["keys"], **kwargs
                )

            # Unpacking should only be done for singular nested values i.e. only one key per nesting level
            if "unpack" in context["!parsing"]:
                if isinstance(context["!parsing"]["unpack"], bool):
                    if not context["!parsing"]["unpack"]:
                        _LOG.debug(dumps(context["!parsing"], indent=4, default=vars))
                        raise RuntimeError(
                            f"Incorrect unpacking configuration in !parsing context: unpack={False}"
                        )

                    metadata = _unpack_singular_nested_value(metadata)

                elif isinstance(context["!parsing"]["unpack"], int):
                    if context["!parsing"]["unpack"] == 0:
                        _LOG.debug(dumps(context["!parsing"], indent=4, default=vars))
                        raise RuntimeError(
                            f"Incorrect unpacking configuration in !parsing context: unpack={0}"
                        )

                    metadata = _unpack_singular_nested_value(
                        metadata, context["!parsing"]["unpack"]
                    )

        # Update parsed metadata
        # When in a regex context then resulting parsed metadata is a dict
        if isinstance(parsed_metadata, dict):

            # When updating the parsed metadata dict,
            # the relative path to cache entry is used,
            # however the filename is changed to the name of key of the interpreted_schema key.
            relative_path = cache_entry.rel_path.parent / interpreted_schema.key
            _update_dict_with_parts(
                parsed_metadata, metadata, list(relative_path.parts)
            )

        # Else by default we append to a list
        else:
            parsed_metadata.append(metadata)

    # Update tree according to metadata retrieved
    if isinstance(parsed_metadata, list):
        tree = parsed_metadata[0] if len(parsed_metadata) == 1 else parsed_metadata
    else:
        tree = parsed_metadata

    return tree


def _format_calculate_rule(
    formatter: Formatter,
    interpreted_schema: _SchemaEntry,
    branch: list,
    value: dict,
    **kwargs,
) -> Union[int, float]:
    # Returns numerical value based on a mathematical equation using parsing results as variables.
    # For each variable a corresponding numerical value in parsing results must be found.
    # At this point variable, count and names have been verified by Interpreter.

    if not isinstance(value, dict):
        raise TypeError(
            f"Incorrect value type found while formatting calculation: {type(value)}"
        )

    if "add_description" in kwargs and kwargs["add_description"]:
        _LOG.warning("Add description enabled in calculate directive. Ignoring option.")
        kwargs["add_description"] = False

    if "add_type" in kwargs and kwargs["add_type"]:
        _LOG.warning("Add type enabled in calculate directive. Ignoring option.")
        kwargs["add_type"] = False

    if not all(key in value for key in ["expression", "variables"]):
        raise RuntimeError(
            f"Malformed !calculate entry found while formatting calculation: {value}"
        )

    expression = value["expression"]
    variables = value["variables"]

    parsing_values = {}
    for variable in variables:
        entry = variables[variable]
        if not isinstance(entry, _SchemaEntry):
            raise TypeError(
                f"Incorrect variable type found while formatting calculation: {type(entry)}"
            )
        if not len(entry.items()) == 1:
            raise ValueError(
                f"Incorrect variable entry found while formatting calculation: {entry}"
            )

        parsing_values[variable] = _format_parser_id_rule(
            formatter, entry, branch, entry["!parser_id"], **kwargs
        )

    formatted_expression = expression.format(**parsing_values)

    return eval(formatted_expression)


_FORMATTING_RULES = {
    "!parser_id": _format_parser_id_rule,
    "!calculate": _format_calculate_rule,
}
