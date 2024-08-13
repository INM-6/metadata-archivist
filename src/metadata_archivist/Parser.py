#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""

Parser abstract class to parse metadata from file.
To be specialized by custom parser made by users.

exports:
    AParser

Authors: Jose V., Matthias K.

"""

from pathlib import Path
from copy import deepcopy
from abc import ABC, abstractmethod

from .Logger import _LOG
from .helper_functions import _merge_dicts, _filter_dict, _deep_get_from_schema, _pattern_parts_match

# Try to load jsonschema package components for validation
# In case of failure, validation is disabled
try:
    from jsonschema import validate, ValidationError
    _DO_VALIDATE = True
except:
    _LOG.warning("JSONSchema package not found, disabling validation.")
    def validate(instance: dict, schema: dict):
        return True
    ValidationError = Exception
    _DO_VALIDATE = False


class AParser(ABC):
    """
    Base parser class.
    Multiple Parsers can "look for" the same metadata,
    but will differ on the file they process and how.

    Parsers use schemas to validate the data they process.
    The parsing process and returned structure defines the schema.

    Attributes:
        input_file_pattern: regex pattern of name of files to parse.
        schema: Parser schema used to validate parsed metadata.
        name: unique name string used for Formatter schema handling.
        parsed_metadata: dictionary contained parsed metadata.
        validate_output: control boolean to enable parsing output validation against self contained schema.

    Methods:
        parse: Abstract method for file parsing, user defined.
        run_validation: If jsonschema package is available, validates self contained parsed metadata against self contained schema.
    """

    def __init__(self, name: str, input_file_pattern: str, schema: dict, validate_output: bool = True) -> None:
        """
        Constructor for base abstract AParser.

        Arguments:
            name: string name of Parser. Should be unique across parsers used.
            input_file_pattern: regexp string describing pattern of input file.
            schema: dictionary describing parsed output.
            validate_output: control boolean to enable parsing output validation against self contained schema.
        """

        super().__init__()
        self._name = name
        self._input_file_pattern = input_file_pattern
        self._schema = schema
        self.validate_output = _DO_VALIDATE and validate_output

        self._formatters = []  # For two way relationship (Formatter - Parser) update handling

        self.parsed_metadata = {}

    @property
    def input_file_pattern(self) -> str:
        """Returns Parser input file pattern (str)."""
        return self._input_file_pattern

    @input_file_pattern.setter
    def input_file_pattern(self, pattern: str) -> None:
        """
        Sets Parser input file pattern (str).
        Triggers parsers update.
        """
        self._input_file_pattern = pattern
        self._update_formatters()

    @property
    def schema(self) -> dict:
        """Returns Parser schema (dict)."""
        return self._schema

    @schema.setter
    def schema(self, schema: dict) -> None:
        """
        Sets Parser schema (dict).
        Triggers formatter update.
        """
        self._schema = schema
        self._update_formatters()

    @property
    def name(self) -> str:
        """Returns Parser name (str)."""
        return self._name

    @name.setter
    def name(self, name: str) -> None:
        """
        Sets Parser name (str).
        Due to indexing mechanism of Formatter,
        name change requires removing and re-adding.
        """
        self._remove_from_formatters()
        self._name = name
        self._add_to_formatters()

    def _get_reference(self) -> str:
        """
        Returns unique reference for Parser.
        """
        return f"#/$defs/{self._name}"  # str(self.__hash__()) for more complex cases

    def _add_to_formatters(self) -> None:
        """Reverse add of related parsers."""
        for f in self._formatters:
            f.add_parser(self)

    def _update_formatters(self) -> None:
        """Reverse update of related parsers."""
        for f in self._formatters:
            f.update_parser(self)

    def _remove_from_formatters(self) -> None:
        """Reverse remove of related parsers."""
        for f in self._formatters:
            f.remove_parser(self)

    def _parse_file(self, file_path: Path) -> dict:
        """
        Internal wrapper for the user defined parsing method,
        takes care of prior file checking and applies validate on parsed metadata.

        Arguments:
            file_path: Path object to file to be parsed.

        Returns:
            dictionary of parsed metadata.
        """

        if not file_path.is_file():
            raise RuntimeError(
                f'The input file {file_path.name} is incorrect')
 
        pattern = self.input_file_pattern.split("/")
        pattern.reverse()
        if _pattern_parts_match(pattern, list(reversed(file_path.parts))):
            self.parsed_metadata = self.parse(file_path)
        self.run_validation()

        return self.parsed_metadata

    @abstractmethod
    def parse(self, file_path: Path) -> dict:
        """
        Main method of the Parser class used to parse metadata from the files.
        To be defined by custom user classes.
        Must return JSON objects to be able to validate.
        Result is stored in parsed_metadata  and returned as value.
        """

    def run_validation(self) -> None:
        """
        Method used to validate parsed metadata.
        Can only be run if jsonschema package is present in python environment.
        """

        if self.validate_output:
            try:
                validate(instance=self.parsed_metadata, schema=self.schema)
            except ValidationError as e:
                # TODO: better exception mechanism
                _LOG.warning(e.message)

    # Considering the name of the Parser as unique then we can use
    # the name property for equality/hashing
    def __eq__(self, other) -> bool:
        """Class instance equality method, returns true if instance name is equal."""
        return self._name == other._name if isinstance(other, type(self)) else False

    def __ne__(self, other) -> bool:
        """Class instance inequality method, returns true if instance equality is false."""
        return not self.__eq__(other)

    def __hash__(self) -> int:
        """Class instance hashing method, returns hash of instance name."""
        return hash(self._name)

    def _filter_metadata(self, metadata: dict, keys: list, **kwargs) -> dict:
        """
        WIP
        Filters parsed metadata by providing keys corresponding to metadata attributes.
        If metadata is a nested dictionary then keys can be shaped as UNIX paths,
        where each path part corresponding to a nested attribute.

        Arguments:
            metadata: dictionary to filter.
            keys: list of keys to filter with.

        Returns:
            filtered dictionary.
        """

        if 'add_description' in kwargs.keys():
            add_description = kwargs['add_description']
        else:
            add_description = False
        if 'add_type' in kwargs.keys():
            add_type = kwargs['add_type']
        else:
            add_type = False
        metadata_copy = deepcopy(metadata)
        if keys is None:
            return metadata_copy
        else:
            new_dict = {}
            for k in keys:
                _LOG.debug(f"filtering key: {k}")
                new_dict = _merge_dicts(
                    new_dict, _filter_dict(metadata, k.split('/')))
            if add_description or add_type:
                self._add_info_from_schema(new_dict, add_description, add_type)
            return new_dict

    def _add_info_from_schema(self,
                              metadata,
                              add_description,
                              add_type,
                              key_list=[]):
        """
        WIP
        Adds additional information from input schema to parsed metadata inplace.

        Arguments:
            metadata: dictionary to add information to.
            add_description: control boolean to enable addition of description information.
            add_type: control boolean to enable addition of type information.
            key_list: recursion list containing visited dictionary keys.
        """

        for kk in metadata.keys():
            if isinstance(metadata[kk], dict):
                self._add_info_from_schema(metadata[kk], add_description,
                                           add_type, key_list + [kk])
            else:
                val = metadata[kk]
                metadata[kk] = {'value': val}
                print(key_list + [kk])
                schem_entry = _deep_get_from_schema(
                    deepcopy(self._schema['properties']), key_list + [kk])
                if schem_entry is None and 'additionalProperties' in self._schema.keys(
                ):
                    schem_entry = _deep_get_from_schema(
                        deepcopy(self._schema['additionalProperties']), *key_list)
                if schem_entry is None and 'patternProperties' in self._schema.keys(
                ):
                    schem_entry = _deep_get_from_schema(
                        deepcopy(self._schema['patternProperties']), *key_list)
                print(schem_entry)
                if schem_entry is not None:
                    if add_description and 'description' in schem_entry.keys():
                        metadata[kk].update(
                            {'description': schem_entry['description']})
                    if add_type and 'type' in schem_entry.keys():
                        metadata[kk].update({'type': schem_entry['type']})
