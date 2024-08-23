#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""

Module containing collection of rules as functions to interpreter user defined schema.

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

exports:
    INTERPRETATION_RULES: dictionary mapping schema keys to interpretation rules.

Authors: Jose V., Matthias K.

"""

from re import sub
from json import dumps
from typing import Callable
from typing import Optional, Union, TYPE_CHECKING

from metadata_archivist.logger import LOG, is_debug
from metadata_archivist.helper_functions import math_check

if TYPE_CHECKING:
    from metadata_archivist.helper_classes import SchemaInterpreter, SchemaEntry

# Constants for schema specific/special values to be considered when parsing.
_KNOWN_REFS = [
    "#/$defs/",
]


def _interpret_simple_property_rule(
    interpreter: "SchemaInterpreter",
    prop_val: dict,
    prop_key: str,
    parent_key: str,
    entry: "SchemaEntry",
) -> "SchemaEntry":
    # Known simple properties return recursion results without branching
    return interpreter.interpret_schema(prop_val, parent_key, entry)


def _interpret_pattern_property_rule(
    interpreter: "SchemaInterpreter",
    prop_val: dict,
    prop_key: str,
    parent_key: str,
    entry: "SchemaEntry",
) -> "SchemaEntry":
    # We create a regex context and recurse over the contents of the property.
    entry.context.update({"useRegex": True})

    return interpreter.interpret_schema(prop_val, parent_key, entry)


def _interpret_parsing_directive_rule(
    interpreter: "SchemaInterpreter",
    prop_val: Union[str, dict],
    prop_key: str,
    parent_key: str,
    entry: "SchemaEntry",
) -> "SchemaEntry":
    # We create an !parsing context but keep on with current recursion level
    # Contents of this dictionary are not supposed to be handled by the interpreter.
    entry.context.update({prop_key: prop_val})

    return entry


def _interpret_varname_directive_rule(
    interpreter: "SchemaInterpreter",
    prop_val: dict,
    prop_key: str,
    parent_key: str,
    entry: "SchemaEntry",
) -> "SchemaEntry":
    # Check if regex context is present in current entry
    if "useRegex" not in entry.context:
        if is_debug():
            LOG.debug("SchemaEntry context = %s", dumps(entry.context, indent=4, default=vars))
        raise RuntimeError("Contextless !varname found.")
    # Add a !varname context which contains the name to use
    # and to which expression it corresponds to.
    entry.context.update({prop_key: prop_val, "regexp": parent_key})

    return entry


def _interpret_reference_rule(
    interpreter: "SchemaInterpreter",
    prop_val: dict,
    prop_key: str,
    parent_key: str,
    entry: "SchemaEntry",
) -> "SchemaEntry":
    # Check if reference is well formed against knowledge base
    if not any(prop_val.startswith(ss) for ss in _KNOWN_REFS):
        if is_debug():
            LOG.debug(
                "Reference item ('%s' , %s)",
                prop_key,
                dumps(prop_val, indent=4, default=vars),
            )
        raise ValueError("Malformed reference prop_value.")

    # Get schema definitions
    defs = interpreter.schema["$defs"]

    # Call _process_refs to check for correctness before creating parsing context.
    entry = _interpret_refs(defs, prop_val, entry)

    return entry


def _interpret_refs(definitions: dict, prop_val: str, entry: "SchemaEntry") -> "SchemaEntry":
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
        LOG.debug("Reference value '%s'", prop_val)
        raise ValueError("Malformed reference.")

    # Test for existence of Parser id
    pid = val_split[2]
    if pid not in definitions:
        LOG.debug("Given parser name '%s'", pid)
        raise KeyError("Parser not found.")

    # Add identified Parser to context
    LOG.debug("Processing reference to '%s'", pid)
    entry["!parser_id"] = pid

    return entry


def _interpret_calculate_directive_rule(
    interpreter: "SchemaInterpreter",
    prop_val: dict,
    prop_key: str,
    parent_key: str,
    entry: "SchemaEntry",
) -> "SchemaEntry":
    # Calculates simple math expressions using values from parsers.
    # Requires referenced parsers to return numerical values.
    # references can be supplemented with !parsing directives to properly select value.
    if not all(key in prop_val for key in ["expression", "variables"]):
        if is_debug():
            LOG.debug(
                "Directive item ('%s' , %s)",
                prop_key,
                dumps(prop_val, indent=4, default=vars),
            )
        raise ValueError("Malformed !calculate directive.")

    expression = prop_val["expression"]
    if not isinstance(expression, str):
        LOG.debug("Expression type '%s' , expected type '%s'", str(type(expression)), str(str))
        raise TypeError("Incorrect expression type in !calculate directive.")

    cleaned_expr = sub(r"\s", "", expression)
    correct, variable_names = math_check(cleaned_expr)
    if not correct:
        LOG.debug("Expression '%s'", cleaned_expr)
        raise ValueError("Incorrect expression value in !calculate directive.")

    variables = prop_val["variables"]
    if not isinstance(variables, dict):
        LOG.debug("Variables type '%s' , expected type '%s'", str(type(variables)), str(str))
        raise TypeError("Incorrect variables type in !calculate directive.")

    if len(variable_names) != len(variables):
        if is_debug():
            LOG.debug(
                "Expression '%s' , expression variables '%s' , defined variables = %s",
                expression,
                str(variable_names),
                dumps(variables, indent=4, default=vars),
            )
        raise RuntimeError("Variables count mismatch in !calculate directive.")

    # At this point we check if each variable entry corresponds to a reference to a Parser
    variable_entries = {}
    for variable in variables:
        if not variable in variable_names:
            LOG.debug("Variable name '%s'", variable)
            raise RuntimeError("Variable name mismatch in !calculate directive.")

        value = variables[variable]
        if not isinstance(value, dict):
            LOG.debug(
                "Variables type '%s' , expected type '%s'",
                str(type(variable)),
                str(dict),
            )
            raise TypeError("Incorrect variable type in !calculate directive.")

        if not "$ref" in value:
            if is_debug():
                LOG.debug("Variable content = %s", dumps(value, indent=4, default=vars))
            raise RuntimeError("Variable does not reference a Parser in !calculate directive.")

        # We create a SchemaEntry in the context to be specially handled by the Formatter
        new_entry = entry.inherit(
            key=prop_key,
            key_path=[],
            context={},
        )

        if "!parsing" in value:
            _interpret_parsing_directive_rule(interpreter, value["!parsing"], "!parsing", prop_key, new_entry)

        _interpret_reference_rule(interpreter, value["$ref"], "$ref", prop_key, new_entry)

        variable_entries[variable] = new_entry

    entry[prop_key] = {"expression": cleaned_expr, "variables": variable_entries}

    return entry


INTERPRETATION_RULES = {
    "properties": _interpret_simple_property_rule,
    "patternProperties": _interpret_pattern_property_rule,
    "!parsing": _interpret_parsing_directive_rule,
    "$ref": _interpret_reference_rule,
    "!varname": _interpret_varname_directive_rule,
    "!calculate": _interpret_calculate_directive_rule,
}


def register_interpretation_rule(interpretation_key: str, rule: Callable) -> None:
    """
    Function to register new rules in the INTERPRETATION_RULES dictionary.

    Arguments:
        interpretation_key: string keyword of schema to interpret.
        rule: callable rule to export to new format.
    """

    if interpretation_key in INTERPRETATION_RULES:
        raise KeyError("Export rule already exists")

    INTERPRETATION_RULES[interpretation_key] = rule
