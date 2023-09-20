#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""

Extractor class to get metadata from file.
Parser class for handling Extractors.
To be specialized by custom parsers made by users.

Authors: Jose V., Matthias K.

"""

from pathlib import Path
from copy import deepcopy
from re import match, fullmatch
from json import dump, load, dumps
from typing import Optional, List, NoReturn, Union

from .Logger import LOG
from .Extractor import AExtractor
from . import ParserHelpers as helpers
from .SchemaInterpreter import SchemaInterpreter, SchemaEntry
from .helper_functions import _update_dict_with_path_hierarchy, _merge_dicts


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


class Parser():
    """Parser
    A Parser creates a metadata object (dict) that
    is further described by a json schema.
    The json schema describing the metadata object is build using
    the schema of the Parser and the schema's provided by the extractors.

    All metadata for a node is put at a corresponding node in the
    metadata dict tree. the directories in the metadata archive (lake)
    are used for structuring the tree.
    """

    def __init__(self,
                 schema: Optional[Union[dict, Path]] = None,
                 extractors: Optional[List[AExtractor]] = None,
                 lazy_load: Optional[bool] = False) -> None:

        # Protected
        # These attributes should only be modified through the add, update remove methods
        self._extractors = []
        self._input_file_patterns = [] # TODO: Check if this list can/may become a 1D - 2D hybrid list if an extractor accepts multiple patterns
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

        # Used for updating/removing extractors
        # Indexing is done storing a triplet with extractors, patterns, schema indexes
        self._indexes = helpers.Indexes()

        # Set lazy loading
        self._lazy_load = lazy_load

        # For extractor result caching
        self._cache = helpers.Cache()

        # Public
        self.metadata = {}

        self.combine = lambda parser2, schema=None: _combine(
            parser1=self, parser2=parser2, schema=schema)

        if extractors is not None:
            for e in extractors:
                self.add_extractor(e)

    @property
    def extractors(self) -> List[AExtractor]:
        """Returns list of added extractors (list)."""
        return self._extractors

    @extractors.setter
    def extractors(self, _) -> NoReturn:
        """
        Forbidden setter for extractors attribute.
        (pythonic indirection for protected attributes)
        """
        raise AttributeError(
            "Extractors list should be modified through add, update and remove procedures"
        )

    @property
    def input_file_patterns(self) -> List[str]:
        """
        Returns list of re.pattern (str) for input files, given by the extractors.
        The re.patterns are then used by the decompressor to select files.
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
        if len(self._extractors) > 0:
            for ex in self._extractors:
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
                    "Lazy loading needs to be enabled before metadata extraction"
                )
        else:
            if len(self.metadata) > 0:
                # TODO: Should we raise exception instead of warning?
                LOG.warning(
                    "Compiling available metadata after disabling lazy loading."
                    )
            self.compile_metadata()
        self._lazy_load = lazy_load

    def _extend_json_schema(self, extractor: AExtractor) -> None:
        """
        Extends parser schema (dict) with a given extractor schema (dict).
        Indexes schema.
        """
        if "$defs" not in self._schema:
            self._schema["$defs"] = {"node": {"properties": {"anyOf": []}}}
        elif not isinstance(self._schema["$defs"], dict):
            raise TypeError(
                f"Incorrect schema format, $defs property should be a dictionary, got {type(self._schema['$defs'])}")
        
        ex_id = extractor.id
        ex_ref = extractor.ref
        self._schema["$defs"][ex_id] = extractor.schema

        if 'node' not in self._schema["$defs"]:
            self._schema["$defs"].update({"node": {"properties": {"anyOf": []}}})

        self._indexes.set_index(ex_id, "sp",
                                len(self._schema["$defs"]["node"]["properties"]["anyOf"]))
        self._schema["$defs"]["node"]["properties"]["anyOf"].append(
            {"$ref": ex_ref})

    def add_extractor(self, extractor: AExtractor) -> None:
        """
        Method to add extractor to list.
        Indexes extractors list and input files patterns list.
        """
        if extractor in self.extractors:
            raise RuntimeError("Extractor is already in Parser")
        ex_id = extractor.id
        self._cache.add(ex_id)
        self._indexes.set_index(ex_id, "ex", len(self._extractors))
        self._extractors.append(extractor)
        self._indexes.set_index(ex_id, "ifp", len(self._input_file_patterns))
        self._input_file_patterns.append(extractor.input_file_pattern)
        self._extend_json_schema(extractor)
        extractor._parsers.append(self)

    def update_extractor(self, extractor: AExtractor) -> None:
        """
        Method to update a known extractor.
        Updates are done in place.
        """
        if extractor not in self._extractors:
            raise RuntimeError("Unknown Extractor")
        ex_id = extractor.id
        self._schema["$defs"][ex_id] = extractor.schema
        ifp_index = self._indexes.get_index(ex_id, "ifp")
        self._input_file_patterns[ifp_index] = extractor.input_file_pattern
        sp_index = self._indexes.get_index(ex_id, "sp")
        self._schema["$defs"]["node"]["properties"]["anyOf"][sp_index] = \
            {"$ref": extractor.ref}

    def remove_extractor(self, extractor: AExtractor) -> None:
        """
        Removes extractor from extractor list.
        Reflects removal in schema and input files patterns list.
        """
        if extractor not in self._extractors:
            raise RuntimeError("Unknown Extractor")
        ex_id = extractor.id
        indexes = self._indexes.get_index(ex_id)
        self._extractors.pop(indexes["ex"], None)
        self._input_file_patterns.pop(indexes["ifp"], None)
        self._schema["$defs"]["node"]["properties"]["anyOf"].pop(indexes["sp"], None)
        self._schema["$defs"].pop(ex_id, None)
        self._indexes.drop_indexes(ex_id)
        self._cache.drop(ex_id)
        extractor._parsers.remove(self)

    def get_extractor(self, extractor_name: str) -> AExtractor:
        """
        helper method returns extractor given a extractor name
        """
        for ex in self.extractors:
            if ex.name == extractor_name:
                return ex
        LOG.warning(f"No extractor with name: {extractor_name} exist")

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
        usually by sending calling all extract's linked to the file-name or regexp of files names.

        :param file_paths: list of file paths (Path)
        """
        to_extract = {}
        meta_files = []
        # TODO: Think about parallelization scheme with ProcessPoolExecutor
        # Would it be worth it in terms of performance?
        for extractor in self._extractors:
            ex_id = extractor.id
            to_extract[ex_id] = []
            LOG.debug(f'    preparing extractor: {ex_id}')
            for fp in file_paths:
                pattern = extractor.input_file_pattern
                if pattern[0] == '*':
                    pattern = '.' + pattern
                if fullmatch(pattern, fp.name):
                    to_extract[ex_id].append(fp)

        # TODO: Think about parallelization scheme with ProcessPoolExecutor
        # For instance this loop is trivially parallelizable if there is no file usage overlap
        for ex_id in to_extract:
            for file_path in to_extract[ex_id]:
                # Get extractor and extract metadata
                ex_index = self._indexes.get_index(ex_id, "ex")
                extractor = self._extractors[ex_index]
                metadata = extractor.extract_metadata_from_file(file_path)

                if not self._lazy_load:
                    # self._update_metadata_tree_with_path_hierarchy(metadata, decompress_path, file_path)
                    self._cache[ex_id].add(
                        decompress_path,
                        file_path,
                        metadata
                    )
                else:
                    entry = self._cache[ex_id].add(
                        decompress_path,
                        file_path
                    )
                    if entry.meta_path.exists():
                        if override_meta_files:
                            LOG.warning(f"Metadata file {entry.meta_path} exists, overriding.")
                        else:
                            raise FileExistsError(
                                f"Unable to save extracted metadata: {entry.meta_path} exists")
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
        and whenever an extractor context is found the branch terminates.
        Handles additional context like extractor directives (!extractor) and directory directives (!varname).

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

                # If current context and child context contain regex information
                # We merge all recursion results from children and return the resulting merge
                if "useRegex" in context:
                    tree = _merge_dicts(tree, self._update_metadata_tree_with_schema2(value, branch))

                # If current context does not contain regex information but child context does
                # We retrieve the root node of the children recursion and an entry to the tree
                elif "useRegex" in value.context:
                    recursion_result = self._update_metadata_tree_with_schema2(value, branch)
                    if key not in recursion_result:
                        LOG.debug(f"current metadata tree: {tree}\n\nrecursion results: {recursion_result}")
                        raise RuntimeError("Malformed metadata tree when processing regex context")
                    tree[key] = self._update_metadata_tree_with_schema2(value, branch)[key]

                # Else we add a new entry to the tree using the recursion results
                else:
                    tree[key] = self._update_metadata_tree_with_schema2(value, branch)

                branch.pop()

            # If entry corresponds to an extractor reference
            elif key == "$extractor_id" and isinstance(value, str):

                # Currently only one extractor reference per entry is allowed
                # and if a reference exists it must be the only content in the entry
                if len(interpreted_schema.items()) > 1:
                    LOG.debug(dumps(interpreted_schema._content, indent=4, default=vars))
                    raise RuntimeError(f"Invalid entry content {interpreted_schema.key}: {interpreted_schema._content}")

                # Get extractor and its cache
                extractor = self.get_extractor(value)
                cache_extractor = self._cache[value]

                # Extractor may have processed multiple files
                extracted_metadata = None

                # For all cache entries
                for cache_entry in cache_extractor:

                    # If needed match path against branch position
                    if "useRegex" in context:

                        # Extracted metadata should be structured in a dictionary
                        # where keys are filenames and values are metadata
                        if extracted_metadata is None:
                            extracted_metadata = {}

                        is_match = False

                        # If no path is available for matching the we match using the available branch paths
                        if not ("!extractor" in context and "path" in context["!extractor"]):
                            file_path_parts = list(cache_entry.rel_path.parent.parts)
                            file_path_parts.reverse()
                            # We skip the last element as it represents the node name of the extracted metadata
                            # not included in the path of the tree
                            reversed_branch = list(reversed(branch[:len(branch) - 1]))

                            # We match through looping over the branch parts in reverse order
                            for i, part in enumerate(reversed_branch):

                                # Expand star pattern
                                # TODO: should star patterns be allowed without using path information?
                                if part == "*":

                                    # If star at end of regex path then match is true
                                    if (i + 1) == len(regex_path):
                                        continue

                                    # Else match against same index element in file path
                                    # TODO: star matching should always be true, is this necessary?
                                    elif not match('.*', file_path_parts[i]):
                                        LOG.debug(f"{part} did not match against {file_path_parts[i]}")
                                        break

                                # Else literal matching
                                elif not match(part, file_path_parts[i]):
                                    LOG.debug(f"{part} did not match against {file_path_parts[i]}")
                                    break
                            
                            # Everything matched in the for loop i.e. no breakpoint reached
                            else:
                                is_match = True

                        # Otherwise we prioritize path matching using extractor directives
                        else:
                            file_path_parts = list(cache_entry.rel_path.parts)
                            file_path_parts.reverse()
                            regex_path = context["!extractor"]["path"].split("/")
                            regex_path.reverse()

                            # We match through looping over the regex path in reverse order
                            for i, part in enumerate(regex_path):

                                # Expand star pattern
                                if part == "*":

                                    # If star at end of regex path then match is true
                                    if (i + 1) == len(regex_path):
                                        continue

                                    # Else match against same index element in file path
                                    # TODO: star matching should always be true, is this necessary?
                                    elif not match('.*', file_path_parts[i]):
                                        LOG.debug(f"{part} did not match against {file_path_parts[i]}")
                                        break
                                
                                # Match against varname
                                elif fullmatch('.*{[a-zA-Z0-9_]+}.*', part):
                                    # !varname should always be in context in this case
                                    if "!varname" not in context:
                                        # TODO: should we instead raise an error?
                                        LOG.critical(f"Varname required to match with variables: {regex_path}")
                                        break
                                    
                                    # correctly interpreted !varname should also come with a regexp in context
                                    if "regexp" not in context:
                                        LOG.debug(dumps(interpreted_schema, indent=4, default=vars))
                                        raise RuntimeError("!varname in context but no regexp found")

                                    # Else match against same index element in file path
                                    elif not match(part.format(**{context["!varname"]: context["regexp"]}), file_path_parts[i]):
                                        LOG.debug(f"{part} did not match against {file_path_parts[i]}")
                                        break

                                # Else literal matching
                                elif not match(part, file_path_parts[i]):
                                    LOG.debug(f"{part} did not match against {file_path_parts[i]}")
                                    break
                            
                            # Everything matched in the for loop i.e. no breakpoint reached
                            else:
                                is_match = True
                                    
                        # If the match is negative then we skip the current cache entry
                        if not is_match:
                            continue

                    # If not in a regex context then extracted metadata is structured
                    # in a list and metadata is appended to it
                    else:
                        if extracted_metadata is None:
                            extracted_metadata = []

                    # Lazy loading handling
                    metadata = cache_entry.load_metadata()
                    
                    # Compute additional directives if given
                    if "!extractor" in context and "keys" in context["!extractor"]:
                        filtered_metadata = extractor.filter_metadata(
                            metadata, context["!extractor"]["keys"],
                            **kwargs)
                        
                        # When in a regex context then resulting extracted metadata is a dict
                        if isinstance(extracted_metadata, dict):

                            # When updating the extracted metadata dict,
                            # the relative path to cache entry is used,
                            # however the filename is changed to the name of key of the interpreted_schema key.
                            relative_path = cache_entry.rel_path.parent / interpreted_schema.key
                            _update_dict_with_path_hierarchy(extracted_metadata, filtered_metadata, relative_path)

                        # Else by default we append to a list
                        else:
                            extracted_metadata.append(filtered_metadata)

                    # Else directly add metadata
                    else:
                        # When in a regex context then resulting extracted metadata is a dict
                        if isinstance(extracted_metadata, dict):

                            # When updating the extracted metadata dict,
                            # the relative path to cache entry is used,
                            # however the filename is changed to the name of key of the interpreted_schema key.
                            relative_path = cache_entry.rel_path.parent / interpreted_schema.key
                            _update_dict_with_path_hierarchy(extracted_metadata, metadata, relative_path)

                        # Else by default we append to a list
                        else:
                            extracted_metadata.append(metadata)

                # Update tree according to metadata retrieved
                if isinstance(extracted_metadata, list):
                    tree = extracted_metadata[0] if len(extracted_metadata) == 1 else extracted_metadata
                else:
                    tree = extracted_metadata
            
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
            for extractor_cache in self._cache:
                for cache_entry in extractor_cache:
                    cache_entry.load_metadata()
                    _update_dict_with_path_hierarchy(
                        self.metadata,
                        cache_entry.metadata,
                        cache_entry.rel_path)

        return self.metadata


def _combine(parser1: Parser,
             parser2: Parser,
             schema: Optional[dict] = None) -> Parser:
    """
    Function used to combine two different parsers.
    Combination is never done in-place.
    Needs an englobing schema that will take into account the combination of extractors.
    """
    ll = False
    if parser1.lazy_load != parser2.lazy_load:
        LOG.warning(
            f"Lazy load configuration mismatch. Setting to default: {ll}")
    else:
        ll = parser1.lazy_load
    combined_parser = Parser(schema=schema,
                             extractors=parser1.extractors +
                             parser2.extractors,
                             lazy_load=ll)

    if len(parser1.metadata) > 0 or len(parser2.metadata) > 0:
        #combined_parser.metadata = _merge_dicts(parser1.metadata, parser2.metadata)
        raise NotImplementedError("Combining Parsers with existing metadata is not yet implemented.")

    return combined_parser


Parser.combine = _combine
