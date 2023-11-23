#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""

Formatter class for handling Parsers.
Coordinates parsing of files using Explorer output and user defined Parsers.
If a user schema is provided, formats the metadata output according to the
defined schema.

Authors: Jose V., Matthias K.

"""

from pathlib import Path
from copy import deepcopy
from json import dump, load
from typing import Optional, List, NoReturn, Union

from .Logger import LOG
from .Parser import AParser
from . import FormatterHelpers as helpers
from .SchemaInterpreter import SchemaInterpreter, SchemaEntry
from .helper_functions import _update_dict_with_parts, _merge_dicts, _pattern_parts_match


DEFAULT_PARSER_SCHEMA = {
    "$schema": "https://abc",
    "$id": "https://abc.json",
    "description": "A plain schema for directory structures",
    "type": "object",
    "properties": {
        "name": {
            "type": "string"
        },
        "children": {
            "type": "array",
            "items": {
                "$ref": "#"
            }
        },
        "node": {
            "$ref": "#/$defs/node"
        }
    },
    "$defs": {
        "node": {
            "$id": "/schemas/address",
            "$schema": "http://abc",
            "type": "object",
            "properties": {
                "anyOf": []
            }
        }
    }
}


class Formatter():
    """Formatter
    A Formatter creates a metadata object (dict) that
    is further described by a json schema.
    The json schema describing the metadata object is build using
    the schema of the Formatter and the schema's provided by the Parsers.

    All metadata for a node is put at a corresponding node in the
    metadata dict tree. the directories in the metadata archive (lake)
    are used for structuring the tree.
    """

    def __init__(self,
                 schema: Optional[Union[dict, Path]] = None,
                 parsers: Optional[List[AParser]] = None,
                 lazy_load: Optional[bool] = False) -> None:

        # Protected
        # These attributes should only be modified through the add, update remove methods
        self._parsers = []
        self._input_file_patterns = [] # TODO: Check if this list can/may become a 1D - 2D hybrid list if an parser accepts multiple patterns
        # Can also be completely replaced through set method
        if schema is not None:
            self._use_schema = True
            if isinstance(schema, dict):
                self._schema = schema
            elif isinstance(schema, Path):
                if schema.suffix in ['.json']:
                    with schema.open() as f:
                        self._schema = load(f)
                else:
                    raise RuntimeError(
                        f'Incorrect format for schema: {schema.suffix}, expected JSON format'
                    )
            else:
                raise TypeError('schema must be dict or Path')
        else:
            self._use_schema = False
            self._schema = deepcopy(DEFAULT_PARSER_SCHEMA)

        # Used for internal handling:
        # Shouldn't use much memory but TODO: check additional memory usage

        # Used for updating/removing parsers
        # Indexing is done storing a triplet with parsers, patterns, schema indexes
        self._indexes = helpers.Indexes()

        # Set lazy loading
        self._lazy_load = lazy_load

        # For parser result caching
        self._cache = helpers.Cache()

        # Formatting rules
        from .FormattingRules import _FORMATTING_RULES
        self._rules = deepcopy(_FORMATTING_RULES)

        # Public
        self.metadata = {}

        self.combine = lambda parser2, schema=None: _combine(
            parser1=self, parser2=parser2, schema=schema)

        if parsers is not None:
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
        raise AttributeError(
            "parsers list should be modified through add, update and remove procedures"
        )

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
        raise AttributeError(
            "Input file patterns list should be modified through add, update and remove procedures"
        )

    @property
    def schema(self) -> dict:
        """Returns parser schema (dict)."""
        return self._schema

    @schema.setter
    def schema(self, schema: dict) -> None:
        """Sets parser schema (dict)."""
        self._schema = schema
        self._use_schema = True
        if len(self._parsers) > 0:
            for ex in self._parsers:
                # TODO: Needs consistency checks
                self._extend_json_schema(ex)

    @property
    def lazy_load(self) -> bool:
        """Returns lazy loading (bool) state."""
        return self._lazy_load

    @lazy_load.setter
    def lazy_load(self, lazy_load: bool) -> None:
        """Sets lazy load state (bool)."""
        if lazy_load == self._lazy_load:
            return
        if lazy_load and not self._lazy_load:
            if len(self.metadata) > 0:
                raise RuntimeError(
                    "Lazy loading needs to be enabled before metadata parsing"
                )
        else:
            if len(self.metadata) > 0:
                # TODO: Should we raise exception instead of warning?
                LOG.warning(
                    "Compiling available metadata after disabling lazy loading."
                    )
            self.compile_metadata()
        self._lazy_load = lazy_load

    def _extend_json_schema(self, parser: AParser) -> None:
        """
        Extends parser schema (dict) with a given parser schema (dict).
        Indexes schema.
        """
        if "$defs" not in self._schema:
            self._schema["$defs"] = {"node": {"properties": {"anyOf": []}}}
        elif not isinstance(self._schema["$defs"], dict):
            raise TypeError(
                f"Incorrect schema format, $defs property should be a dictionary, got {type(self._schema['$defs'])}")
        
        pid = parser.id
        p_ref = parser.ref
        self._schema["$defs"][pid] = parser.schema

        if 'node' not in self._schema["$defs"]:
            self._schema["$defs"].update({"node": {"properties": {"anyOf": []}}})

        self._indexes.set_index(pid, "scp",
                                len(self._schema["$defs"]["node"]["properties"]["anyOf"]))
        self._schema["$defs"]["node"]["properties"]["anyOf"].append(
            {"$ref": p_ref})

    def add_parser(self, parser: AParser) -> None:
        """
        Method to add parser to list.
        Indexes parsers list and input files patterns list.
        """
        if parser in self.parsers:
            raise RuntimeError("Parser is already in Formatter")
        pid = parser.id
        self._cache.add(pid)
        self._indexes.set_index(pid, "prs", len(self._parsers))
        self._parsers.append(parser)
        self._indexes.set_index(pid, "ifp", len(self._input_file_patterns))
        self._input_file_patterns.append(parser.input_file_pattern)
        self._extend_json_schema(parser)
        parser._parsers.append(self)

    def update_parser(self, parser: AParser) -> None:
        """
        Method to update a known parser.
        Updates are done in place.
        """
        if parser not in self._parsers:
            raise RuntimeError("Unknown Parser")
        pid = parser.id
        self._schema["$defs"][pid] = parser.schema
        ifp_index = self._indexes.get_index(pid, "ifp")
        self._input_file_patterns[ifp_index] = parser.input_file_pattern
        scp_index = self._indexes.get_index(pid, "scp")
        self._schema["$defs"]["node"]["properties"]["anyOf"][scp_index] = \
            {"$ref": parser.ref}

    def remove_parser(self, parser: AParser) -> None:
        """
        Removes parser from internal list.
        Reflects removal in schema and input files patterns list.
        """
        if parser not in self._parsers:
            raise RuntimeError("Unknown Parser")
        pid = parser.id
        indexes = self._indexes.get_index(pid)
        self._parsers.pop(indexes["prs"], None)
        self._input_file_patterns.pop(indexes["ifp"], None)
        self._schema["$defs"]["node"]["properties"]["anyOf"].pop(indexes["scp"], None)
        self._schema["$defs"].pop(pid, None)
        self._indexes.drop_indexes(pid)
        self._cache.drop(pid)
        parser._parsers.remove(self)

    def get_parser(self, parser_name: str) -> AParser:
        """
        helper method returns Parser given its name
        """
        for ex in self.parsers:
            if ex.name == parser_name:
                return ex
        LOG.warning(f"No Parser with name: {parser_name} exist")

    # TODO: Check whether we want to keep this or not:
    # def _update_metadata_tree(self, decompress_path: Path,
    #                           file_path: Path) -> Path:
    #     """
    #     Update tree structure of metadata dict with file path.

    #     :param file_path: path to a file
    #     """
    #     iter_dict = self.metadata
    #     rel_file_path = file_path.relative_to(decompress_path)
    #     for pp in rel_file_path.parts[:-1]:
    #         if pp not in iter_dict:
    #             iter_dict[pp] = {}
    #             iter_dict = iter_dict[pp]
    #         elif pp in iter_dict and not isinstance(iter_dict[pp], dict):
    #             raise RuntimeError(
    #                 f'Trying to created nested structure in metadata object failed: {pp}'
    #             )
    #     return rel_file_path

    # def _deep_set(self, metadata: dict, value, path: Path) -> None:
    #     if len(path.parts) == 1:
    #         metadata[path.parts[0]] = value
    #     else:
    #         self._deep_set(metadata[path.parts[0]], value,
    #                        path.relative_to(path.parts[0]))

    # def parse_file(self, file_path: Path) -> None:
    #     """
    #     Add metadata from input file to metadata object,
    #     usually by sending calling all extract's linked to the file-name or regexp of file name.

    #     :param file_path: path to file (Path)
    #     """

    #     # TODO: Should lazy loading also be implemented here?

    #     rel_file_path = self._update_metadata_tree(file_path)

    #     for extractor in self._extractors:
    #         pattern = extractor.input_file_pattern
    #         if pattern[0] == '*':
    #             pattern = '.' + pattern
    #         if fullmatch(pattern, file_path.name):
    #             metadata = extractor.extract_metadata_from_file(file_path)
    #             # TODO: The metadata tree should be compiled/merged with the Parser schema
    #             # We should think if this is to be done instead of the path tree structure
    #             # or do it afterwards through another mechanism
    #             #   ->  Think about reshaping/filtering function for dictionaries using schemas
    #             #       add bool condition to switch between directory hierarchy for metadata objects
    #             #            or schema hierarchy
    #             #       add linking between extracted metadata object properties through schema keywords
    #             #           -> cf mattermost chat
    #             self._deep_set(self.metadata, metadata, rel_file_path)

    def parse_files(self, decompress_path: Path,
                    file_paths: List[Path],
                    override_meta_files: bool = True) -> List[Path]:
        """
        Add metadata from input files to metadata object,
        usually by sending calling all parsers linked to the file-name or regexp of files names.

        :param file_paths: list of file paths (Path)
        """
        to_parse = {}
        meta_files = []
        # TODO: Think about parallelization scheme with ProcessPoolExecutor
        # Would it be worth it in terms of performance?
        for parser in self._parsers:
            pid = parser.id
            to_parse[pid] = []
            LOG.debug(f'    preparing parser: {pid}')
            for fp in file_paths:
                pattern = parser.input_file_pattern.split("/")
                pattern.reverse()
                if _pattern_parts_match(pattern, list(reversed(fp.parts))):
                    to_parse[pid].append(fp)

        # TODO: Think about parallelization scheme with ProcessPoolExecutor
        # For instance this loop is trivially parallelizable if there is no file usage overlap
        for pid in to_parse:
            for file_path in to_parse[pid]:
                # Get parser and parse metadata
                pix = self._indexes.get_index(pid, "prs")
                parser = self._parsers[pix]
                metadata = parser.parse_file(file_path)

                if not self._lazy_load:
                    # self._update_metadata_tree_with_path_hierarchy(metadata, decompress_path, file_path)
                    self._cache[pid].add(
                        decompress_path,
                        file_path,
                        metadata
                    )
                else:
                    entry = self._cache[pid].add(
                        decompress_path,
                        file_path
                    )
                    if entry.meta_path.exists():
                        if override_meta_files:
                            LOG.warning(f"Metadata file {entry.meta_path} exists, overriding.")
                        else:
                            raise FileExistsError(
                                f"Unable to save parsed metadata: {entry.meta_path} exists")
                    with entry.meta_path.open("w") as mp:
                        dump(metadata, mp, indent=4)
                    meta_files.append(entry.meta_path)

        return meta_files

   # def _update_metadata_tree_with_schema(self, hierarchy, **kwargs) -> None:
   #     """add metadata from a Hierachy object to the metadata dict
   #     currently the metadata is only taken from a !extractor object located at the last
   #     entry in the list provided by the hierachy class. this can be extended in the future

   #     :param hierarchy: a Hierachy object
   #     :returns: None

   #     """

   #     # If there is an extractor passed by the Hierachy (i.e. at the last entry in the list)
   #     if hierarchy.extractor_name is not None:
   #         LOG.debug(
   #             f'        working on extractor: {hierarchy.extractor_name}')
   #         LOG.debug(
   #             f'        with path: {hierarchy._hierachy[-1].path} and re`s: {hierarchy.regexps} '
   #         )

   #         extractor = self.get_extractor(
   #             hierarchy.extractor_name
   #         )  # TODO: reconcider: we should use id here
   #         for meta_set in self._cache[extractor.id]:
   #             LOG.debug(
   #                 f'            checking available metadata: {meta_set.rel_path}'
   #             )
   #             # check which metadata sets read by the extractor match the path in the metadata tree
   #             if hierarchy.match_path(meta_set.rel_path):
   #                 # LOG.debug(
   #                 #     f'            found metadata: {meta_set.metadata}')
   #                 # build dict-structure following the structure passed by the hierachy
   #                 relative_root = self.metadata
   #                 for node in hierarchy._hierachy[:-1]:
   #                     if node.add_to_metadata:
   #                         if node.name not in relative_root.keys():
   #                             relative_root[node.name] = {}
   #                             if node.description is not None:
   #                                 relative_root[node.name][
   #                                     'description'] = node.description
   #                         relative_root = relative_root[node.name]
   #                 # relative_root.update(
   #                 #     extractor.filter_metadata(
   #                 #         meta_set.metadata,
   #                 #         hierarchy.extractor_directive.keys, **kwargs))
   #                 filtered_metadata = extractor.filter_metadata(
   #                     meta_set.metadata, hierarchy.extractor_directive.keys,
   #                     **kwargs)
   #                 relative_root[
   #                     meta_set.rel_path.as_posix()] = filtered_metadata
   #     else:
   #         raise NotImplementedError(
   #             'currently only metadata from extractors can be added to the schema'
   #         )

   # def _schema_iterator(self,
   #                      properties: Optional[dict] = None,
   #                      hierachy=None,
   #                      level=0,
   #                      prop_type: Optional[str] = None,
   #                      parent_prop_name: Optional[str] = None):
   #     """
   #     schema iterator, returns nodes in schema.
   #     """
   #     # index_dirdirective = None
   #     if self.schema is None:
   #         raise RuntimeError(
   #             f'A schema must be specified before starting the _schema_iterator'
   #         )
   #     # --- initialize variables if none are given
   #     if properties is None:
   #         if 'properties' not in self.schema.keys() or not isinstance(
   #                 self.schema['properties'], dict):
   #             raise RuntimeError(
   #                 f'The root schema is expected to contain a dict properites: {self.schema}'
   #             )
   #         properties = self.schema['properties']
   #         prop_name = 'properties'
   #     if hierachy is None:
   #         hierachy = helpers.Hierachy()
   #     for prop_name, prop in properties.items():
   #         # --- check for archivist directives
   #         if prop_name in [
   #                 'properties', 'unevaluatedProperties',
   #                 'additionalProperties', 'patternProperties'
   #         ]:
   #             prop_type = prop_name
   #             yield from self._schema_iterator(prop, hierachy, level,
   #                                              prop_type, prop_name)
   #         elif prop_name == '!varname':
   #             level = hierachy.add(helpers.DirectoryDirective(
   #                 varname=properties['!varname'], regexp=parent_prop_name),
   #                                  level=level)
   #         elif prop_name == '!extractor':
   #             level = hierachy.add(helpers.ExtractorDirective(**prop), level=level)
   #             yield prop, hierachy
   #         elif prop_name == '$ref':
   #             if prop[:8] == '#/$defs/':
   #                 # search defs for corresponding schema and apply it
   #                 for defs in self.schema['$defs']:
   #                     defstring = f'#/$defs/{defs}'.strip()
   #                     if defstring == prop[:len(defstring)]:
   #                         subschem = self.schema['$defs'][defs.split('/')
   #                                                         [-1]]
   #                         yield from self._schema_iterator(
   #                             subschem, hierachy, level, prop_type,
   #                             prop_name)
   #                         break
   #             elif prop[:13] == '#/properties/':
   #                 # for referencing other properties, basically links
   #                 nodes = prop.split('/')
   #                 if not nodes:
   #                     raise RuntimeError(f'unknown ref: {prop}')
   #             else:
   #                 raise NotImplementedError(
   #                     f'unkown reference, please open an issue: {prop}')
   #         elif isinstance(prop, dict) and prop_name != '!extractor':
   #             yield from self._schema_iterator(prop, hierachy, level,
   #                                              prop_type, prop_name)

    def _update_metadata_tree_with_schema2(self,
                                           interpreted_schema: SchemaEntry,
                                           branch: Optional[list] = None,
                                           **kwargs) -> dict:
        """
        Recursively generate metadata file using interpreted_schema obtained with SchemaInterpreter.
        Designed to mimic structure of interpreted_schema where each SchemaEntry is a branching node in the metadata
        and whenever an parsing context is found the branch terminates.
        Handles additional context like parsing directives (!parsing) and directory directives (!varname).

        While recursing over the tree branches, the branch path i.e. all the parent nodes are tracked in order
        to use patternProperties without path directives.
        """
        tree = {}
        context = interpreted_schema.context
        if branch is None:
            branch = []

        # For all the entries in the interpreted schema
        for key, value in interpreted_schema.items():

            # Only process SchemaEntries
            if isinstance(value, SchemaEntry):

                branch.append(key)

                # Update position in branch

                # If current context contains regex information (children always inherit context)
                # We merge all recursion results from children and return the resulting merge
                if "useRegex" in context:
                    tree = _merge_dicts(tree, self._update_metadata_tree_with_schema2(value, branch))

                # If current context does not contain regex information but child context does,
                # we need to integrate the recursion result into the metadata tree.
                # However the recursion result will contain all the nodes in the branch up to
                # the root of the tree i.e. if we are not currently at the root there will be
                # a merging conflict. For this we loop over the tree nodes stored in the branch
                # until we reach the current node and at that point we integrate into the tree.
                elif "useRegex" in value.context:
                    recursion_result = self._update_metadata_tree_with_schema2(value, branch)
                    # For each tree node in the current branch
                    for node in branch:

                        # Check the length of the recursion result and and existence of node
                        if len(recursion_result) > 1 or node not in recursion_result:
                            LOG.debug(f"current metadata tree: {tree}\n\nrecursion results: {recursion_result}")
                            raise RuntimeError("Malformed recursion result when processing regex context")
                        
                        # If the current node is equal to the key in the interpreted schema i.e. last iteration of loop
                        if key == node:
                            # Add recursion result to tree
                            tree[key] = recursion_result[key]
                            # With break loop won't exit into else clause
                            break

                        # Otherwise we move in depth with the next node of the recursion result
                        else:
                            recursion_result = recursion_result[node]
                    
                    # If the break is never reached an error has ocurred
                    else:
                        LOG.debug(f"current metadata tree: {tree}\n\nrecursion results: {recursion_result}")
                        raise RuntimeError("Malformed metadata tree when processing regex context")

                # Else we add a new entry to the tree using the recursion results
                else:
                    tree[key] = self._update_metadata_tree_with_schema2(value, branch)

                branch.pop()

            # If entry corresponds to an parser reference
            elif key in self._rules:
                tree = self._rules[key](self, interpreted_schema, branch, value, **kwargs)
            # Nodes should not be of a different type than SchemaEntry
            else:
                raise RuntimeError(f"Unexpected value in interpreted schema: {key}: {type(value)}")

        return tree

    def compile_metadata(self, **kwargs) -> dict:
        """
        Method to build full metadata tree from cached metadata.
        """
        if self._cache.is_empty():
            raise RuntimeError(
                "Metadata needs to be parsed before updating the tree."
                )
        if self._use_schema:
            # if self.lazy_load:
                # raise NotImplementedError()
            # LOG.debug("    using schema")
            # iterator = self._schema_iterator()
            # while True:
                # try:
                    # _, hierarchy = next(iterator)
                    # self._update_metadata_tree_with_schema(hierarchy, **kwargs)
                # except StopIteration:
                    # break
            interpreter = SchemaInterpreter(self.schema)
            interpreted_schema = interpreter.generate()
            self.metadata = self._update_metadata_tree_with_schema2(interpreted_schema, **kwargs)

        else:
            for parser_cache in self._cache:
                for cache_entry in parser_cache:
                    cache_entry.load_metadata()
                    _update_dict_with_parts(
                        self.metadata,
                        cache_entry.metadata,
                        list(cache_entry.rel_path.parts))

        return self.metadata


def _combine(parser1: Formatter,
             parser2: Formatter,
             schema: Optional[dict] = None) -> Formatter:
    """
    Function used to combine two different parsers.
    Combination is never done in-place.
    Needs an englobing schema that will take into account the combination of parsers.
    """
    ll = False
    if parser1.lazy_load != parser2.lazy_load:
        LOG.warning(
            f"Lazy load configuration mismatch. Setting to default: {ll}")
    else:
        ll = parser1.lazy_load
    combined_parser = Formatter(schema=schema,
                             parsers=parser1.parsers +
                             parser2.parsers,
                             lazy_load=ll)

    if len(parser1.metadata) > 0 or len(parser2.metadata) > 0:
        #combined_parser.metadata = _merge_dicts(parser1.metadata, parser2.metadata)
        raise NotImplementedError("Combining Parsers with existing metadata is not yet implemented.")

    return combined_parser


Formatter.combine = _combine
