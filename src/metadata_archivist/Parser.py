#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""

Metadata base parser class.
To be specialized by custom parsers made by users.
Tested with Python 3.8.10
Author: Jose V., Kelbling, M.

"""

import jsonschema  # to validate extracted data
import json
import sys
import re

import abc  # Abstract class base infrastructure
from pathlib import Path
from io import IOBase
from typing import Optional, Literal, Union
from .util import get_structured_metadata

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
    name: str  # name of the extractor
    ref: str  # the ref string usually: '#/$defs/{self.name}'
    _input_file_pattern: str
    _extracted_metadata: dict  # JSON object as dict to be used as cache
    schema: dict  # JSON schema as dict

    # TODO: Think about whether we stay with pure OOP getter and setter functions
    # or we go with the pythonic way of directly accessing members where possible
    @property
    def input_file_pattern(self):
        """retuns a re.pattern describing input files"""
        return self._input_file_pattern

    @input_file_pattern.setter
    def input_file_pattern(self, pattern: str):
        """set pattern of input file"""
        self._input_file_pattern = pattern

    # TODO: maybe we want a setter/getter for schema and add a schema validation check on the setter.
    # then we could do the vallidations of the metadata without each time checking the validity of the
    # schema
    # @property
    # def schema(self):
    #     """return json schema of output"""
    #     return self.schema

    # @schema.setter
    # def schema(self, schema: dict):
    #     """set schema"""
    #     self.schema = schema

    def extract_metadata_from_file(
            self, file_path: Path,
            data: IOBase) -> dict:  # JSON object as dict
        """
        Wrapper for the user defined _extract method,
        takes care of prior file checking and applies validate
        on extracted metadata
        """
        pattern = self._input_file_pattern
        if pattern[0] == '*':
            pattern = '.' + pattern
        if not re.fullmatch(pattern, file_path.name):
            raise RuntimeError(
                f'The inputfile {file_path.name} does not match the extractors pattern: {self._input_file_pattern}'
            )
        elif not file_path.is_file():
            raise RuntimeError(
                f'The inputfile {file_path.name} does not exist!')
        else:
            self._extracted_metadata = self.extract(data)
        self.validate()

        return self._extracted_metadata

    # TODO: Think about lazy storing the extractor results in files (in case memory is information)
    # and load it later when filtering/reshaping with schema

    @abc.abstractmethod
    def extract(self, data: IOBase) -> dict:
        """
        Main method of the Extractor class
        used to "extract" metadata from the files.
        To be defined by custom user classes.
        Must return JSON objects to be able to validate.
        Result is stored in _extracted_metadata  and returned as value
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
            jsonschema.validate(self._extracted_metadata, schema=self.schema)
            return True
        except jsonschema.ValidationError as e:
            # TODO: better exception mechanism
            print(e.message)

        return False

    def __eq__(self, other):
        return other and self._input_file_pattern == other._input_file_pattern and self.schema == other.schema

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash((self._input_file_pattern, self.schema))


class Parser():
    """Parser
    A Parser creates a metadata object (dict) that
    is further described by a json schema.
    The json schema describing the metadata object is build using
    the schema of the Parser and the schema's provided by the extractors

    all metadata for a node is put at a corresponding node in the
    metadata dict tree. the directories in the metadata archive (lake)
    are used for structering the tree
    """

    def __init__(self,
                 extractors: Optional[list[AExtractor]] = None,
                 metadata_tree: Optional[Literal[
                     'from_dir_tree', 'from_schema']] = 'from_schema',
                 schema: Optional[Union[str, Path, dict]] = None) -> None:
        self._extractors = []
        self._input_file_patterns = []
        self._metadata = {}
        if schema is None:
            self.schema = DEFAULT_PARSER_SCHEMA
        elif isinstance(schema, (str, Path)):
            with open(schema) as f:
                self.schema = json.load(f)
        elif isinstance(schema, dict):
            # ToDo: Validate the dict as schema
            self.schema = schema
        self.decompress_path = Path('./')
        self.metadata_tree = metadata_tree

        if extractors is not None:
            for e in extractors:
                self.add_extractor(e)

    @property
    def input_file_patterns(self) -> list[str]:
        """
        return list of re.pattern for input files, given by the extractors
        The re.pattern are then used by the decompressor to select files
        """
        return self._input_file_patterns

    @property
    def extractors(self) -> list[AExtractor]:
        """return list of extractors"""
        return self._extractors

    def print_schema(self):
        print(json.dumps(self.schema, indent=2))

    def add_extractor(self, extractor: AExtractor):
        # TODO: Handle duplicate extractors?
        self._extractors.append(extractor)
        self._input_file_patterns.append(extractor.input_file_pattern)
        self._extend_json_schema(extractor)

    def _extend_json_schema(self, extractor):
        if "$defs" not in self.schema.keys():
            self.schema["$defs"] = {}
        # TODO: Will generate pointer issue if extractor schema is redefined
        # -> Create two way relationships with update triggers
        if extractor.name not in self.schema["$defs"]:
            self.schema["$defs"][extractor.name] = extractor.schema
        if 'node' in self.schema["$defs"]:
            self.schema["$defs"]["node"]["properties"]["anyOf"].append(
                {"$ref": f"#/$defs/{extractor.name}"})
        # TODO: we should probably create an attachement and dettachement procedures
        # to update schema with addition and removal of extractors

    @property
    def metadata(self) -> dict:
        """return the metadata object"""
        return self._metadata

    def _update_metadata_tree(self, rel_file_path: Path) -> None:
        """update tree structure of metadata dict with file path

        :param file_path: path to a file

        """
        iter_dict = self.metadata
        for pp in rel_file_path.parts[:-1]:
            if pp not in iter_dict:
                iter_dict[pp] = {}
                iter_dict = iter_dict[pp]
            elif pp in iter_dict and not isinstance(iter_dict[pp], dict):
                print(
                    f'Trying to created nested structure in metadata object failed: {pp}'
                )
                sys.exit()

    def _deep_set_dict_from_path(self, metadata: dict, value, path: Path):
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
        """add metadata from input file to metadata object
        usually by sending calling all extract's linked to the file-name or regexp of file name

        TODO: Think about optimization  for multiple files

        :param file_path: path to file (Path)

        """

        rel_file_path = file_path.relative_to(self.decompress_path)
        if self.metadata_tree == 'from_dir_tree':
            self._update_metadata_tree(rel_file_path)

        # TODO: Change to explore pre compiled list of file from matches
        # TODO: change to pass only file paths and extractor will handle file opening.
        with file_path.open("r") as f:
            for extractor in self.extractors:
                pattern = extractor.input_file_pattern
                if pattern[0] == '*':
                    pattern = '.' + pattern
                if re.fullmatch(pattern, file_path.name):
                    f.seek(0)
                    metadata = extractor.extract_metadata_from_file(
                        file_path, f)
                    if self.metadata_tree == 'from_schema':
                        metadata = get_structured_metadata(
                            self.schema, extractor.ref, metadata)
                        self._deep_set_dict(self.metadata, metadata)
                    # TODO: The metadata tree should be compiled/merged with the Parser schema
                    # We should think if this is to be done instead of the path tree structure
                    # or do it afterwards through another mechanism
                    #   ->  Think about reshaping/filtering function for dictionaries using schemas
                    #       add bool condition to swtich between directory hierarchy for metadata objects
                    #            or schema hierarchy
                    #       add linking between extracted metadata object properties through schema keywords
                    #           -> cf mattermost chat
                    else:
                        self._deep_set_dict_from_path(self.metadata, metadata,
                                                      rel_file_path)
