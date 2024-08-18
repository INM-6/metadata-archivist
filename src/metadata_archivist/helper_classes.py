#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""

Module containing collection of convenience classes internally used.

Authors: Jose V., Matthias K.

"""

from pathlib import Path
from copy import deepcopy
from json import load, dumps
from collections.abc import Iterable
from typing import Optional, Dict, Union, Any

from .logger import _LOG, _is_debug


class _FormatterCache:
    """
    Convenience class for storing ParserCache objects.
    For each Parser a _ParserCache object is created which will store all parsing results.
    Iteration is possible by using dictionary iterator on the actual cache storage.

    Attributes are only used internally.

    Methods:
        add: add new ParserCache using Parser name.
        drop: drop ParserCache using Parser name.
        is_empty: empty test for internal dictionary containing ParserCaches.
    """

    def __init__(self):
        """Constructor for FormatterCache."""
        self._cache = dict()
        self._iterator = None

    def add(self, parser_name: str) -> None:
        """
        Method to add new ParserCache to internal dictionary.

        Arguments:
            parser_name: string name of Parser to create a ParserCache for.
        """
        if parser_name not in self._cache:
            self._cache[parser_name] = _ParserCache()
        else:
            raise KeyError(f"Parser {parser_name} already exists in cache")

    def drop(self, parser_name: str) -> None:
        """
        Method to drop ParserCache from internal dictionary.

        Arguments:
            parser_name: string name of Parser to drop its ParserCache for.
        """
        self._cache.pop(parser_name, None)

    def __getitem__(self, parser_name: str):
        """
        Get operator for internal dictionary using Parser names.

        Arguments:
            parser_name: string name of Parser to fetch from internal dictionary.
        """
        return self._cache[parser_name]

    def __iter__(self):
        """
        Iteration operator.
        Iteration is done by iterating over the storage dictionary.
        """
        self._iterator = iter(self._cache)
        return self

    def __next__(self):
        """
        Next operator.
        When iterating over a dictionary keys are returned,
        here we return the corresponding _ParserCache objects.
        """
        if self._iterator is None:
            raise StopIteration
        return self._cache[next(self._iterator)]

    def is_empty(self):
        """Empty test method for internal ParserCache dictionary."""
        return len(self._cache) == 0


class _ParserCache:
    """
    Convenience class for storing CacheEntry objects.
    For each file parsed by the corresponding parser a CacheEntry object is created.
    Iteration is possible by using list iterator on the actual entry storage.

    Attributes are only used internally.

    Methods:
        add: add new CacheEntry for parsed file.
        is_empty: empty test for internal list containing CacheEntries.
    """

    def __init__(self):
        """Constructor for ParserCache"""
        self._entries = list()
        self._iterator = None

    def add(self, *args):
        """
        Method to add CacheEntry to internal list.

        Arguments are directly passed on to CacheEntry (cf constructor).

        Returns:
            new CacheEntry.
        """
        entry = _CacheEntry(*args)
        self._entries.append(entry)
        return entry

    def __getitem__(self, index: int):
        """
        Get operator for internal list using index.

        Arguments:
            index integer where CacheEntry is located at.

        Returns:
            indexed CacheEntry.
        """
        return self._entries[index]

    def __iter__(self):
        """
        Iteration operator.
        Iteration is done by iterating over the storage dictionary.
        """
        self._iterator = iter(self._entries)
        return self

    def __next__(self):
        """
        Next operator.
        When iterating over a dictionary keys are returned,
        here we return the corresponding _ParserCache objects.
        """
        if self._iterator is None:
            raise StopIteration
        return next(self._iterator)

    def is_empty(self):
        """Empty test method for internal CacheEntry list."""
        return len(self._entries) == 0


class _CacheEntry:
    """
    Convenience class for storing parsing results.
    For each parsed file a _CacheEntry object is created, after parsing, the results can be
    lazily stored and a meta_path is generated or the metadata can be directly stored in the entry.
    If the results are lazily stored then calling load_metadata would load them to memory.

    Attributes:
        explored_path: Path object pointing to root exploration directory. Used to get relative file paths.
        file_path: Path object pointing to parsed file.
        rel_path: file Path relative to explored Path.
        metadata: parsed metadata dictionary.

    Methods:
        load_metadata: returns CachedMetadata, if lazy loading is enabled then loads metadata from self contained meta file.
    """

    def __init__(
        self, explored_path: Path, file_path: Path, metadata: Optional[dict] = None
    ):
        """
        Constructor of CacheEntry.

        Arguments:
            explored_path: Path object pointing to root exploration directory. Used to get relative file paths.
            file_path: Path object pointing to parsed file.
            rel_path: file Path relative to explored Path.
            metadata: parsed metadata dictionary.
        """

        self.explored_path = explored_path
        self.file_path = file_path
        self.rel_path = file_path.relative_to(explored_path)
        self.metadata = metadata
        if metadata is None:
            self.meta_path = Path(str(file_path) + ".meta")
        else:
            self.meta_path = None

    def load_metadata(self) -> dict:
        """
        Loads cached metadata.
        If no cache exists this implies that lazy loading is enabled,
        metadata is loaded then from the self generated meta path.

        Returns:
            self contained parsed metadata dictionary.
        """
        if self.metadata is None:
            if self.meta_path is None:
                raise RuntimeError(
                    "Cache entry does not contain metadata and meta path not found."
                )

            with self.meta_path.open("r") as f:
                self.metadata = load(f)

            if self.metadata is None:
                raise RuntimeError(
                    f"Failed to load metadata {dumps(self, indent=4, default=vars)}"
                )

        return self.metadata


class _ParserIndexes:
    """
    Indexing class for storing different indexes for each Parser:
        index in parsers list.
        index in input file patterns list.
        index in schema properties list.

    Attributes:
        prs_indexes: dictionary of Parser indexes in parsers list.
        ifp_indexes: dictionary of Parser indexes in input file patterns list.
        scp_indexes: dictionary of Parser indexes in schema properties list.

    Methods:
        set_index: stores the index of a Parser in a given list using Parser name.
        get_index: fetches the index of a Parser in a given list using Parser name.
        drop_index: drops the stored index of a Parser in a given list using Parser name.
    """

    def __init__(self) -> None:
        """Constructor of ParserIndexes class."""
        self.prs_indexes = dict()
        self.ifp_indexes = dict()
        self.scp_indexes = dict()

    def _get_storage(self, storage: str) -> dict:
        """
        Internal method for getting specific storage based on storage name string.
        To determine which storage should the index go to:
            'prs' or 'parsers' for parser index list.
            'ifp' or 'input_file_patterns' for input file pattern index list.
            'scp' or 'schema_properties' for schema property list.

        Arguments:
            storage: string name of storage to get.

        Returns:
            selected storage dictionary.
        """

        prs_patterns = ["prs", "parsers"]
        ifp_patterns = ["ifp", "input_file_patterns"]
        scp_patterns = ["scp", "schema_properties"]
        if storage in prs_patterns:
            return self.prs_indexes
        elif storage in ifp_patterns:
            return self.ifp_indexes
        elif storage in scp_patterns:
            return self.scp_indexes

        raise ValueError(
            f"Incorrect value for storage name, got {storage}, accepted {prs_patterns + ifp_patterns + scp_patterns}"
        )

    def set_index(self, parser_name: str, storage: str, index: int) -> None:
        """
        Set index method for selected storage.

        Arguments:
            parser_name: name string of Parser to use as identifier.
            storage: string name of storage to set into.
            index: int index to store.
        """
        self._get_storage(storage)[parser_name] = index

    def get_index(
        self, parser_name: str, storage: Optional[str] = None
    ) -> Union[int, Dict[str, int]]:
        """
        Get index method for all storages.
        If no storage specified, all stored indexes are returned as a dictionary.

        Arguments:
            parser_name: name string of Parser to use as identifier.
            storage: Optional string name of storage to get an index from.

        Returns:
            if no storage provided then returns a dictionary of storage names and index pairs,
            otherwise integer index corresponding to selected storage is returned.
        """
        if storage is None:
            return {
                "prs": self.prs_indexes.get(parser_name),
                "ifp": self.ifp_indexes.get(parser_name),
                "scp": self.scp_indexes.get(parser_name),
            }
        else:
            return self._get_storage(storage)[parser_name]

    def drop_indexes(self, parser_name: str) -> dict:
        """
        Remove method for a Parser in all index storages.

        Arguments:
            parser_name: name string of Parser to use as identifier.

        Returns:
            dictionary of storage names and index pairs corresponding to Parser.
        """
        return {
            "prs": self.prs_indexes.pop(parser_name),
            "ifp": self.ifp_indexes.pop(parser_name),
            "scp": self.scp_indexes.pop(parser_name),
        }


class _SchemaEntry:
    """
    Convenience superset of dictionary class.
    Used to recursively generate nested dictionary structure to serve as an intermediary between schema and metadata file.
    Contains additional context dictionary for a given tree level and the name of the root node.
    For initial root node, no name is defined, however for subsequent nodes there should always be a name.
    Get, set, and iteration access is redirected to internal storage.

    Attributes:
        key: schema key used as entry name.
        context: dictionary containing information of schema properties where entry is created.

    Methods:
        items: returns key value pair item view of entry content.
        is_empty: returns True is entry content is empty.
    """

    def __init__(
        self, key: Optional[str] = None, context: Optional[dict] = None
    ) -> None:
        """
        Constructor for schema entry.

        Arguments:
            key: schema key used as entry name.
            context: dictionary containing information of schema properties where entry is created.
        """

        self.key = key
        self.context = context if context is not None else {}
        self._content = {}
        self._iterator = None

    def __getitem__(self, key) -> Any:
        """Value retrieval method for entry content using key."""
        return self._content[key]

    def __setitem__(self, key, value) -> None:
        """Value insertion method for entry content using key."""
        self._content[key] = value

    def __contains__(self, key) -> bool:
        """Key presence test for entry content."""
        return key in self._content

    def items(self):
        """Entry content items get method."""
        return self._content.items()

    def is_empty(self) -> bool:
        """Entry empty content test."""
        return len(self._content) == 0


class _SchemaInterpreter:
    """
    Functionality class used for interpreting the schema.
    When defining the JSON schema with additional directives,
    the object is cannot be used directly for structuring.
    To this end, this class is used to generate an intermediary structure
    that respects the schema and its directives while being functionally
    usable as a mirror for structuring the final metadata file.

    Attributes:
        structure: root SchemaEntry used for interpretation.
        rules: dictionary of interpretation rules.

    Methods:
        generate: convenience method to generate schema interpretation.
    """

    def __init__(self, schema: dict) -> None:
        """
        Constructor of SchemaInterpreter.

        Arguments:
            schema: dictionary containing schema to interpret.
        """

        if not isinstance(schema, dict):
            raise RuntimeError(f"Incorrect schema used for iterator {schema}")
        if "properties" not in schema or not isinstance(schema["properties"], dict):
            raise RuntimeError(
                f"Incorrect schema structure, root is expected to contain properties dictionary: {schema}"
            )
        if "$defs" not in schema or not isinstance(schema["$defs"], dict):
            raise RuntimeError(
                f"Incorrect schema structure, root is expected to contain $defs dictionary: {schema}"
            )

        self._schema = schema
        self.structure = _SchemaEntry()

        # We load INTERPRETATION_RULES directly in instance to avoid circular importing issues
        from .interpretation_rules import _INTERPRETATION_RULES

        self.rules = deepcopy(_INTERPRETATION_RULES)

    def _interpret_schema(
        self,
        properties: dict,
        _parent_key: Optional[str] = None,
        _relative_root: Optional[_SchemaEntry] = None,
    ):
        """
        Recursive method to explore JSON schema.
        Following the technical assumptions made (cf. README.md/SchemaInterpreter),
        only the properties at the root of the schema are interpreted (recursively so),
        items of the property are of type key[str] -> value[dict|str],
        any other type is currently ignored as NotImplemented feature.
        When interpreting we generate a SchemaEntry with nested tree structure.

        - When processing dictionaries, these can either be simple properties,
        special properties or intermediate structures.
        If the dictionary is a simple property then recursion is called on its contents
        without creating a new branch.
        If the dictionary is a special property then: either it is a composite directive
        e.g. !parsing in which case context is added then the current recursion will
        continue until arriving at a leaf (str) and leaf processing is in charge of using
        the enriched entry. Otherwise, the property indicates a new recursion with additional
        context e.g. patternProperties indicate a new recursion with regular expression file
        matching. However the no new branch is created and the recursion results are added to
        the current branch.
        Any other dictionaries are considered as intermediary structures hence a new branch
        is created and a recursion is done on its contents.
        The previous is the ONLY SCENARIO FOR BRANCHING inside the interpretable data structure.

        - When processing strings, they can be either JSON schema additional information
        in which case it is ignored or they can be additional directives e.g. $ref or !varname
        Both of which are specially processed to enriched the context.

        Arguments:
            properties: dictionary of schema properties to interpret.
            _parent_key: key of parent property where method was called. Recursion variable.
            _relative_root: relative SchemaEntry where method was called. Recursion variable. Defaults to self contained structure.
        """

        if _relative_root is None:
            _relative_root = self.structure

        # For all the properties in the given schema
        for key, val in properties.items():

            # If the key is known as an interpretation rule
            # call the function mapped into the INTERPRETATION_RULE dictionary
            if key in self.rules:
                # This error is only raised if an interpretation rule is found at root of schema properties
                # rules must be defined in individual items of the properties, hence a parent key should
                # always be present.
                if _parent_key is None:
                    if _is_debug():
                        _LOG.debug("current structure: %s", dumps(_relative_root, indent=4, default=vars))
                    raise RuntimeError("Cannot interpret rule without parent key.")
                _relative_root = self.rules[key](
                    self, val, key, _parent_key, _relative_root
                )

            else:
                # Case dict i.e. branch
                if isinstance(val, dict):
                    _relative_root[key] = self._interpret_schema(
                        val,
                        key,
                        _SchemaEntry(key=key, context=deepcopy(_relative_root.context)),
                    )

                # Case str i.e. leaf
                elif isinstance(val, str):
                    _LOG.debug("Ignoring key value pair: (%s: %s)", key, val)

                # Else not-implemented/ignored
                else:
                    if isinstance(val, Iterable):
                        _LOG.debug("Unknown iterable type: %s", str(type(val)))
                        raise NotImplementedError(
                            "Unknown iterable type."
                        )
                    else:
                        _LOG.debug("Ignoring key value pair: (%s: %s)", key, str(val))

        return _relative_root

    def generate(self) -> _SchemaEntry:
        """
        Convenience function to launch interpretation recursion over the schema.
        Results is also internally stored for future access.

        Returns:
            self contained SchemaEntry
        """
        if _is_debug():
            # Passing through dumps for pretty printing,
            # however can be costly, so checking if debug is enabled first
            _LOG.debug("Initial structure: %s", dumps(self._schema, indent=4, default=vars))

        if self.structure.is_empty():
            self.structure = self._interpret_schema(self._schema["properties"])

        if _is_debug():
            # Passing through dumps for pretty printing,
            # however can be costly, so checking if debug is enabled first
            _LOG.debug("Interpreted structure: %s", dumps(self.structure, indent=4, default=vars))

        return self.structure
