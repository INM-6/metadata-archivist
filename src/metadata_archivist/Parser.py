#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""

Extractor class to get metadata from file.
Parser class for handling Extractors.
To be specialized by custom parsers made by users.
Authors: Jose V., Matthias K.

"""

import re
import abc  # Abstract class base infrastructure

import jsonschema  # to validate extracted data

from json import dump, load
from pathlib import Path
from typing import Optional, List, Tuple, NoReturn
from collections import Iterable

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

    # Protected
    _input_file_pattern: str
    _schema: dict  # JSON schema as dict

    # To be handled by Parser class
    _parsers = [] # For two way relationship update handling

    # Immutable
    _name: str  # name of the extractor

    # Public
    extracted_metadata: dict  # JSON object as dict to be used as cache

    def __init__(self, name: str, input_file_pattern: str, schema: dict) -> None:
        """
        Initialization for base AExtractor.
        Necessary due to decorators used for encapsulation of attributes.
        """
        super().__init__()
        self._name = name
        self._input_file_pattern = input_file_pattern
        self._schema = schema
        self.extracted_metadata = {}

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
        raise AttributeError("The name of an Extractor is an immutable attribute")

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
        return self.__hash__() == other.__hash__()

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
                schema: Optional[dict] = None,
                extractors: Optional[List[AExtractor]] = None,
                lazy_load: Optional[bool] = False) -> None:
        
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

        # Used for internal handling:
        # Shouldn't use much memory but TODO: check additional memory usage

        # Set lazy loading
        self._lazy_load = lazy_load

        # Used for updating/removing extractors
        # Indexing is done storing a triplet with extractors, patterns, schema indexes
        self._indexes = {}

        # For extractor result caching
        self._cache = {}

        # Public
        self.metadata = {}

        self.combine = lambda parser2, schema=None: _combine(parser1=self, parser2=parser2, schema=schema)

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
        raise AttributeError("Extractors list should be modified through add, update and remove procedures")
    
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
        raise AttributeError("Input file patterns list should be modified through add, update and remove procedures")
    
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
                raise RuntimeError("Lazy loading needs to be enabled before metadata extraction")
        else:
            if len(self.metadata) > 0:
                # TODO: Should we raise exception instead of warning?
                LOG.warning("Warning: compiling available metadata after enabling lazy loading.", RuntimeWarning)
            self.compile_metadata()
        self._lazy_load = lazy_load

    def _extend_json_schema(self, extractor: AExtractor) -> None:
        """
        Extends parser schema (dict) with a given extractor schema (dict).
        Indexes schema.
        """
        if "$defs" not in self._schema.keys():
            self._schema["$defs"] = {
                "node": {
                    "properties": {
                        "anyOf": []
                    }
                }
            }
        ex_id = extractor.__hash__()
        self._schema["$defs"][ex_id] = extractor.schema
        self._indexes[ex_id][2] = len(self._schema["$defs"]["node"]["properties"]["anyOf"])
        self._schema["$defs"]["node"]["properties"]["anyOf"].append(
            {"$ref": f"#/$defs/{ex_id}"}
        )

    def add_extractor(self, extractor: AExtractor) -> None:
        """
        Method to add extractor to list.
        Indexes extractors list and input files patterns list.
        """
        if extractor in self.extractors:
            raise RuntimeError("Extractor is already in Parser")
        ex_id = extractor.__hash__()
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
        ex_id = extractor.__hash__()
        self._schema["$defs"][ex_id] = extractor.schema
        self._input_file_patterns[self._indexes[ex_id][1]] = extractor.input_file_pattern
        self._schema["$defs"]["node"]["properties"]["anyOf"][self._indexes[ex_id][2]] = \
            {"$ref": f"#/$defs/{ex_id}"}
        
    def remove_extractor(self, extractor: AExtractor) -> None:
        """
        Removes extractor from extractor list.
        Reflects removal in schema and input files patterns list.
        """
        if extractor not in self._extractors:
            raise RuntimeError("Unknown Extractor")
        ex_id = extractor.__hash__()
        self._extractors.pop(self._indexes[ex_id][0], None)
        self._input_file_patterns.pop(self._indexes[ex_id][1], None)
        self._schema["$defs"]["node"]["properties"]["anyOf"].pop(self._indexes[ex_id][2], None)
        self._schema["$defs"].pop(ex_id, None)
        self._indexes.pop(ex_id, None)
        extractor._parsers.remove(self)

    def _update_metadata_tree(self, decompress_path: Path, file_path: Path) -> Path:
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
            self._deep_set(metadata[path.parts[0]], value,
                           path.relative_to(path.parts[0]))

    def parse_file(self, file_path: Path) -> None:
        """
        Add metadata from input file to metadata object,
        usually by sending calling all extract's linked to the file-name or regexp of file name.

        :param file_path: path to file (Path)
        """

        # TODO: Should lazy loading also be implemented here?

        rel_file_path = self._update_metadata_tree(file_path)

        for extractor in self._extractors:
            pattern = extractor.input_file_pattern
            if pattern[0] == '*':
                pattern = '.' + pattern
            if re.fullmatch(pattern, file_path.name):
                metadata = extractor.extract_metadata_from_file(
                    file_path)
                # TODO: The metadata tree should be compiled/merged with the Parser schema
                # We should think if this is to be done instead of the path tree structure
                # or do it afterwards through another mechanism
                #   ->  Think about reshaping/filtering function for dictionaries using schemas
                #       add bool condition to switch between directory hierarchy for metadata objects
                #            or schema hierarchy
                #       add linking between extracted metadata object properties through schema keywords
                #           -> cf mattermost chat
                self._deep_set(self.metadata, metadata, rel_file_path)

    def _update_metadata_tree_with_path_hierarchy(self,
                                                  metadata: dict,
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
            hierarchy.reverse() # Get the hierarchy starting from root node
            hierarchy.pop(0) # Remove '.' node
            iterator = iter(hierarchy)
            node = next(iterator) # Should not raise StopIteration as there is at least one element in list
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
                raise RuntimeError(f"Could not update metadata tree based on file hierarchy. File: {file_path}")

    def parse_files(self, decompress_path: Path, file_paths: List[Path]) -> Tuple[dict, List[Path]]:
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
            ex_id = extractor.__hash__()
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
                    self._cache[ex_id].append((metadata, decompress_path, file_path))
                else:
                    meta_path = Path(str(file_path) + ".meta")
                    if meta_path.exists():
                        raise FileExistsError(f"Unable to save extracted metadata: {meta_path} exists")
                    with meta_path.open("w") as mp:
                        dump(metadata, mp, indent=4)
                    meta_files.append(meta_path)
                    self._cache[ex_id].append((meta_path, decompress_path, file_path))

        return meta_files
    
    def _update_metadata_tree_with_schema(self) -> None:
        if len(self._cache) == 0:
            raise RuntimeError("Metadata needs to be parsed before updating the tree")
        # Explore schema
        # When reference found
        # Get extractor id from defs
        ex_id = None # Get extractor id from defs
        for meta, decompress_path, file_path in self._cache[ex_id]:
            if isinstance(meta, Path):
                with meta.open("r") as f:
                    metadata = load(f)
            elif isinstance(meta, dict):
                metadata = meta
            else:
                raise TypeError("Incorrect meta object type")
                    
        # Fill tree with metadata
        
        raise NotImplementedError

    def compile_metadata(self) -> dict:
        """
        Function to gather all metadata extracted using parsing function with lazy loading.
        """
        if len(self._cache) == 0:
            raise RuntimeError("Metadata needs to be parsed before updating the tree")
        if self._use_schema:
            self._update_metadata_tree_with_schema()
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
                    
                    self._update_metadata_tree_with_path_hierarchy(metadata, decompress_path, file_path)

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
                            merged_dict[key] = frozenset(list(val1) + list(val2))
                        else:
                            raise RuntimeError(f"Unknown Iterable type: {type(val1)}")
                    else:
                        if val1 == val2:
                            merged_dict[key] = val1
                        else:
                            merged_dict[key] = [val1, val2]
                else:
                    raise TypeError
            except TypeError:
                # TODO: Need to deal with the combination of shared parser metadata.
                LOG.critical(f"Combination of heterogeneous metadata is not yet implemented.\n          Dropping mutual metadata {key}")
        else:
            merged_dict[key] = dict1[key]
    for key in keys2:
            merged_dict[key] = dict2[key]

    return merged_dict


def _combine(parser1: Parser, parser2: Parser, schema: Optional[dict] = None) -> Parser:
    """
    Function used to combine two different parsers.
    Combination is never done in-place.
    Needs an englobing schema that will take into account the combination of extractors.
    """
    ll = False
    if parser1.lazy_load !=parser2.lazy_load:
        LOG.warning(f"Lazy load configuration mismatch. Setting to default: {ll}")
    else:
        ll = parser1.lazy_load
    schema = schema if schema is not None else DEFAULT_PARSER_SCHEMA
    combined_parser = Parser(schema=schema, extractors=parser1.extractors + parser2.extractors, lazy_load=ll)

    if len(parser1.metadata) > 0 or len(parser2.metadata) > 0:
        raise NotImplementedError("Cannot yet Parser with existing metadata")
        combined_parser.metadata = _merge_dicts(parser1.metadata, parser2.metadata)

    return combined_parser

Parser.combine = _combine
