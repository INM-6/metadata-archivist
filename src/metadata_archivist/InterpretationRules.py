#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Interpretation rules defined for the SchemaInterpreter
Rules can be customized or added through
the INTERPRETATION_RULES dictionary.

All rule functions must have the same arguments.

Authors: Jose V., Matthias K.

"""

from typing import Optional, Union

from .Logger import LOG
from .SchemaInterpreter import SchemaInterpreter, SchemaEntry

"""
Constants for schema specific/special values to be considered when parsing.
"""
_KNOWN_REFS = [
    "#/$defs/",
]

def _process_simple_property(interpreter: SchemaInterpreter, prop_val: dict, prop_key: str, parent_key: str, entry: SchemaEntry) -> SchemaEntry:
    # Known simple properties return recursion results without branching
    return interpreter._interpret_schema(prop_val, parent_key, entry)

def _process_pattern_property(interpreter, prop_val: dict, prop_key: str, parent_key: str, entry: SchemaEntry) -> SchemaEntry:
    # We create a regex context and recurse over the contents of the property.
    entry.context.update({"useRegex": True})

    return interpreter._interpret_schema(prop_val, parent_key, entry)

def _process_parser_directive(interpreter: SchemaInterpreter, prop_val: Union[str, dict], prop_key: str, parent_key: str, entry: SchemaEntry) -> SchemaEntry:
    # We create an !extractor context but keep on with current recursion level
    # Contents of this dictionary are not supposed to be handled by the interpreter.
    entry.context.update({prop_key: prop_val})

    return entry 

def _process_reference(interpreter: SchemaInterpreter, prop_val: dict, prop_key: str, parent_key: str, entry: SchemaEntry) -> SchemaEntry:
    # Check if reference is well formed against knowledge base
    if not any(prop_val.startswith(ss) for ss in _KNOWN_REFS):
        raise RuntimeError(f"Malformed reference prop_value: {prop_key}: {prop_val}")
    
    # Get schema definitions
    defs = interpreter._schema["$defs"]

    # Call _process_refs to check for correctness before creating parsing context.
    entry = _process_refs(defs, prop_val, entry)

    return entry
    

def _process_varname(interpreter: SchemaInterpreter, prop_val: dict, prop_key: str, parent_key: str, entry: SchemaEntry) -> SchemaEntry:
    # Check if regex context is present in current entry
    if "useRegex" not in entry.context:
        raise RuntimeError("Contextless !varname found")
    # Add a !varname context which contains the name to use
    # and to which expression it corresponds to.
    entry.context.update({prop_key: prop_val, "regexp": parent_key})
    
    return entry
    
def _recurse_sub_schema(sub_schema: dict, entry: SchemaEntry, filters: Optional[list] = None) -> list:
    # TODO: recursively explore Parser sub-schema and collect entry names and description.
    # List of keys can be passed as filters to select a branch of the Parser sub schema.
    # Resulting list should contain all the #/property that needs to be linked
    # with their respective positions so that _process_refs can take care of creating links
    # and avoid circular dependencies.
    return []

def _process_refs(definitions: dict, prop_val: str, entry: SchemaEntry) -> SchemaEntry:
    # Test correctness of reference
    val_split = prop_val.split("/")
    if len(val_split) < 3:
        raise ValueError(f"Malformed reference: {prop_val}")

    # Test for existence of Parser id
    pid = val_split[2]
    if pid not in definitions:
        raise KeyError(f"Parser not found: {pid}")
    
    # Add identified Parser to context
    LOG.debug(f"processing reference to: {pid}")
    entry["$extractor_id"] = pid

    # Further process reference e.g. filters, internal property references -> links
    sub_schema = definitions[pid]["properties"]
    links = _recurse_sub_schema(sub_schema, entry, filters=None if len(val_split) <= 3 else val_split[3:])
    # TODO: take care of linking

    return entry

_INTERPRETATION_RULES = {
    "properties": _process_simple_property,
    "unevaluatedProperties": _process_simple_property,
    "additionalProperties": _process_simple_property,
    "patternProperties": _process_pattern_property,
    "!extractor": _process_parser_directive,
    "$ref": _process_reference,
    "!varname": _process_varname,
}
