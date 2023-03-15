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

from json import dump
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
        return self._name == other.name

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

        self._metadata = {}
        if schema is None:
            self._schema = DEFAULT_PARSER_SCHEMA
        elif isinstance(schema, (str, Path)):
            with open(schema) as f:
                self._schema = json.load(f)
        elif isinstance(schema, dict):
            # ToDo: Validate the dict as schema
            self._schema = schema

        self.metadata_tree = metadata_tree

        # Used for internal handling:
        # Shouldn't use much memory but TODO: check additional memory usage
        self._lazy_load = lazy_load
        if lazy_load:
            self._load_indexes = {}
        # Used for updating/removing extractors
        # Indexing is done storing a triplet with extractors, patterns, schema indexes
        # with [<index in self._extractors>,<index in self._input_file_patterns>,<len(
        # self._schema["$defs"]["node"]["properties"]["anyOf"])>  ]
        # the last entry being None if 'node' does not exist
        self._indexes = {}

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
            self._load_indexes = {}
        else:
            if len(self.metadata) > 0:
                # TODO: Should we raise exception instead of warning?
                LOG.warning(
                    "Warning: compiling available metadata after enabling lazy loading.",
                    RuntimeWarning)
            self.compile_metadata()

    def _extend_json_schema(self, extractor: AExtractor) -> None:
        """
        Extends parser schema (dict) with a given extractor schema (dict).
        Indexes schema.
        """
        if "$defs" not in self._schema.keys():
            self._schema["$defs"] = {}
        self._schema["$defs"][extractor.name] = extractor.schema
        if 'node' in self._schema["$defs"]:
            self._indexes[extractor.name][2] = len(
                self._schema["$defs"]["node"]["properties"]["anyOf"])
            self._schema["$defs"]["node"]["properties"]["anyOf"].append(
                {"$ref": f"#/$defs/{extractor.name}"})
            # {"$ref": f"{extractor.ref}"})
        else:
            self._indexes[extractor.name][2] = None

    def add_extractor(self, extractor: AExtractor) -> None:
        """
        Method to add extractor to list.
        Indexes extractors list and input files patterns list.
        """
        if extractor in self.extractors:
            raise RuntimeError("Extractor is already in Parser")
        self._indexes[extractor.name] = [len(self._extractors), 0, 0]
        self._extractors.append(extractor)
        self._indexes[extractor.name][1] = len(self._input_file_patterns)
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
        self._schema["$defs"][extractor.name] = extractor.schema
        self._input_file_patterns[self._indexes[extractor.name]
                                  [1]] = extractor.input_file_pattern
        if self._indexes[extractor.name][2] is not None:
            self._schema["$defs"]["node"]["properties"]["anyOf"][self._indexes[extractor.name][2]] = \
                {"$ref": f"#/$defs/{extractor.name}"}

    def remove_extractor(self, extractor: AExtractor) -> None:
        """
        Removes extractor from extractor list.
        Reflects removal in schema and input files patterns list.
        """
        if extractor not in self._extractors:
            raise RuntimeError("Unknown Extractor")
        self._extractors.pop(self._indexes[extractor.name][0], None)
        self._input_file_patterns.pop(self._indexes[extractor.name][1], None)
        if self._indexes[extractor.name][2] is not None:
            self._schema["$defs"]["node"]["properties"]["anyOf"].pop(
                self._indexes[extractor.name][2], None)
        self._schema["$defs"].pop(extractor.name, None)
        self._indexes.pop(extractor.name, None)
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
        if len(hierarchy) < 1:
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
            to_extract[extractor.name] = []
            for fp in file_paths:
                pattern = extractor.input_file_pattern
                if pattern[0] == '*':
                    pattern = '.' + pattern
                if re.fullmatch(pattern, fp.name):
                    to_extract[extractor.name].append(fp)

        # TODO: Think about parallelization scheme with ProcessPoolExecutor
        # For instance this loop is trivially parallelizable if there is no file usage overlap
        for exn in to_extract:
            for file_path in to_extract[exn]:
                metadata = self._extractors[self._indexes[exn][
                    0]].extract_metadata_from_file(file_path)
                if self.metadata_tree == 'from_schema':
                    metadata = get_structured_metadata(
                        self.schema,
                        self._extractors[self._indexes[exn][0]].ref, metadata)
                if not self._lazy_load:
                    self._update_metadata_tree_with_path_hierarchy(
                        metadata, decompress_path, file_path)
                else:
                    meta_path = Path(str(file_path) + ".meta")
                    if meta_path.exists():
                        raise FileExistsError(
                            f"Unable to save extracted metadata: {meta_path} exists"
                        )
                    with meta_path.open("w") as mp:
                        dump(metadata, mp, indent=4)
                    meta_files.append(meta_path)
                    self._load_indexes[exn] = (meta_path, decompress_path,
                                               file_path)

        return self.metadata, meta_files

    def compile_metadata(self) -> dict:
        """
        Function to gather all metadata extracted using parsing function with lazy loading.
        """
        if not self._lazy_load:
            raise RuntimeError(
                "Unable to compile metadata, lazy loading not enabled")
        for exn in self._load_indexes:
            meta_info = self._load_indexes[exn]
            with meta_info[0].open("r") as f:
                from json import load
                metadata = load(f)
            self._update_metadata_tree_with_path_hierarchy(
                metadata, meta_info[1], meta_info[2])

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
        combined_parser.metadata = _merge_dicts(parser1.metadata,
                                                parser2.metadata)

    return combined_parser


Parser.combine = _combine
