#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""

Formatter class for handling Parsers.
Coordinates parsing of files using Explorer output and user defined Parsers.
If a user schema is provided, formats the metadata output according to the
defined schema using a SchemaInterpreter.

exports:
    Formatter class

Authors: Jose V., Matthias K.

"""

from pathlib import Path
from copy import deepcopy
from json import load, dumps
from hashlib import sha3_256
from pickle import dumps as p_dumps, HIGHEST_PROTOCOL
from typing import Optional, List, Iterable, NoReturn, Union, Tuple

from metadata_archivist.parser import AParser
from metadata_archivist.logger import LOG, is_debug
from metadata_archivist import helper_classes as helpers
from metadata_archivist.formatting_rules import (
    FORMATTING_RULES,
    register_formatting_rule,
)
from metadata_archivist.helper_functions import (
    update_dict_with_parts,
    merge_dicts,
    pattern_parts_match,
    remove_directives_from_schema,
)


class Formatter:
    """
    A Formatter creates a metadata object (dict) that
    is further described by a json schema.
    The json schema describing the metadata object is build using
    the schema of the Formatter and the schema's provided by the Parsers.

    All metadata for a node is put at a corresponding node in the
    metadata dict tree. the directories in the metadata archive (lake)
    are used for structuring the tree.

    Attributes:
        parsers: list of parsers added to Formatter by corresponding method or at construction time.
        input_file_patterns: list of input file patterns derived from parsers registered to Formatter.
        schema: dictionary containing structure template to format parsing results.
        lazy_load: control boolean to enable storing of parsing results as files.
        config: dictionary containing formatter configuration.

    Methods:
        add_parser: method to add Parser to list, updates internal schema file.
        update_parser: method to update Parser in list, updates internal schema file.
        remove_parser: method to remove Parser from list, updates internal schema file.
        get_parser: method to retrieve Parser from list, uses Parser name for matching.
        parse_files: method to trigger parsing procedures on a given list of input files.
        compile_metadata: method to trigger structuring of parsing results.
        combine: method to merge Formatter instances by combining parsers list. WIP
    """

    def __init__(
        self,
        parsers: Optional[Union[AParser, Iterable[AParser]]] = None,
        schema: Optional[Union[dict, str]] = None,
        config: Optional[dict] = None,
    ) -> None:
        """
        Constructor of Formatter class.

        Arguments:
            parsers: Optional, Parser or iterable sequence of parsers added to Formatter.
            schema: Optional, dictionary containing structure template to format parsing results.
            config: Optional, dictionary containing formatter configuration.
        """

        # Wrapped attributes:
        # These attributes should only be modified through the add, update remove methods
        self._parsers = []
        self._input_file_patterns = []
        # Can also be completely replaced through set method
        if schema is not None:
            if isinstance(schema, dict):
                self._schema = schema
            elif isinstance(schema, (str, Path)):
                schema_path = Path(schema)
                with schema_path.open("r", encoding="utf-8") as f:
                    self._schema = load(f)
            else:
                raise TypeError("Schema must be dict or Path.")
        else:
            self._schema = None

        # Internal attributes:

        # Schema usage enabled
        self._use_schema = bool(self._schema is not None)

        # Attribute for SchemaInterpreter
        self._interpreter = None

        # Used for updating/removing parsers
        # Indexing is done storing a triplet with parsers, patterns, schema indexes
        self._indexes = helpers.ParserIndexes()

        # For parser result caching
        self._cache = helpers.FormatterCache()

        # Public
        self.config = config
        self.metadata = {}

        self.combine = lambda formatter2, schema=None: _combine(formatter1=self, formatter2=formatter2, schema=schema)

        if parsers is not None:
            if isinstance(parsers, AParser):
                self.add_parser(parsers)
            else:
                for e in parsers:
                    self.add_parser(e)

    @property
    def parsers(self) -> List[AParser]:
        """Returns list of added parsers (list)."""
        return self._parsers

    @parsers.setter
    def parsers(self, _) -> NoReturn:
        """
        Forbidden setter for parsers attribute.
        (pythonic indirection for protected attributes)
        """
        raise AttributeError("parsers list should be modified through add, update and remove procedures")

    @property
    def input_file_patterns(self) -> List[str]:
        """
        Returns list of re.pattern (str) for input files, given by the parsers.
        The re.patterns are then used by the explorer to select files.
        """
        return self._input_file_patterns

    @input_file_patterns.setter
    def input_file_patterns(self, _) -> NoReturn:
        """
        Forbidden setter for input_file_patterns attribute.
        (pythonic indirection for protected attributes)
        """
        raise AttributeError("Input file patterns list should be modified through add, update and remove procedures")

    @property
    def schema(self) -> dict:
        """Returns parser schema (dict)."""
        return self._schema

    @schema.setter
    def schema(self, schema: dict) -> None:
        """
        Sets a schema (dict) for structuring.
        Triggers automatic extension of given schema by self contained parsers.
        Enables usage of schema to structure parsing results.

        Arguments:
            schema: dictionary containing structure template to format parsing results.
        """

        self._schema = schema
        self._use_schema = True
        if len(self._parsers) > 0:
            for ex in self._parsers:
                self._extend_json_schema(ex)

    def export_schema(self) -> dict:
        """
        Removes interpretation directives from schema, such that result respects JSONSchema standard.

        Returns:
            cleaned schema dictionary.
        """

        if not self._use_schema:
            return None

        return remove_directives_from_schema(self._schema)

    def set_lazy_load(self, lazy_load: bool) -> None:
        """
        Sets lazy load of parsing results.

        Arguments:
            lazy_load: control boolean to enable storing of parsing results as files.
        """

        if lazy_load == self.config["lazy_load"]:
            return
        if lazy_load and not self.config["lazy_load"]:
            if len(self.metadata) > 0:
                raise RuntimeError("Lazy loading needs to be enabled before metadata parsing")
        else:
            if len(self.metadata) > 0:
                LOG.warning("Compiling available metadata after disabling lazy loading.")
            self.compile_metadata()
        self.config["lazy_load"] = lazy_load

    def _extend_json_schema(self, parser: AParser) -> None:
        """
        Extends self contained schema with schema from input Parser.
        Uses ParserIndexes class for easier indexing.

        Arguments:
            parser: AParser instance containing schema description of parsing output.
        """

        if not self._use_schema:
            return

        if "$defs" not in self._schema:
            self._schema["$defs"] = {"node": {"properties": {"anyOf": []}}}
        elif not isinstance(self._schema["$defs"], dict):
            LOG.debug(
                "$def property type '%s' , expected type '%s'",
                str(type(self._schema["$defs"])),
                str(dict),
            )
            raise TypeError("Incorrect schema format, $defs property should be a dictionary.")

        pid = parser.name
        p_ref = parser.get_reference()
        self._schema["$defs"][pid] = parser.schema

        if "node" not in self._schema["$defs"]:
            self._schema["$defs"].update({"node": {"properties": {"anyOf": []}}})

        self._indexes.set_index(pid, "scp", len(self._schema["$defs"]["node"]["properties"]["anyOf"]))
        self._schema["$defs"]["node"]["properties"]["anyOf"].append({"$ref": p_ref})

    def add_parser(self, parser: AParser) -> None:
        """
        Method to add Parser to self contained list.
        Reflects addition in schema and input files patterns list.
        Uses ParserIndexes class for easier indexing.

        Arguments:
            parser: AParser instance.
        """

        if parser in self.parsers:
            raise RuntimeError("Parser is already in Formatter.")

        pid = parser.name
        self._cache.add(pid)
        self._indexes.set_index(pid, "prs", len(self._parsers))
        self._parsers.append(parser)
        self._indexes.set_index(pid, "ifp", len(self._input_file_patterns))
        self._input_file_patterns.append(parser.input_file_pattern)

        if self._use_schema:
            self._extend_json_schema(parser)

        parser.register_formatter(self)

    def update_parser(self, parser: AParser) -> None:
        """
        Method to update a known parser.
        Reflects update in schema and input files patterns list.
        Uses ParserIndexes class for easier indexing.

        Arguments:
            parser: AParser instance.
        """

        if parser not in self._parsers:
            raise RuntimeError("Unknown Parser.")

        pid = parser.name
        self._schema["$defs"][pid] = parser.schema
        ifp_index = self._indexes.get_index(pid, "ifp")
        self._input_file_patterns[ifp_index] = parser.input_file_pattern

        if self._use_schema:
            scp_index = self._indexes.get_index(pid, "scp")
            self._schema["$defs"]["node"]["properties"]["anyOf"][scp_index] = {"$ref": parser.get_reference()}

    def remove_parser(self, parser: AParser) -> None:
        """
        Removes parser from self contained list.
        Reflects removal in schema and input files patterns list.
        Uses ParserIndexes class for easier indexing.

        Arguments:
            parser: AParser instance.
        """
        if parser not in self._parsers:
            raise RuntimeError("Unknown Parser.")

        pid = parser.name
        indexes = self._indexes.drop_indexes(pid)
        self._parsers.pop(indexes["prs"], None)
        self._input_file_patterns.pop(indexes["ifp"], None)

        if self._use_schema:
            self._schema["$defs"]["node"]["properties"]["anyOf"].pop(indexes["scp"], None)
            self._schema["$defs"].pop(pid, None)

        self._cache.drop(pid)
        parser.remove_formatter(self)

    def get_parser(self, parser_name: str) -> Tuple[AParser, helpers.ParserCache]:
        """
        Retrieves parser from self contained list.

        Arguments:
            parser: AParser instance.

        Returns:
            Tuple of:
                Parser instance and corresponding internal ParserCache.
        """

        for ex in self.parsers:
            if ex.name == parser_name:
                return ex, self._cache[parser_name]
        LOG.warning("No Parser with name '%s' exist", parser_name)
        return None, None

    def parse_files(
        self,
        explored_path: Path,
        file_paths: List[Path],
    ) -> List[Path]:
        """
        Method to orchestrate parsing of list of given input files by self contained parsers.
        Input files are sorted by input file patterns.
        If lazy loading is enabled, parsing results are stored in cache files and release from memory.

        Arguments:
            explored_path: Path object pointing to root exploration target.
            file_paths: List of Path objects pointing to target files for parsing.

        Returns:
            list of lazy load cache file Paths (empty if lazy load disabled).
        """

        LOG.info("Parsing files ...")

        to_parse = {}
        meta_files = []
        for parser in self._parsers:
            pid = parser.name
            to_parse[pid] = []
            LOG.debug("    preparing parser '%s'", pid)
            for fp in file_paths:
                pattern = parser.input_file_pattern.split("/")
                pattern.reverse()
                if pattern_parts_match(pattern, list(reversed(fp.parts))):
                    to_parse[pid].append(fp)

        for pid, sorted_paths in to_parse.items():
            for file_path in sorted_paths:
                LOG.debug("    parsing file '%s'", str(file_path))
                # Get parser and parse metadata
                pix = self._indexes.get_index(pid, "prs")
                parser = self._parsers[pix]
                metadata = parser.run_parser(file_path)

                if not self.config["lazy_load"]:
                    self._cache[pid].add(explored_path, file_path, metadata)
                else:
                    entry = self._cache[pid].add(explored_path, file_path)
                    entry.save_metadata(
                        metadata,
                        overwrite=self.config.get("overwrite", True),
                    )
                    meta_files.append(entry.meta_path)

        LOG.info("Done!")

        return meta_files

    def _update_metadata_tree_with_schema(
        self, interpreted_schema: helpers.SchemaEntry, branch: Optional[list] = None
    ) -> dict:
        """
        Recursively generate metadata file using interpreted_schema obtained with SchemaInterpreter.
        Designed to mimic structure of interpreted_schema where each SchemaEntry is a branching node in the metadata
        and whenever an parsing context is found the branch terminates.
        Handles additional context like parsing directives (!parsing) and directory directives (!varname).

        While recursing over the tree branches, the branch path i.e. all the parent nodes are tracked in order
        to use patternProperties without path directives.

        Arguments:
            interpreted_schema: dictionary containing interpreted schema obtained from SchemaInterpreter.
            branch: Optional, list containing current recursion branch key.

        Returns:
            structured metadata obtained from parsing results
        """

        tree = {}
        context = interpreted_schema.context
        if branch is None:
            branch = []

        # For all the entries in the interpreted schema
        for key, value in interpreted_schema.items():

            # Only process SchemaEntries
            if isinstance(value, helpers.SchemaEntry):

                branch.append(key)

                # Update position in branch

                # If current context contains regex information (children always inherit context)
                # We merge all recursion results from children and return the resulting merge
                if "useRegex" in context:
                    tree = merge_dicts(tree, self._update_metadata_tree_with_schema(value, branch))

                # If current context does not contain regex information but child context does,
                # we need to integrate the recursion result into the metadata tree.
                # However the recursion result will contain all the nodes in the branch up to
                # the root of the tree i.e. if we are not currently at the root there will be
                # a merging conflict. For this we loop over the tree nodes stored in the branch
                # until we reach the current node and at that point we integrate into the tree.
                elif "useRegex" in value.context:
                    recursion_result = self._update_metadata_tree_with_schema(value, branch)
                    # For each tree node in the current branch
                    for node in branch:

                        # Check the length of the recursion result and and existence of node
                        if len(recursion_result) > 1 or node not in recursion_result:
                            if is_debug():
                                LOG.debug(
                                    "current metadata tree = %s\nrecursion results = %s",
                                    dumps(tree, indent=4, default=vars),
                                    dumps(recursion_result, indent=4, default=vars),
                                )
                            raise RuntimeError("Malformed recursion result when processing regex context")

                        # If the current node is equal to the key in the interpreted schema i.e. last iteration of loop
                        if key == node:
                            # Add recursion result to tree
                            tree[key] = recursion_result[key]
                            # With break loop won't exit into else clause
                            break

                        # Otherwise we move in depth with the next node of the recursion result
                        recursion_result = recursion_result[node]

                    # If the break is never reached an error has ocurred
                    else:
                        if is_debug():
                            LOG.debug(
                                "current metadata tree = %s\nrecursion results = %s",
                                dumps(tree, indent=4, default=vars),
                                dumps(recursion_result, indent=4, default=vars),
                            )
                        raise RuntimeError("Malformed metadata tree when processing regex context")

                # Else we add a new entry to the tree using the recursion results
                else:
                    tree[key] = self._update_metadata_tree_with_schema(value, branch)

                branch.pop()

            # If entry corresponds to an parser reference
            elif key in FORMATTING_RULES:
                tree = FORMATTING_RULES[key](self, interpreted_schema, branch, value, **deepcopy(self.config))
            # Nodes should not be of a different type than SchemaEntry
            else:
                LOG.debug(
                    "entry key '%s' , value type '%s' , expected type '%s'",
                    key,
                    str(type(value)),
                    str(helpers.SchemaEntry),
                )
                raise TypeError("Unexpected value in interpreted schema.")

        return tree

    def compile_metadata(self) -> dict:
        """
        Method to build full metadata tree from cached metadata.

        Returns:
            unified metadata dictionary, with default structure or custom schema structure.
        """

        LOG.info("Compiling metadata ...")

        if self._cache.is_empty():
            raise RuntimeError("Metadata needs to be parsed before compiling.")

        if self._use_schema:
            LOG.debug("    using schema structure ...")
            self._interpreter = helpers.SchemaInterpreter(self.schema)
            self.metadata = self._update_metadata_tree_with_schema(self._interpreter.generate())

        else:
            LOG.debug("    using file path structure ...")
            for parser_cache in self._cache:
                for cache_entry in parser_cache:
                    update_dict_with_parts(
                        self.metadata,
                        cache_entry.load_metadata(),
                        list(cache_entry.rel_path.parts),
                    )
        LOG.info("Done!")

        return self.metadata


# Class level method to register formatting rules
Formatter.register_formatting_rule = register_formatting_rule

# Indirection to class level method to register interpretation rules
Formatter.register_interpretation_rule = helpers.SchemaInterpreter.register_rule


def _combine(
    formatter1: Formatter,
    formatter2: Formatter,
    schema: Optional[dict] = None,
    config: Optional[dict] = None,
) -> Formatter:
    """
    Function used to combine two different formatters.
    Combination is never done in-place.
    Needs an englobing schema that will take into account the combination of formatters.
    New configuration dictionary can be provided to overwrite existing configurations.
    If no configuration is provided then both Formatter's configuration must be equal.

    Arguments:
        formatter1: instance of Formatter.
        formatter2: instance of Formatter.
        schema: Optional, dictionary schema containing structure used for combined formatter.
        config: Optional, dictionary containing formatter configuration.

    Returns:
        combined Formatter instance.
    """

    if config is None:
        # Test reference
        if formatter1.config != formatter2.config:
            for key, value in formatter1.config:
                if key not in formatter2.config:
                    if is_debug():
                        LOG.debug(
                            "formatter1.config = %s\nformatter2.config = %s",
                            dumps(formatter1.config, indent=4, default=vars),
                            dumps(formatter2.config, indent=4, default=vars),
                        )
                    raise KeyError("key mismatch in Formatter.combine.")
                if value != formatter2.config[key]:
                    if is_debug():
                        LOG.debug(
                            "formatter1.config = %s\nformatter2.config = %s",
                            dumps(formatter1.config, indent=4, default=vars),
                            dumps(formatter2.config, indent=4, default=vars),
                        )
                    raise ValueError("Value mismatch in Formatter.combine.")

            # If different reference but same content then copy content to new config
            config = deepcopy(formatter1.config)

        else:
            # If same reference then keep reference
            config = formatter1.config

    combined_formatter = Formatter(schema=schema, parsers=formatter1.parsers + formatter2.parsers, config=config)

    if len(formatter1.metadata) > 0 or len(formatter2.metadata) > 0:
        # combined_parser.metadata = _merge_dicts(parser1.metadata, parser2.metadata)
        raise NotImplementedError("Combining Parsers with existing metadata is not yet implemented.")

    return combined_formatter


# Class level method to combine two instances
Formatter.combine = _combine
