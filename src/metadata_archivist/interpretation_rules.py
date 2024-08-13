#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""

Interpretation rules defined for the SchemaInterpreter
Rules can be customized or added through
the INTERPRETATION_RULES dictionary.

All rule functions must have the same arguments.

Arguments:
    interpreter: instance of schema interpreter. Used to continue interpretation on generated entry.
    prop_val: value of property on which rule was called.
    prop_key: key of property on which rule was called.
    parent_key: key of parent property where current property is.
    entry: schema entry where property is being interpreted.

Returns:
    interpreted schema entry.

Only for internal use.

Authors: Jose V., Matthias K.

"""

from re import sub
from copy import deepcopy
from typing import Optional, Union

from .Logger import _LOG
from .helper_functions import _math_check
from .SchemaInterpreter import _SchemaInterpreter, _SchemaEntry


# Constants for schema specific/special values to be considered when parsing.
_KNOWN_REFS = [
    "#/$defs/",
]


def _interpret_simple_property_rule(interpreter: _SchemaInterpreter, prop_val: dict, prop_key: str, parent_key: str, entry: _SchemaEntry) -> _SchemaEntry:
    # Known simple properties return recursion results without branching
    return interpreter._interpret_schema(prop_val, parent_key, entry)


def _interpret_pattern_property_rule(interpreter: _SchemaInterpreter, prop_val: dict, prop_key: str, parent_key: str, entry: _SchemaEntry) -> _SchemaEntry:
    # We create a regex context and recurse overfrom copy import deepcopy the contents of the property.
    entry.context.update({"useRegex": True})

    return interpreter._interpret_schema(prop_val, parent_key, entry)


def _interpret_parsing_directive_rule(interpreter: _SchemaInterpreter, prop_val: Union[str, dict], prop_key: str, parent_key: str, entry: _SchemaEntry) -> _SchemaEntry:
    # We create an !parsing context but keep on with current recursion level
    # Contents of this dictionary are not supposed to be handled by the interpreter.
    entry.context.update({prop_key: prop_val})

    return entry 


def _interpret_varname_directive_rule(interpreter: _SchemaInterpreter, prop_val: dict, prop_key: str, parent_key: str, entry: _SchemaEntry) -> _SchemaEntry:
    # Check if regex context is present in current entry
    if "useRegex" not in entry.context:
        raise RuntimeError("Contextless !varname found")
    # Add a !varname context which contains the name to use
    # and to which expression it corresponds to.
    entry.context.update({prop_key: prop_val, "regexp": parent_key})
    
    return entry


def _interpret_reference_rule(interpreter: _SchemaInterpreter, prop_val: dict, prop_key: str, parent_key: str, entry: _SchemaEntry) -> _SchemaEntry:
    # Check if reference is well formed against knowledge base
    if not any(prop_val.startswith(ss) for ss in _KNOWN_REFS):
        raise RuntimeError(f"Malformed reference prop_value: {prop_key}: {prop_val}")
    
    # Get schema definitions
    defs = interpreter._schema["$defs"]

    # Call _process_refs to check for correctness before creating parsing context.
    entry = __interpret_refs(defs, prop_val, entry)

    return entry


def __interpret_refs(definitions: dict, prop_val: str, entry: _SchemaEntry) -> _SchemaEntry:
    """
    Auxiliary function to check reference to Parser.

    Arguments:
        definitions: schema definitions dictionary.
        prop_val: string value of property where reference is invoked. Should correspond to Parser name.
        entry: schema entry where Parser was referenced.

    Returns:
        schema entry containing reference information.
    """
    # Test correctness of reference
    val_split = prop_val.split("/")
    if len(val_split) < 3:
        raise ValueError(f"Malformed reference: {prop_val}")

    # Test for existence of Parser id
    pid = val_split[2]
    if pid not in definitions:
        raise KeyError(f"Parser not found: {pid}")
    
    # Add identified Parser to context
    _LOG.debug(f"processing reference to: {pid}")
    entry["!parser_id"] = pid

    # Further process reference e.g. filters, internal property references -> links
    sub_schema = definitions[pid]["properties"]
    links = __interpret_sub_schema(sub_schema, entry, filters=None if len(val_split) <= 3 else val_split[3:])
    # TODO: take care of linking

    return entry


def __interpret_sub_schema(sub_schema: dict, entry: _SchemaEntry, filters: Optional[list] = None) -> list:
    """
    WIP
    Recursively explore Parser sub-schema and collect entry names and description.
    List of keys can be passed as filters to select a branch of the Parser sub schema.
    Resulting list should contain all the #/property that needs to be linked
    with their respective positions so that _process_refs can take care of creating links
    and avoid circular dependencies.

    Arguments:
        sub_schema: dictionary of Parser schema.
        entry: schema entry where Parser was referenced.
        filters: list of filters to apply to Parser schema.

    Returns:
        list of filtered sub-properties of Parser schema.
    """

    # TODO

    return []


def _interpret_calculate_directive_rule(interpreter: _SchemaInterpreter, prop_val: dict, prop_key: str, parent_key: str, entry: _SchemaEntry) -> _SchemaEntry:
    # Calculates simple math expressions using values from parsers.
    # Requires referenced parsers to return numerical values.
    # references can be supplemented with !parsing directives to properly select value.
    if not all(key in prop_val for key in ["expression", "variables"]):
        raise RuntimeError(f"Malformed !calculate directive: {prop_key}: {prop_val}")
    
    expression = prop_val["expression"]
    if not isinstance(prop_val["expression"], str):
        raise TypeError(f"Incorrect expression type in !calculate directive: expression={expression}")

    cleaned_expr = sub(r"\s", "", expression)
    correct, variable_names = _math_check(cleaned_expr)
    if not correct:
        raise ValueError(f"Incorrect expression in !calculate directive: expression={cleaned_expr}")
    
    variables = prop_val["variables"]
    if not isinstance(variables, dict):
        raise TypeError(f"Incorrect variables type in !calculate directive: variables={variables}")
    
    if len(variable_names) != len(variables):
        raise RuntimeError(f"Variables count mismatch in !calculate directive: expression={expression}, variables={variables}, names={variable_names}")
    
    # At this point we check if each variable entry corresponds to a reference to a Parser
    variable_entries = {}
    for variable in variables:
        if not variable in variable_names:
            raise RuntimeError(f"Variable name mismatch in !calculate directive: variable={variable}")

        value = variables[variable]
        if not isinstance(value, dict):
            raise TypeError(f"Incorrect variable type in !calculate directive: {variable}={value}")
        
        if not "$ref" in value:
            raise RuntimeError(f"Variable does not reference a Parser in !calculate directive: {variable}={value}")
        
        # We create a SchemaEntry in the context to be specially handled by the Formatter
        new_entry = _SchemaEntry(key=prop_key, context=deepcopy(entry.context))

        if "!parsing" in value:
           _interpret_parsing_directive_rule(interpreter, value["!parsing"], "!parsing", prop_key, new_entry)

        _interpret_reference_rule(interpreter, value["$ref"], "$ref", prop_key, new_entry)

        variable_entries[variable] = new_entry

    entry[prop_key] = {
        "expression": cleaned_expr,
        "variables": variable_entries
    }

    return entry


_INTERPRETATION_RULES = {
    "properties": _interpret_simple_property_rule,
    "unevaluatedProperties": _interpret_simple_property_rule,
    "additionalProperties": _interpret_simple_property_rule,
    "patternProperties": _interpret_pattern_property_rule,
    "!parsing": _interpret_parsing_directive_rule,
    "$ref": _interpret_reference_rule,
    "!varname": _interpret_varname_directive_rule,
    "!calculate": _interpret_calculate_directive_rule
}
