#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""

Schema Interpretation class for creating the
interpretable structure for the unified metadata file.
See README.md/SchemaInterpreter section.

Authors: Jose V., Matthias K.

"""

from json import dumps
from copy import deepcopy
from typing import Optional, Any
from collections.abc import Iterable

from .Logger import LOG, is_debug

class SchemaEntry:
    """
    Convenience superset of dictionary class.
    Used to recursively generate nested dictionary structure to serve as an intermediary between schema and metadata file.
    Contains additional context dictionary for a given tree level and the name of the root node.
    For initial root node, no name is defined, however for subsequent nodes there should always be a name.
    Get, set, and iteration access is redirected to internal storage.
    """

    key: str
    context: dict
    _content: dict

    def __init__(self, key: Optional[str] = None, context: Optional[dict] = None) -> None:
       self.key = key
       self.context = context if context is not None else {}
       self._content = {}
       self._iterator = None

    def __getitem__(self, key) -> Any:
        return self._content[key]
    
    def __setitem__(self, key, value) -> None:
        self._content[key] = value

    def __contains__(self, key) -> bool:
        return key in self._content
    
    def items(self):
        return self._content.items()
    
    def is_empty(self) -> bool:
        return len(self._content) == 0


class SchemaInterpreter:
    """
    Functionality class used for interpreting the schema.
    When defining the JSON schema with additional directives,
    the object is cannot be used directly for structuring.
    To this end, this class is used to generate an intermediary structure
    that respects the schema and its directives while being functionally
    usable as a mirror for structuring the final metadata file.
    """

    _schema: dict
    structure: SchemaEntry
    

    def __init__(self, schema: dict) -> None:
        if not isinstance(schema, dict):
            raise RuntimeError(
                f'Incorrect schema used for iterator {schema}'
            )
        if 'properties' not in schema or not isinstance(
                schema['properties'], dict):
            raise RuntimeError(
                f'Incorrect schema structure, root is expected to contain properties dictionary: {schema}'
            )
        if '$defs' not in schema or not isinstance(
                schema['$defs'], dict):
            raise RuntimeError(
                f'Incorrect schema structure, root is expected to contain $defs dictionary: {schema}'
            )

        self._schema = schema
        self.structure = SchemaEntry()

        # We load INTERPRETATION_RULES directly in instance to avoid circular importing issues
        from .InterpretationRules import _INTERPRETATION_RULES
        self.rules = deepcopy(_INTERPRETATION_RULES)

    def _interpret_schema(self,
                         properties: dict,
                         parent_key: Optional[str] = None,
                         relative_root: Optional[SchemaEntry] = None):
        """
        Recursive method to explore JSON schema.
        Following the technical assumptions made (cf. README.md/SchemaInterpreter),
        only the properties at the root of the schema are interpreted (recursively so),
        items of the property are of type key[str] -> value[dict|str],
        any other type is currently ignored as NotImplemented feature.
        When interpreting we generate a SchemaEntry with nested tree structure.

        - When processing dictionaries, these can either be simple properties,
        special properties or intermediate structures.
        If the dictionary is a simple property then recursion is called on its contents
        without creating a new branch.
        If the dictionary is a special property then: either it is a composite directive
        e.g. !extractor in which case context is added then the current recursion will
        continue until arriving at a leaf (str) and leaf processing is in charge of using
        the enriched entry. Otherwise, the property indicates a new recursion with additional
        context e.g. patternProperties indicate a new recursion with regular expression file
        matching. However the no new branch is created and the recursion results are added to
        the current branch.
        Any other dictionaries are considered as intermediary structures hence a new branch
        is created and a recursion is done on its contents.
        The previous is the ONLY SCENARIO FOR BRANCHING inside the interpretable data structure.

        - When processing strings, they can be either JSON schema additional information
        in which case it is ignored or they can be additional directives e.g. $ref or !varname
        Both of which are specially processed to enriched the context.

        """
        if relative_root is None:
            relative_root = self.structure

        # For all the properties in the given schema
        for key, val in properties.items():

            # If the key is known as an interpretation rule
            # call the function mapped into the INTERPRETATION_RULE dictionary
            if key in self.rules:
                # This error is only raised if an interpretation rule is found at root of schema properties
                # rules must be defined in individual items of the properties, hence a parent key should
                # always be present.
                if parent_key is None:
                    LOG.debug(dumps(relative_root, indent=4, default=vars))
                    raise RuntimeError("Cannot interpret rule without parent key.")
                relative_root = self.rules[key](self, val, key, parent_key, relative_root)

            else:
                # Case dict i.e. branch
                if isinstance(val, dict):
                    relative_root[key] = self._interpret_schema(val, key, SchemaEntry(key=key, context=deepcopy(relative_root.context)))

                # Case str i.e. leaf
                elif isinstance(val, str):
                    LOG.debug(f"Ignoring key value pair: {key}: {val}")

                # Else not-implemented/ignored
                else:
                    if isinstance(val, Iterable):
                        raise NotImplementedError(f"Unknown iterable type: {key}: {type(val)}")
                    else:
                        LOG.debug(f"Ignoring key value pair: {key}: {val}")

        return relative_root
    
    def generate(self) -> SchemaEntry:
        """
        Convenience function to launch interpretation recursion over the schema.
        Results is also internally stored for future access.
        """
        if is_debug():
            # Passing through dumps for pretty printing,
            # however can be costly, so checking if debug is enabled first
            LOG.debug(dumps(self._schema, indent=4, default=vars))

        if self.structure.is_empty():
            self.structure = self._interpret_schema(self._schema["properties"])

        if is_debug():
            # Passing through dumps for pretty printing,
            # however can be costly, so checking if debug is enabled first
            LOG.debug(dumps(self.structure, indent=4, default=vars))
        
        return self.structure
        