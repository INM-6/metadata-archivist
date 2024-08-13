#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""

Schema Interpretation class for creating the
interpretable structure for the unified metadata file.
See README.md/SchemaInterpreter section.

Only for internal use.

Authors: Jose V., Matthias K.

"""

from json import dumps
from copy import deepcopy
from typing import Optional
from collections.abc import Iterable

from .Logger import _LOG, _is_debug
from .helper_classes import _SchemaEntry


class _SchemaInterpreter:
    """
    Functionality class used for interpreting the schema.
    When defining the JSON schema with additional directives,
    the object is cannot be used directly for structuring.
    To this end, this class is used to generate an intermediary structure
    that respects the schema and its directives while being functionally
    usable as a mirror for structuring the final metadata file.

    Attributes:
        structure: root SchemaEntry used for interpretation.
        rules: dictionary of interpretation rules.

    Methods:
        generate: convenience method to generate schema interpretation.
    """

    def __init__(self, schema: dict) -> None:
        """
        Constructor of SchemaInterpreter.

        Arguments:
            schema: dictionary containing schema to interpret.
        """

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
        self.structure = _SchemaEntry()

        # We load INTERPRETATION_RULES directly in instance to avoid circular importing issues
        from .interpretation_rules import _INTERPRETATION_RULES
        self.rules = deepcopy(_INTERPRETATION_RULES)

    def _interpret_schema(self,
                         properties: dict,
                         _parent_key: Optional[str] = None,
                         _relative_root: Optional[_SchemaEntry] = None):
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
        e.g. !parsing in which case context is added then the current recursion will
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

        Arguments:
            properties: dictionary of schema properties to interpret.
            _parent_key: key of parent property where method was called. Recursion variable.
            _relative_root: relative SchemaEntry where method was called. Recursion variable. Defaults to self contained structure.
        """

        if _relative_root is None:
            _relative_root = self.structure

        # For all the properties in the given schema
        for key, val in properties.items():

            # If the key is known as an interpretation rule
            # call the function mapped into the INTERPRETATION_RULE dictionary
            if key in self.rules:
                # This error is only raised if an interpretation rule is found at root of schema properties
                # rules must be defined in individual items of the properties, hence a parent key should
                # always be present.
                if _parent_key is None:
                    _LOG.debug(dumps(_relative_root, indent=4, default=vars))
                    raise RuntimeError("Cannot interpret rule without parent key.")
                _relative_root = self.rules[key](self, val, key, _parent_key, _relative_root)

            else:
                # Case dict i.e. branch
                if isinstance(val, dict):
                    _relative_root[key] = self._interpret_schema(val, key, _SchemaEntry(key=key, context=deepcopy(_relative_root.context)))

                # Case str i.e. leaf
                elif isinstance(val, str):
                    _LOG.debug(f"Ignoring key value pair: {key}: {val}")

                # Else not-implemented/ignored
                else:
                    if isinstance(val, Iterable):
                        raise NotImplementedError(f"Unknown iterable type: {key}: {type(val)}")
                    else:
                        _LOG.debug(f"Ignoring key value pair: {key}: {val}")

        return _relative_root
    
    def generate(self) -> _SchemaEntry:
        """
        Convenience function to launch interpretation recursion over the schema.
        Results is also internally stored for future access.

        Returns:
            self contained SchemaEntry
        """
        if _is_debug():
            # Passing through dumps for pretty printing,
            # however can be costly, so checking if debug is enabled first
            _LOG.debug(dumps(self._schema, indent=4, default=vars))

        if self.structure.is_empty():
            self.structure = self._interpret_schema(self._schema["properties"])

        if _is_debug():
            # Passing through dumps for pretty printing,
            # however can be costly, so checking if debug is enabled first
            _LOG.debug(dumps(self.structure, indent=4, default=vars))
        
        return self.structure
        