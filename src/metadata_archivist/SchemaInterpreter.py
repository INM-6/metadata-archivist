#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""

Schema Interpretation class for creating the
interpretable structure for the unified metadata file.
See README.md/SchemaInterpreter section.

Interpretation rules can be customized or added through
the INTERPRETATION_RULES dictionary.

Authors: Jose V., Matthias K.

"""

from json import dumps
from copy import deepcopy
from collections.abc import Iterable
from typing import Optional, Any, Union

from .Logger import LOG, is_debug

"""
Constants for schema specific/special values to be considered when parsing.
"""
_KNOWN_REFS = [
    "#/$defs/",
]

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

        # INTERPRETATION_RULES constant is created inside
        # class instance to be able to pass self to function context
        self._INTERPRETATION_RULES = {
            "properties": self._process_simple_property,
            "unevaluatedProperties": self._process_simple_property,
            "additionalProperties": self._process_simple_property,
            "patternProperties": self._process_pattern_property,
            "!extractor": self._process_extractor_directive,
            "$ref": self._process_reference,
            "!varname": self._process_varname,
        }

    def _process_simple_property(self, prop_val: dict, prop_key: str, parent_key: str, entry: SchemaEntry) -> SchemaEntry:
        # Known simple properties return recursion results without branching
        return self._interpret_schema(prop_val, parent_key, entry)

    def _process_pattern_property(self, prop_val: dict, prop_key: str, parent_key: str, entry: SchemaEntry) -> SchemaEntry:
        # We create a regex context and recurse over the contents of the property.
        entry.context.update({"useRegex": True})

        return self._interpret_schema(prop_val, parent_key, entry)

    def _process_extractor_directive(self, prop_val: Union[str, dict], prop_key: str, parent_key: str, entry: SchemaEntry) -> SchemaEntry:
        # We create an !extractor context but keep on with current recursion level
        # Contents of this dictionary are not supposed to contain additional directives/properties.
        entry.context.update({prop_key: prop_val})

        return entry 

    def _process_reference(self, prop_val: dict, prop_key: str, parent_key: str, entry: SchemaEntry) -> SchemaEntry:
        # Check if reference is well formed against knowledge base
        if not any(prop_val.startswith(ss) for ss in _KNOWN_REFS):
            raise RuntimeError(f"Malformed reference prop_value: {prop_key}: {prop_val}")

        # Call _process_refs to check for correctness before creating extraction context.
        entry = self._process_refs(prop_val, entry)

        return entry
        

    def _process_varname(self, prop_val: dict, prop_key: str, parent_key: str, entry: SchemaEntry) -> SchemaEntry:
        # Check if regex context is present in current entry
        if "useRegex" not in entry.context:
            raise RuntimeError("Contextless !varname found")
        # Add a !varname context which contains the name to use
        # and to which expression it corresponds to.
        entry.context.update({prop_key: prop_val, "regexp": parent_key})
        
        return entry
        
    def _recurse_sub_schema(self, sub_schema: dict, entry: SchemaEntry, filters: Optional[list] = None) -> list:
        # TODO: recursively explore extractor sub-schema and collect entry names and description.
        # List of keys can be passed as filters to select a branch of the extractor sub schema.
        # Resulting list should contain all the #/property that needs to be linked
        # with their respective positions so that _process_refs can take care of creating links
        # and avoid circular dependencies.
        return []

    def _process_refs(self, prop_val: str, entry: SchemaEntry) -> SchemaEntry:

        # Test correctness of reference
        val_split = prop_val.split("/")
        if len(val_split) < 3:
            raise ValueError(f"Malformed reference: {prop_val}")
        ex_id = val_split[2]
        if ex_id not in self._schema["$defs"]:
            raise KeyError(f"Extractor not found: {ex_id}")
        
        # Add identified extractor to context
        LOG.debug(f"processing reference to: {ex_id}")
        entry["$extractor_id"] = ex_id

        # Further process reference e.g. filters, internal property references -> links
        sub_schema = self._schema["$defs"][ex_id]["properties"]
        links = self._recurse_sub_schema(sub_schema, entry, filters=None if len(val_split) <= 3 else val_split[3:])
        # TODO: take care of linking

        return entry
    
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
            if key in self._INTERPRETATION_RULES:
                # This error is only raised if an interpretation rule is found at root of schema properties
                # rules must be defined in individual items of the properties, hence a parent key should
                # always be present.
                if parent_key is None:
                    LOG.debug(dumps(relative_root, indent=4, default=vars))
                    raise RuntimeError("Cannot interpret rule without parent key.")
                relative_root = self._INTERPRETATION_RULES[key](val, key, parent_key, relative_root)

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
        