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
from typing import TYPE_CHECKING
from abc import ABC, abstractmethod

from metadata_archivist.logger import LOG
from metadata_archivist.helper_functions import pattern_parts_match

if TYPE_CHECKING:
    from metadata_archivist.formatter import Formatter

# Try to load jsonschema package components for validation
# In case of failure, validation is disabled
try:
    from jsonschema import validate, ValidationError

    _DO_VALIDATE = True

except ImportError:
    LOG.warning("JSONSchema package not found, disabling validation.")

    def validate(*args, **kwargs) -> bool:
        """Mock validate method for compatibility. Returns True."""
        return True

    ValidationError = ValueError
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
        validate_output: control boolean to enable parsing output validation against self contained schema.

    Methods:
        register_formatter: method to add a Formatter instance to known list. Used for two way instance updating.
        remove_formatter: method to remove a Formatter instance from known list.
        run_parsing: wrapper around parse method for additional checks and automated validation.
        parse: Abstract method for file parsing, user defined.
        run_validation: If jsonschema package is available, validates self contained parsed metadata against self contained schema.
    """

    def __init__(
        self,
        name: str,
        input_file_pattern: str,
        schema: dict,
        validate_output: bool = True,
    ) -> None:
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

        # For two way relationship (Formatter - Parser) update handling
        self._formatters = []

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

    def get_reference(self) -> str:
        """Returns unique reference for Parser."""
        return f"#/$defs/{self._name}"  # str(self.__hash__()) for more complex cases

    def register_formatter(self, formatter: "Formatter") -> None:
        """
        Appends a formatter to self contained formatters list.

        Arguments:
            formatter: Formatter instance to append.
        """
        self._formatters.append(formatter)

    def remove_formatter(self, formatter: "Formatter") -> None:
        """
        Removes a formatter from self contained formatters list.

        Arguments:
            formatter: Formatter instance to remove.
        """
        self._formatters.remove(formatter)

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

    def run_parser(self, file_path: Path) -> dict:
        """
        Internal wrapper for the user defined parsing method,
        takes care of prior file checking and applies validate on parsed metadata.

        Arguments:
            file_path: Path object to file to be parsed.

        Returns:
            dictionary of parsed metadata.
        """

        if not file_path.is_file():
            LOG.debug("Path '%s'", str(file_path))
            raise RuntimeError("Given path does not point to file.")

        pattern = self.input_file_pattern.split("/")
        pattern.reverse()
        if pattern_parts_match(pattern, list(reversed(file_path.parts))):
            parsed_metadata = self.parse(file_path)
            self.run_validation(parsed_metadata)

        return parsed_metadata

    @abstractmethod
    def parse(self, file_path: Path) -> dict:
        """
        Main method of the Parser class used to parse metadata from the files.
        To be defined by custom user classes.
        Must return JSON objects to be able to validate.
        Result is stored in parsed_metadata  and returned as value.
        """

    def run_validation(self, metadata) -> None:
        """
        Method used to validate parsed metadata.
        Can only be run if jsonschema package is present in python environment.

        Arguments:
            metadata: metadata dictionary to validate.
        """

        if self.validate_output:
            try:
                validate(instance=metadata, schema=self.schema)
            except ValidationError as e:
                # TODO: better exception mechanism
                LOG.warning(e.message)

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
