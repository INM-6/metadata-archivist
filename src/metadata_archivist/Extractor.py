#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""

Extractor abstract class to get metadata from file.
To be specialized by custom extractors made by users.

Authors: Jose V., Matthias K.

"""

import re
import abc  # Abstract class base infrastructure

import jsonschema  # to validate extracted data

from pathlib import Path
from typing import NoReturn

from .Logger import LOG
from .helper_functions import _merge_dicts


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
    _parsers = []  # For two way relationship update handling

    # Immutable
    _name: str  # name of the extractor

    # Public
    extracted_metadata: dict  # JSON object as dict to be used as cache

    def __init__(self, name: str, input_file_pattern: str,
                 schema: dict) -> None:
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
    def id(self) -> str:
        """
        Returns unique identifier for extractor
        """
        return self._name  # str(self.__hash__()) for more complex cases

    @id.setter
    def id(self, _) -> NoReturn:
        """
        Forbidden setter for id attribute.
        (pythonic indirection for protected attributes)
        """
        raise AttributeError(
            "Cannot manually set the id.\nThe id of an Extractor is a computed property based on the Extractor attributes"
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
                f'The input file {file_path.name} is incorrect')
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

    def filter_metadata(self, metadata: dict, keys: list, **kwargs):
        if 'add_description' in kwargs.keys():
            add_description = kwargs['add_description']
        else:
            add_description = False
        if 'add_type' in kwargs.keys():
            add_type = kwargs['add_type']
        else:
            add_type = False
        metadata_copy = metadata.copy()
        if keys is None:
            return metadata_copy
        else:
            new_dict = {}
            for k in keys:
                LOG.debug(k)
                new_dict = _merge_dicts(
                    new_dict, self._filter_dict(metadata, k.split('/')))
            if add_description or add_type:
                self._add_info_from_schema(new_dict, add_description, add_type)
            return new_dict

    def _filter_dict(self,
                     metadata: dict,
                     filter: list,
                     level: int = 0) -> dict:
        """filter a dict using a filter (ordered list of re's)

        :param metadata: dict to filter
        :param filter: a list of re's
        :param level: index of re in filter to use
        :returns: a filtered dict

        """
        new_dict = {}
        if level >= len(filter):
            new_dict = metadata.copy()
        else:
            for k in metadata.keys():
                if re.fullmatch(filter[level], k):
                    if isinstance(metadata[k], dict):
                        new_dict[k] = self._filter_dict(
                            metadata[k], filter, level + 1)
                    else:
                        new_dict[k] = metadata[k]
        return new_dict

    def _add_info_from_schema(self,
                              metadata,
                              add_description,
                              add_type,
                              key_list=[]):
        """TODO: add a function that enriches the metadata with information from the schema
        NOT WORKING YET

        :returns: None

        """
        for kk in metadata.keys():
            if isinstance(metadata[kk], dict):
                self._add_info_from_schema(metadata[kk], add_description,
                                           add_type, key_list + [kk])
            else:
                val = metadata[kk]
                metadata[kk] = {'value': val}
                print(key_list + [kk])
                schem_entry = deep_get_from_schema(
                    self._schema['properties'].copy(), key_list + [kk])
                if schem_entry is None and 'additionalProperties' in self._schema.keys(
                ):
                    schem_entry = deep_get_from_schema(
                        self._schema['additionalProperties'].copy(), *key_list)
                if schem_entry is None and 'patternProperties' in self._schema.keys(
                ):
                    schem_entry = deep_get_from_schema(
                        self._schema['patternProperties'].copy(), *key_list)
                print(schem_entry)
                if schem_entry is not None:
                    if add_description and 'description' in schem_entry.keys():
                        metadata[kk].update(
                            {'description': schem_entry['description']})
                    if add_type and 'type' in schem_entry.keys():
                        metadata[kk].update({'type': schem_entry['type']})


def deep_get_from_schema(schema, keys: list):
    # if len(keys) > 0:
    k = keys.pop(0)
    if len(keys) > 0:
        if k in schema.keys():
            deep_get_from_schema(schema[k], keys)
        elif 'properties' in schema.keys() and keys[0] in schema['properties']:
            deep_get_from_schema(schema['properties'][k], keys)
        elif 'additionalProperties' in schema.keys(
        ) and keys[0] in schema['additionalProperties']:
            deep_get_from_schema(schema['additionalProperties'], keys)
        elif 'additionalProperties' in schema.keys(
        ) and 'properties' in schema['additionalProperties'] and keys[
                0] in schema['additionalProperties']['properties']:
            deep_get_from_schema(schema['additionalProperties']['properties'],
                                 keys)
        elif 'patternProperties' in schema.keys() and any(
                re.fullmatch(x, k)
                for x in schema['patternProperties'].keys()):
            for kk in schema['patternProperties'].keys():
                if re.fullmatch(kk, k):
                    deep_get_from_schema(schema['patternProperties'][kk], keys)
                    break
    else:
        print(schema[k])
        return schema[k]
