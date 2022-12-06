#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""

Metadata base parser class.
To be specialized by custom parsers made by users.
Tested with Python 3.8.10
Author: Jose V., Kelbling, M.

"""

import jsonschema  # to validate extracted data
import sys
import re

import abc  # Abstract class base infrastructure
from pathlib import Path
from io import IOBase
from typing import Optional


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
    _input_file_pattern: str
    _extracted_metadata: dict  # JSON object as dict to be used as cache
    _schema: dict  # JSON schema as dict

    @property
    def input_file_pattern(self):
        """retuns a re.pattern describing input files"""
        return self._input_file_pattern

    @input_file_pattern.setter
    def input_file_pattern(self, pattern: str):
        """set pattern of input file"""
        self._input_file_pattern = pattern

    @property
    def schema(self):
        """return json schema of output"""
        return self._schema

    @schema.setter
    def schema(self, schema: dict):
        """set schema"""
        self._schema = schema

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
            jsonschema.validate(self._extracted_metadata, schema=self._schema)
            return True
        except jsonschema.ValidationError as e:
            # TODO: better exception mechanism
            print(e.message)

        return False

    def __eq__(self, other):
        return other and self._input_file_pattern == other._input_file_pattern and self._schema == other._schema

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash((self._input_file_pattern, self._schema))


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
                 schema: dict,
                 extractors: Optional[list[AExtractor]] = None) -> None:
        self._extractors = []
        self._schema = schema
        self._input_file_pattern = []
        self._metadata = {}

        if extractors is not None:
            for e in extractors:
                self.add_extractor(e)

    @property
    def input_file_pattern(self) -> list[str]:
        """
        return list of re.pattern for input files, given by the extractors
        The re.pattern are then used by the decompressor to select files
        """
        return self._input_file_pattern

    @property
    def extractors(self) -> list[AExtractor]:
        """return list of extractors"""
        return self._extractors

    def add_extractor(self, extractor: AExtractor):
        self._extractors.append(extractor)
        self._input_file_pattern.append(extractor.input_file_pattern)
        self._extend_json_schema(extractor.schema)

    @property
    def schema(self):
        """return json schema of output"""
        return self._schema

    def _extend_json_schema(self, schema):
        print('some sophisticated method is missing')

    @property
    def metadata(self) -> dict:
        """return the metadata object"""
        return self._metadata

    def _update_metadata_tree(self, file_path: Path) -> None:
        """update tree structure of metadata dict with file path

        :param file_path: path to a file

        """
        iter_dict = self.metadata
        for pp in file_path.parts[:-1]:
            if pp not in iter_dict:
                iter_dict[pp] = {}
                iter_dict = iter_dict[pp]
            elif pp in iter_dict and not isinstance(iter_dict[pp], dict):
                print(
                    f'Trying to created nested structure in metadata object failed: {pp}'
                )
                sys.exit()

    def _deep_set(self, metadata: dict, value, tree: list):
        if len(tree) == 1:
            metadata[tree[0]] = value
        else:
            self._deep_set(metadata[tree[0]], value, tree[1:])

    def parse_file(self, file_path: Path) -> None:
        """add metadata from input file to metadata object
        usually by sending calling all extract's linked to the file-name or regexp of file name

        :param file_path: path to file (Path)

        """

        self._update_metadata_tree(file_path)

        with file_path.open("r") as f:
            for extractor in self.extractors:
                pattern = extractor.input_file_pattern
                if pattern[0] == '*':
                    pattern = '.' + pattern
                if re.fullmatch(pattern, file_path.name):
                    f.seek(0)
                    metadata = extractor.extract_metadata_from_file(
                        file_path, f)
                    self._deep_set(self.metadata, metadata,
                                   list(file_path.parts))
