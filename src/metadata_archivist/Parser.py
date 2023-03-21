#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""

Extractor class to get metadata from file.
Parser class for handling Extractors.
To be specialized by custom parsers made by users.
Authors: Jose V., Matthias K.

"""

import jsonschema  # to validate extracted data
import json
import sys
import re
import abc  # Abstract class base infrastructure

import jsonschema  # to validate extracted data

from json import dump, load
from pathlib import Path
from typing import Optional, List, Tuple, NoReturn, Literal, Union
from .util import get_structured_metadata
from collections.abc import Iterable

from .Logger import LOG

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


class AExtractor(abc.ABC):
    """
    Base extractor class.
    There is a one to one mapping from extractors
    to extracted files.
    Many extractors can "look for" the same metadata
    but will differ on the file they process and how.

    Extractors use schemas to validate and structure
    the data they process. The extraction process and
    returned structure defines the schema.
    """
    ref: str  # the ref string usually: '#/$defs/{self.name}'

    # Protected
    _input_file_pattern: str
    _schema: dict  # JSON schema as dict

    # To be handled by Parser class
    _parsers = []  # For two way relationship update handling

    # Immutable
    _name: str  # name of the extractor

    # Public
    extracted_metadata: dict  # JSON object as dict to be used as cache

    def __init__(self,
                 name: str,
                 input_file_pattern: str,
                 schema: dict,
                 ref: Optional[str] = None) -> None:
        """
        Initialization for base AExtractor.
        Necessary due to decorators used for encapsulation of attributes.
        """
        super().__init__()
        self._name = name
        self._input_file_pattern = input_file_pattern
        self._schema = schema

        self.ref = f"#/$defs/{self.id}"
        self.extracted_metadata = {}
        if ref is None:
            self.ref = f'#/$defs/{self.name}'
        else:
            self.ref = ref

    @property
    def input_file_pattern(self) -> str:
        """Returns extractor input file pattern (str)."""
        return self._input_file_pattern

    @input_file_pattern.setter
    def input_file_pattern(self, pattern: str) -> None:
        """
        Sets extractor input file pattern (str).
        Triggers parsers update.
        """
        self._input_file_pattern = pattern
        self._update_parsers()

    @property
    def schema(self) -> dict:
        """Returns extractor schema (dict)."""
        return self._schema

    # TODO: Now, schema should not be directly modified but completely replaced, is this correct?
    @schema.setter
    def schema(self, schema: dict) -> None:
        """
        Sets extractor schema (dict).
        Triggers parsers update.
        """
        self._schema = schema
        self._update_parsers()

    @property
    def name(self) -> str:
        """Returns extractor name (str)."""
        return self._name

    @name.setter
    def name(self, _) -> NoReturn:
        """
        Forbidden setter for name attribute.
        (pythonic indirection for protected attributes)
        """
        raise AttributeError(
            "The name of an Extractor is an immutable attribute")

    @property
    def id(self) -> int:
        """
        Returns unique identifier for extractor
        """
        return self._name  # self.__hash__() for more complex cases

    @id.setter
    def id(self, _) -> NoReturn:
        """
        Forbidden setter for id attribute.
        (pythonic indirection for protected attributes)
        """
        raise AttributeError(
            "Cannot manually set the id.\nThe id of an Extractor is a computed property based on the Extractor attributes."
        )

    def _update_parsers(self) -> None:
        """Reverse update of related parsers."""
        for p in self._parsers:
            p.update_extractor(self)

    def extract_metadata_from_file(
            self, file_path: Path) -> dict:  # JSON object as dict
        """
        Wrapper for the user defined extract method,
        takes care of prior file checking and applies validate
        on extracted metadata.
        """
        pattern = self.input_file_pattern
        if pattern[0] == '*':
            pattern = '.' + pattern
        if not re.fullmatch(pattern, file_path.name):
            raise RuntimeError(
                f'The input file {file_path.name} does not match the extractors pattern: {self.input_file_pattern}'
            )
        elif not file_path.is_file():
            raise RuntimeError(
                f'The input file {file_path.name} does not exist!')
        else:
            self.extracted_metadata = self.extract(file_path)
        self.validate()

        return self.extracted_metadata

    @abc.abstractmethod
    def extract(self, file_path: Path) -> dict:
        """
        Main method of the Extractor class
        used to "extract" metadata from the files.
        To be defined by custom user classes.
        Must return JSON objects to be able to validate.
        Result is stored in _extracted_metadata  and returned as value.
        """

    def validate(self) -> bool:
        """
        Method used to validate extracted metadata.
        Returns false if validation was not possible or
        metadata has not been extracted yet.

        Returns:
            - True if validation successful False otherwise
        """
        try:
            jsonschema.validate(self.extracted_metadata, schema=self.schema)
            return True
        except jsonschema.ValidationError as e:
            # TODO: better exception mechanism
            LOG.warning(e.message)

        return False

    # Considering the name of the extractor as an immutable and unique property then we should only use
    # the name property for equality/hashing
    # TODO: to verify for robustness and correctness
    def __eq__(self, other) -> bool:
        return self.id == other.id if isinstance(other, type(self)) else False

    def __ne__(self, other) -> bool:
        return not self.__eq__(other)

    def __hash__(self) -> int:
        return hash(self._name)


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
                 extractors: Optional[list[AExtractor]] = None,
                 metadata_tree: Optional[Literal[
                     'from_dir_tree', 'from_schema']] = 'from_schema',
                 lazy_load: Optional[bool] = False,
                 schema: Optional[Union[str, Path, dict]] = None) -> None:
        # Protected
        # These attributes should only be modified through the add, update remove methods
        self._extractors = []
        self._input_file_patterns = []
        # Can also be completely replaced through set method
        if schema is not None:
            self._use_schema = True
            self._schema = schema
        else:
            self._use_schema = False
            self._schema = DEFAULT_PARSER_SCHEMA
        # elif isinstance(schema, (str, Path)):
        #     with open(schema) as f:
        #         self._schema = json.load(f)
        # elif isinstance(schema, dict):
        #     # ToDo: Validate the dict as schema
        #     self._schema = schema

        self.metadata_tree = metadata_tree

        # Used for internal handling:
        # Shouldn't use much memory but TODO: check additional memory usage

        # Set lazy loading
        self._lazy_load = lazy_load

        # Used for updating/removing extractors
        # Indexing is done storing a triplet with extractors, patterns, schema indexes
        # with [<index in self._extractors>,<index in self._input_file_patterns>,<len(
        # self._schema["$defs"]["node"]["properties"]["anyOf"])>  ]
        # the last entry being None if 'node' does not exist
        self._indexes = {}

        # For extractor result caching
        self._cache = {}

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

    def print_schema(self):
        print(json.dumps(self.schema, indent=2))

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
                    "Warning: compiling available metadata after enabling lazy loading.",
                    RuntimeWarning)
            self.compile_metadata()
        self._lazy_load = lazy_load

    def _extend_json_schema(self, extractor: AExtractor) -> None:
        """
        Extends parser schema (dict) with a given extractor schema (dict).
        Indexes schema.
        """
        if "$defs" not in self._schema.keys():
            self._schema["$defs"] = {"node": {"properties": {"anyOf": []}}}
        ex_id = extractor.id
        ex_ref = extractor.ref
        self._schema["$defs"][ex_id] = extractor.schema
        if 'node' in self._schema["$defs"]:
            self._indexes[ex_id][2] = len(
                self._schema["$defs"]["node"]["properties"]["anyOf"])
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
        self._indexes[ex_id] = [len(self._extractors), 0, 0]
        self._extractors.append(extractor)
        self._indexes[ex_id][1] = len(self._input_file_patterns)
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
        self._input_file_patterns[self._indexes[ex_id]
                                  [1]] = extractor.input_file_pattern
        self._schema["$defs"]["node"]["properties"]["anyOf"][self._indexes[ex_id][2]] = \
            {"$ref": extractor.ref}

    def remove_extractor(self, extractor: AExtractor) -> None:
        """
        Removes extractor from extractor list.
        Reflects removal in schema and input files patterns list.
        """
        if extractor not in self._extractors:
            raise RuntimeError("Unknown Extractor")
        ex_id = extractor.id
        self._extractors.pop(self._indexes[ex_id][0], None)
        self._input_file_patterns.pop(self._indexes[ex_id][1], None)
        self._schema["$defs"]["node"]["properties"]["anyOf"].pop(
            self._indexes[ex_id][2], None)
        self._schema["$defs"].pop(ex_id, None)
        self._indexes.pop(ex_id, None)
        extractor._parsers.remove(self)

    def _update_metadata_tree(self, decompress_path: Path,
                              file_path: Path) -> Path:
        """
        Update tree structure of metadata dict with file path.

        :param file_path: path to a file
        """
        iter_dict = self.metadata
        rel_file_path = file_path.relative_to(decompress_path)
        for pp in rel_file_path.parts[:-1]:
            if pp not in iter_dict:
                iter_dict[pp] = {}
                iter_dict = iter_dict[pp]
            elif pp in iter_dict and not isinstance(iter_dict[pp], dict):
                raise RuntimeError(
                    f'Trying to created nested structure in metadata object failed: {pp}'
                )
        return rel_file_path

    def _deep_set(self, metadata: dict, value, path: Path) -> None:
        if len(path.parts) == 1:
            metadata[path.parts[0]] = value
        else:
            self._deep_set_dict_from_path(metadata[path.parts[0]], value,
                                          path.relative_to(path.parts[0]))

    def _deep_set_dict(self, metadata: dict, value: dict):
        for k, v in value.items():
            if v is dict:
                if k not in metadata.keys():
                    metadata[k] = {}
                self._deep_set_dict(metadata[k], v)
            elif k in metadata.keys():
                print(
                    f'Warning: variable {k} exists and will not be overwritten!'
                )
            else:
                metadata[k] = v

    def parse_file(self, file_path: Path) -> None:
        """
        Add metadata from input file to metadata object,
        usually by sending calling all extract's linked to the file-name or regexp of file name.

        :param file_path: path to file (Path)
        """

        # TODO: Should lazy loading also be implemented here?
        rel_file_path = self._update_metadata_tree(file_path)
        if self.metadata_tree == 'from_dir_tree':
            self._update_metadata_tree(rel_file_path)

        for extractor in self._extractors:
            pattern = extractor.input_file_pattern
            if pattern[0] == '*':
                pattern = '.' + pattern
            if re.fullmatch(pattern, file_path.name):
                metadata = extractor.extract_metadata_from_file(file_path)
                # TODO: The metadata tree should be compiled/merged with the Parser schema
                # We should think if this is to be done instead of the path tree structure
                # or do it afterwards through another mechanism
                #   ->  Think about reshaping/filtering function for dictionaries using schemas
                #       add bool condition to switch between directory hierarchy for metadata objects
                #            or schema hierarchy
                #       add linking between extracted metadata object properties through schema keywords
                #           -> cf mattermost chat
                self._deep_set(self.metadata, metadata, rel_file_path)

    def _update_metadata_tree_with_path_hierarchy(self, metadata: dict,
                                                  decompress_path: Path,
                                                  file_path: Path) -> None:
        """
        Generates and dynamically fills the metadata tree with path hierarchy.
        The hierarchy is based on decompressed directory.
        """
        relative_path = file_path.relative_to(decompress_path)
        hierarchy = list(relative_path.parents)
        # '.' is always the root of a relative path hence parents of a relative path will always contain 1 element
        if len(hierarchy) < 2:
            # In case there is no hierarchy then we just add the metadata in a flat structure
            self.metadata[file_path.name] = metadata
        else:
            # Else we generate the hierarchy structure in the metadata tree
            hierarchy.reverse()  # Get the hierarchy starting from root node
            hierarchy.pop(0)  # Remove '.' node
            iterator = iter(hierarchy)
            node = next(
                iterator
            )  # Should not raise StopIteration as there is at least one element in list
            relative_root = self.metadata
            while node is not None:
                node_str = str(node)
                if node_str not in relative_root:
                    relative_root[node_str] = {}
                relative_root = relative_root[node_str]
                try:
                    node = next(iterator).relative_to(node)
                    # If relative paths are not used then they will contain previous node name in path
                except StopIteration:
                    relative_root[file_path.name] = metadata
                    break
            else:
                # If break point not reached
                raise RuntimeError(
                    f"Could not update metadata tree based on file hierarchy. File: {file_path}"
                )

    def parse_files(self, decompress_path: Path,
                    file_paths: List[Path]) -> Tuple[dict, List[Path]]:
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
            for fp in file_paths:
                pattern = extractor.input_file_pattern
                if pattern[0] == '*':
                    pattern = '.' + pattern
                if re.fullmatch(pattern, fp.name):
                    to_extract[ex_id].append(fp)

        # TODO: Think about parallelization scheme with ProcessPoolExecutor
        # For instance this loop is trivially parallelizable if there is no file usage overlap
        for ex_id in to_extract:
            for file_path in to_extract[ex_id]:
                # Get extractor and extract metadata
                extractor = self._extractors[self._indexes[ex_id][0]]
                metadata = extractor.extract_metadata_from_file(file_path)

                # Setup cache for storing
                if ex_id not in self._cache:
                    self._cache[ex_id] = []

                if not self._lazy_load:
                    # self._update_metadata_tree_with_path_hierarchy(metadata, decompress_path, file_path)
                    self._cache[ex_id].append(
                        (metadata, decompress_path, file_path))
                else:
                    meta_path = Path(str(file_path) + ".meta")
                    if meta_path.exists():
                        raise FileExistsError(
                            f"Unable to save extracted metadata: {meta_path} exists"
                        )
                    with meta_path.open("w") as mp:
                        dump(metadata, mp, indent=4)
                    meta_files.append(meta_path)
                    self._cache[ex_id].append(
                        (meta_path, decompress_path, file_path))

        return meta_files

    def _path_from_hierarchy(self, hierarchy) -> list:
        return [x['dir'] for x in hierarchy if x['type'] == 'object']

    def _update_metadata_tree_with_schema(self, hierarchy: list,
                                          extractor: AExtractor,
                                          prop_name: str) -> None:
        if len(self._cache) == 0:
            raise RuntimeError(
                "Metadata needs to be parsed before updating the tree")
        # Fill tree with metadata

        if 'properties' not in self.schema.keys():
            raise RuntimeError(f'No properties found in schema')
        # metadata = self._cache[extractor.id]

        # Else we generate the hierarchy structure in the metadata tree
        for meta_set in self._cache[extractor.id]:
            if self._schema_node_matches_file_path(
                    meta_set, self._path_from_hierarchy(hierarchy)):
                iterator = iter(meta_set[2].relative_to(meta_set[1]).parts)
                node = next(iterator)
                relative_root = self.metadata
                while node is not None:
                    if node not in relative_root:
                        relative_root[node] = {}
                    relative_root = relative_root[node]
                    try:
                        node = next(iterator)
                        # If relative paths are not used then they will contain previous node name in path
                    except StopIteration:
                        relative_root[node] = meta_set[0]
                        break
                else:
                    # If break point not reached
                    raise RuntimeError(
                        "Could not update metadata tree based on file hierarchy. File: {file_path}"
                    )

    def _schema_node_matches_file_path(self, meta_tuple, schema_hierachy):
        file_path_hierarchy = list(meta_tuple[2].relative_to(
            meta_tuple[1]).parts[:-1])
        file_path_hierarchy.reverse()
        schema_hierachy.reverse()

        if len(file_path_hierarchy) == len(schema_hierachy) == 0:
            # In case there is no hierarchy then we just add the metadata in the root
            return True
        else:
            schema_iterator = iter(schema_hierachy)
            schema_dir = next(
                schema_iterator)  # due to 'if' len(schema_hierachy) >= 1
            for i, path_dir in enumerate(file_path_hierarchy):
                # if len(file_path_hierarchy) < i + zz:
                #     # file_path_hierachy at the end but schema_hierachy still going, no match
                #     return False

                if isinstance(schema_dir, str):
                    if not schema_dir == path_dir:
                        return False
                    try:
                        schema_dir = next(schema_iterator)
                    except StopIteration:
                        if i + 1 != len(file_path_hierarchy):
                            return False
                elif isinstance(schema_dir, re.Pattern):
                    if not schema_dir.match(path_dir):
                        return False
                    try:
                        schema_dir = next(schema_iterator)
                    except StopIteration:
                        if i + 1 != len(file_path_hierarchy):
                            return False
            return True

    def _schema_iterator(self,
                         properties: Optional[dict] = None,
                         hierachy: Optional[list] = None,
                         use_regex: Optional[bool] = False):
        """
        schema iterator, returns nodes in schema.
        a node is a entry in a property that itself has no further properties
        TODO: handle 'pattern properties' and 'additional properties'
        TODO: handle recursion, first detect recursion and break, second handle it
        depending on path depth of files in corresponding extractors

        if a ref entry is found
        1. the extractors are checked, if the ref, matches any of them. if so, the metadata from
        the extractor is placed at that point
        2. if no extractor is found check the defs for the reference, if a match is found, put
        the subschema from the defs in the schema and contiune searching
        """
        if properties is None:
            properties = self.schema['properties']
        if hierachy is None:
            hierachy = []
        for prop_name, prop in properties.items():
            # if isinstance(prop, dict) and 'properties' == prop_name:
            if 'properties' == prop_name:
                yield from self._schema_iterator(prop, hierachy)
            elif 'patternProperties' == prop_name:
                yield from self._schema_iterator(prop,
                                                 hierachy,
                                                 use_regex=True)
            elif 'unevaluatedProperties' == prop_name and prop:
                yield from self._schema_iterator(prop, hierachy)
            elif 'additionalProperties' == prop_name and prop:
                yield from self._schema_iterator(prop, hierachy)
            elif prop_name == '$ref':
                matching_extractor = None
                for ex in self.extractors:
                    if ex.ref == prop[:len(ex.ref)]:
                        matching_extractor = ex
                        break
                if matching_extractor is not None:
                    yield prop, hierachy, matching_extractor, prop_name
                    break
                else:
                    for defs in self.schema['$defs']:
                        defstring = f'#/$defs/{defs}'.strip()
                        if defstring == prop[:len(defstring)]:
                            subschem = self.schema['$defs'][defs.split('/')
                                                            [-1]]
                            node_dict = {
                                'name':
                                defs,
                                'type':
                                subschem['type']
                                if 'type' in subschem.keys() else None,
                                'description':
                                subschem['description']
                                if 'description' in subschem.keys() else None,
                                'dir':
                                defs if 'type' in subschem.keys()
                                and subschem['type'] == 'object' else None,
                            }
                            if use_regex:
                                node_dict['dir'] = re.compile(
                                    defs
                                ) if 'type' in subschem.keys(
                                ) and subschem['type'] == 'object' else None
                            else:
                                node_dict[
                                    'dir'] = defs if 'type' in subschem.keys(
                                    ) and subschem['type'] == 'object' else None
                            yield from self._schema_iterator(
                                subschem, hierachy + [node_dict])
                            break
            elif isinstance(prop, dict):
                node_dict = {
                    'name':
                    prop_name,
                    'type':
                    prop['type'] if 'type' in prop.keys() else None,
                    'description':
                    prop['description']
                    if 'description' in prop.keys() else None,
                }
                if use_regex:
                    node_dict['dir'] = re.compile(
                        prop_name) if 'type' in prop.keys(
                        ) and prop['type'] == 'object' else None
                else:
                    node_dict['dir'] = prop_name if 'type' in prop.keys(
                    ) and prop['type'] == 'object' else None
                yield from self._schema_iterator(prop, hierachy + [node_dict])
            # do we want to include further information, e.g. static infos, description etc.? this could be possibly done here
            # else:
            #     yield prop, hierachy + [prop_name], matching_extractor

    def compile_metadata(self) -> dict:
        """
        Function to gather all metadata extracted using parsing function with lazy loading.
        """
        if len(self._cache) == 0:
            raise RuntimeError(
                "Metadata needs to be parsed before updating the tree")
        if self._use_schema:
            LOG.debug("    using schema")
            iterator = self._schema_iterator()
            while True:
                try:
                    _, hierarchy, extractor, prop_name = next(iterator)
                    LOG.debug(
                        f'        working on: {self._path_from_hierarchy(hierarchy)}/{hierarchy[-1]["name"]}'
                    )
                    self._update_metadata_tree_with_schema(
                        hierarchy, extractor, prop_name)
                except StopIteration:
                    break
        else:
            for ex_id in self._cache:
                for meta, decompress_path, file_path in self._cache[ex_id]:
                    if isinstance(meta, Path):
                        with meta.open("r") as f:
                            metadata = load(f)
                    elif isinstance(meta, dict):
                        metadata = meta
                    else:
                        raise TypeError("Incorrect meta object type")

                    self._update_metadata_tree_with_path_hierarchy(
                        metadata, decompress_path, file_path)

        return self.metadata


def _merge_dicts(dict1: dict, dict2: dict) -> dict:
    """
    Recursively merges dictionaries going in depth for nested structures.
    """
    keys1 = list(dict1.keys())
    keys2 = list(dict2.keys())
    merged_dict = {}
    for key in keys1:
        if key in keys2:
            keys2.remove(key)
            val1 = dict1[key]
            val2 = dict2[key]
            try:
                # TODO: behavior needs to be validated
                if type(val1) == type(val2):
                    if isinstance(val1, Iterable):
                        if isinstance(val1, dict):
                            merged_dict[key] = _merge_dicts(dict1, dict2)
                        elif isinstance(val1, list):
                            merged_dict[key] = val1 + val2
                        elif isinstance(val1, set):
                            merged_dict[key] = val1 | val2
                        elif isinstance(val1, tuple):
                            merged_dict[key] = tuple(list(val1) + list(val2))
                        elif isinstance(val1, frozenset):
                            merged_dict[key] = frozenset(
                                list(val1) + list(val2))
                        else:
                            raise RuntimeError(
                                f"Unknown Iterable type: {type(val1)}")
                    else:
                        if val1 == val2:
                            merged_dict[key] = val1
                        else:
                            merged_dict[key] = [val1, val2]
                else:
                    raise TypeError
            except TypeError:
                # TODO: Need to deal with the combination of shared parser metadata.
                LOG.critical(
                    f"Combination of heterogeneous metadata is not yet implemented.\n          Dropping mutual metadata {key}"
                )
        else:
            merged_dict[key] = dict1[key]
    for key in keys2:
        merged_dict[key] = dict2[key]

    return merged_dict


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
    schema = schema if schema is not None else DEFAULT_PARSER_SCHEMA
    combined_parser = Parser(schema=schema,
                             extractors=parser1.extractors +
                             parser2.extractors,
                             lazy_load=ll)

    if len(parser1.metadata) > 0 or len(parser2.metadata) > 0:
        raise NotImplementedError("Cannot yet Parser with existing metadata")
        combined_parser.metadata = _merge_dicts(parser1.metadata,
                                                parser2.metadata)

    return combined_parser


# def defs2dict(defs, search_dict: Optional[dict] = None):
#     sep = '/'
#     if sep not in defs and search_dict is None:
#         return defs
#     elif sep not in defs and search_dict:
#         return search_dict[defs]
#     key, val = defs.split(sep, 1)
#     if key == '#':
#         key, val = val.split(sep, 1)
#     if search_dict is None:
#         return {key: defs2dict(val, None)}
#     else:
#         return {key: defs2dict(val, search_dict[key])}

Parser.combine = _combine
