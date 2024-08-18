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

from .logger import _LOG, _is_debug
from .helper_classes import _SchemaEntry
from .helper_functions import (
    _pattern_parts_match,
    _update_dict_with_parts,
    _unpack_nested_value,
    _filter_metadata,
    _add_info_from_schema,
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
        _LOG.debug("value type: %s\nexpected type: %s", str(type(value)), str(str))
        raise TypeError("Incorrect value type for formatting parser id.")

    # Currently only one parser reference per entry is allowed
    # and if a reference exists it must be the only content in the entry
    if len(interpreted_schema.items()) > 1:
        if _is_debug():
            _LOG.debug(
                "schema entry key: %s\nschema entry content: %s",
                interpreted_schema.key,
                dumps(interpreted_schema._content, indent=4, default=vars),
            )
        raise RuntimeError("Invalid SchemaEntry content.")

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
                if _is_debug():
                    _LOG.debug(
                        "parsed metadata: %s\ncontext: %s",
                        dumps(parsed_metadata, indent=4, default=vars),
                        dumps(context, indent=4, default=vars),
                    )
                raise TypeError("Incorrect parsed_metadata type.")

            # We skip the last element as it represents the node name of the parsed metadata
            # not to be included in the path of the tree
            file_path_parts = list(reversed(cache_entry.rel_path.parent.parts))
            reversed_branch = list(reversed(branch[: len(branch) - 1]))

            # If there is a mismatch we skip the cache entry
            if not _pattern_parts_match(reversed_branch, file_path_parts):
                continue

        parsing_context = context["!parsing"] if "!parsing" in context else None

        # If path information is present in parser directives match file path to given regex path
        if parsing_context is not None and "path" in parsing_context:

            # Parsed metadata should be structured in a dictionary
            # where keys are filenames and values are metadata
            if parsed_metadata is None:
                parsed_metadata = {}
            elif not isinstance(parsed_metadata, dict):
                if _is_debug():
                    _LOG.debug(
                        "parsed metadata: %s\ncontext: %s",
                        dumps(parsed_metadata, indent=4, default=vars),
                        dumps(context, indent=4, default=vars),
                    )
                raise TypeError("Incorrect parsed_metadata type.")

            # In this case the name of the file should be taken into account in the context path
            file_path_parts = list(reversed(cache_entry.rel_path.parts))
            regex_path = parsing_context["path"].split("/")
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
        if parsing_context is not None and "keys" in parsing_context:
            metadata = _filter_metadata(
                metadata,
                parsing_context["keys"],
            )

        add_description = False
        if "add_description" in kwargs:
            add_description = kwargs["add_description"]

        add_type = False
        if "add_type" in kwargs:
            add_type = kwargs["add_type"]

        _add_info_from_schema(metadata, parser.schema, add_description, add_type)

        # Unpacking should only be done for singular nested values i.e. only one key per nesting level
        if parsing_context is not None and "unpack" in parsing_context:
            unpack = parsing_context["unpack"]
            if isinstance(unpack, bool):
                if not unpack:
                    if _is_debug():
                        _LOG.debug(
                            "parsing context: %s",
                            dumps(parsing_context, indent=4, default=vars),
                        )
                    raise ValueError(
                        "Incorrect unpacking configuration in !parsing context: unpack=False."
                    )

                metadata = _unpack_nested_value(metadata)

            elif isinstance(unpack, int):
                if unpack == 0:
                    if _is_debug():
                        _LOG.debug(
                            "parsing context: %s",
                            dumps(parsing_context, indent=4, default=vars),
                        )
                    raise ValueError(
                        "Incorrect unpacking configuration in !parsing context: unpack=0."
                    )

                metadata = _unpack_nested_value(metadata, unpack)
            else:
                _LOG.debug(
                    "Unpack type: %s, expected types: %s or %s",
                    str(type(unpack)),
                    str(bool),
                    str(int),
                )
                raise TypeError(
                    "Incorrect unpacking configuration in !parsing context."
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
        _LOG.debug("value type: %s\nexpected type: %s", str(type(value)), str(dict))
        raise TypeError("Incorrect value type found while formatting calculation")

    if not all(key in value for key in ["expression", "variables"]):
        if _is_debug():
            _LOG.debug(
                "!calculate directive value: %s", dumps(value, indent=4, default=vars)
            )
        raise RuntimeError(
            "Malformed !calculate entry found while formatting calculation."
        )

    add_description = kwargs.pop("add_description", False)
    add_type = kwargs.pop("add_type", False)

    expression = value["expression"]
    variables = value["variables"]

    parsing_values = {}
    for variable in variables:
        entry = variables[variable]
        if not isinstance(entry, _SchemaEntry):
            _LOG.debug(
                "entry type: %s\nexpected type: %s", str(type(entry)), str(_SchemaEntry)
            )
            raise TypeError(
                "Incorrect variable type found while formatting calculation."
            )
        if not len(entry.items()) == 1:
            if _is_debug():
                _LOG.debug(
                    "entry content: %s", dumps(entry._content, indent=4, default=vars)
                )
            raise ValueError(
                "Incorrect variable entry found while formatting calculation."
            )

        parsing_values[variable] = _format_parser_id_rule(
            formatter, entry, branch, entry["!parser_id"], **kwargs
        )

    formatted_expression = expression.format(**parsing_values)
    result = eval(formatted_expression)

    if add_description or add_type:
        # In calculate directive description or type are retrieved from formatting schema
        # It is necessary to generate a mock dictionary tree following formatting schema to be able to use _add_info_from_schema function
        # After retrieving info from schema then unpacking is used to remove mock tree and getting the annotated result.
        mock_tree = {}
        _update_dict_with_parts(mock_tree, result, interpreted_schema.key_path)
        _add_info_from_schema(mock_tree, formatter.schema, add_description, add_type)
        result = _unpack_nested_value(mock_tree, level=len(interpreted_schema.key_path))

    return result


_FORMATTING_RULES = {
    "!parser_id": _format_parser_id_rule,
    "!calculate": _format_calculate_rule,
}
