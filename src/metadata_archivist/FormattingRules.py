
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Formatting rules defined for the Formatter
Rules can be customized or added through
the FORMATTING_RULES dictionary.

All rule functions must have the same arguments.

Authors: Jose V., Matthias K.

"""

from json import dumps
from typing import Optional, Union

from .Logger import LOG
from .Formatter import Formatter
from .SchemaInterpreter import SchemaEntry
from .helper_functions import _pattern_parts_match, _update_dict_with_parts

def _format_parser_id_rule(formatter: Formatter, interpreted_schema: SchemaEntry, branch: list, value: str, **kwargs) -> dict:
    if not isinstance(value, str):
        raise ValueError(f"Incorrect value type for formatting parser: {type(value)}")

    # Currently only one parser reference per entry is allowed
    # and if a reference exists it must be the only content in the entry
    if len(interpreted_schema.items()) > 1:
        LOG.debug(dumps(interpreted_schema._content, indent=4, default=vars))
        raise RuntimeError(f"Invalid entry content {interpreted_schema.key}: {interpreted_schema._content}")
    
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
                LOG.debug(f"parsed metadata: {parsed_metadata}\n\ncontext: {context}")
                raise RuntimeError(f"Incorrect parsed_metadata initialization type: {parsed_metadata}")

            # We skip the last element as it represents the node name of the parsed metadata
            # not to be included in the path of the tree
            file_path_parts = list(reversed(cache_entry.rel_path.parent.parts))
            reversed_branch = list(reversed(branch[:len(branch) - 1]))

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
                LOG.debug(f"parsed metadata: {parsed_metadata}\n\ncontext: {context}")
                raise RuntimeError(f"Incorrect parsed_metadata initialization type: {parsed_metadata}")

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
        if "!parsing" in context and "keys" in context["!parsing"]:
            metadata = parser.filter_metadata(
                metadata, context["!parsing"]["keys"],
                **kwargs)

        # Update parsed metadata
        # When in a regex context then resulting parsed metadata is a dict
        if isinstance(parsed_metadata, dict):

            # When updating the parsed metadata dict,
            # the relative path to cache entry is used,
            # however the filename is changed to the name of key of the interpreted_schema key.
            relative_path = cache_entry.rel_path.parent / interpreted_schema.key
            _update_dict_with_parts(parsed_metadata, metadata, list(relative_path.parts))

        # Else by default we append to a list
        else:
            parsed_metadata.append(metadata)

    # Update tree according to metadata retrieved
    if isinstance(parsed_metadata, list):
        tree = parsed_metadata[0] if len(parsed_metadata) == 1 else parsed_metadata
    else:
        tree = parsed_metadata

    return tree

_FORMATTING_RULES = {
    "$parser_id": _format_parser_id_rule, 
}
