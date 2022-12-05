'''
Abstract classes for setting up Extractors
'''

import sys

from abc import ABC, abstractmethod
from pathlib import Path
from re import pattern
from io import IOBase


class AExtractor(ABC):
    """interface for a Extractor class
    a extractor returns metadata from 1 file
    """

    @abstractmethod
    @property
    def input_file_pattern(self) -> pattern:
        """retuns a re.pattern describing input files"""

    @property
    def schema(self):
        """return json schema of output"""
        return self._schema

    @abstractmethod
    def extract(self, file_path: Path, data: IOBase) -> dict:
        """
        extract data from files and returns the metadata as a dict

        :param file_path: path to a file

        """


class AParser(ABC):
    """interface for a Parser
    A Parser creates a metadata object (dict) that
    is further described by a json schema.
    The json schema describing the metadata object is build using
    the schema of the Parser and the schema's provided by the extractors

    all metadata for a node is put at a corresponding node in the
    metadata dict tree. the directories in the metadata archive (lake)
    are used for structering the tree
    """

    @property
    def input_files_pattern(self) -> list[pattern]:
        """
        return list of re.pattern for input files, given by the extractors
        The re.pattern are then used by the decompressor to select files
        """
        return self._input_files_pattern

    @property
    def extractors(self) -> list[AExtractor]:
        """return list of extractors"""
        return self._extractors

    @property
    def schema(self):
        """return json schema of output"""
        return self._schema

    @property
    def metadata(self) -> dict:
        """return the metadata object"""
        return self._metadata

    def update_metadata_tree(self, file_path: Path) -> None:
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

    def deep_set(self, metadata: dict, value, tree: list):
        if len(tree) == 1:
            metadata[tree[0]] = value
        else:
            self.deep_set(metadata[tree[-1]], value, tree[:-1])

    def parse(self, file_path: Path, data: IOBase) -> None:
        """add metadata from input file to metadata object
        usually by sending calling all extract's linked to the file-name or regexp of file name

        :param file_path: path to file (Path)

        """

        self.update_metadata_tree(file_path)

        for extractor in self.extractors:
            if extractor.input_file_pattern.match(file_path.name):
                data.seek(0)
                metadata = extractor.extract(file_path.name, data)
                self.deep_set(self.metadata, metadata, file_path)
