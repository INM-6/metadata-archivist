#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""

Module containing collection of convenience classes internally used.

exports:
    CacheEntry: Cache of metadata entry generated from Parser output.
    ParserCache: Cache for metadata caches from all outputs of a Parser.
    FormatterCache: Cache for ParserCaches generated for all Parsers of a Formatter.
    ParserIndexes: Wrapper for dictionaries containing indexes of parsers in Formatter internal structure.
    SchemaEntry: Class containing context rich schema entry. Generated from schema interpretation.
    SchemaInterpreter: Class orchestrating schema interpretation and generation of context rich entries.

Authors: Jose V., Matthias K.

"""

from json import dumps
from pathlib import Path
from hashlib import sha3_256
from hmac import new, compare_digest
from typing import Optional, Dict, Union, Any
from collections.abc import Iterator, ItemsView
from pickle import loads as p_loads, dumps as p_dumps, HIGHEST_PROTOCOL


from metadata_archivist.logger import LOG, is_debug
from metadata_archivist.helper_functions import merge_dicts, IGNORED_ITERABLE_KEYWORDS
from metadata_archivist.interpretation_rules import (
    INTERPRETATION_RULES,
    register_interpretation_rule,
)


class CacheEntry:
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
        load_metadata: returns CachedMetadata,
                        if lazy loading is enabled then loads metadata from self contained meta file.
    """

    def __init__(
        self, explored_path: Path, file_path: Path, metadata: Optional[dict] = None
    ) -> None:
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
        self.meta_path = Path(str(file_path) + ".meta.pkl")
        self._digest = None

    def load_metadata(self, key: bytes) -> dict:
        """
        Loads cached metadata.
        If no cache exists this implies that lazy loading is enabled,
        metadata is loaded then from the self generated meta path.

        Arguments:
            key: bytes key used to secure pickled file.

        Returns:
            self contained parsed metadata dictionary.
        """

        if self.metadata is None:
            if self._digest is None:
                if is_debug():
                    LOG.debug("CacheEntry = %s", dumps(self, indent=4, default=vars))
                raise RuntimeError("Metadata has not been cached yet.")

            with self.meta_path.open("rb", encoding=None) as f:
                bytes_read = f.read()
                new_digest = new(key, bytes_read, sha3_256).hexdigest()
                if compare_digest(self._digest, new_digest):
                    self.metadata = p_loads(bytes_read)
                else:
                    raise ValueError("Encoded pickle has been tampered with.")

            if self.metadata is None:
                if is_debug():
                    LOG.debug("CacheEntry = %s", dumps(self, indent=4, default=vars))
                raise RuntimeError("Failed to load metadata from CacheEntry.")

        return self.metadata

    def save_metadata(self, metadata: dict, key: bytes, overwrite: bool = True) -> None:
        """
        Saves metadata to file and releases object from memory.

        Arguments:
            metadata: dictionary to save.
            key: bytes key used to secure pickled file.
            overwrite_meta_files : control boolean to enable overwriting of lazy load cache files.
        """

        if self.meta_path.exists():
            if overwrite:
                LOG.warning(
                    "Meta file %s exists, overwriting.",
                    str(self.meta_path),
                )
            else:
                LOG.debug("Meta file path '%s'", str(self.meta_path))
                raise FileExistsError(
                    "Unable to save parsed metadata; overwriting not allowed."
                )

        pickle_dump = p_dumps(metadata, protocol=HIGHEST_PROTOCOL)
        self._digest = new(key, pickle_dump, sha3_256).hexdigest()

        with self.meta_path.open("wb", encoding=None) as f:
            f.write(pickle_dump)

        del metadata


class ParserCache:
    """
    Convenience class for storing CacheEntry objects.
    For each file parsed by the corresponding parser a CacheEntry object is created.
    Iteration is possible by using list iterator on the actual entry storage.

    Attributes are only used internally.

    Methods:
        add: add new CacheEntry for parsed file.
        is_empty: empty test for internal list containing CacheEntries.
    """

    def __init__(self) -> None:
        """Constructor for ParserCache"""
        self._entries = []
        self._iterator = None

    def add(self, *args) -> CacheEntry:
        """
        Method to add CacheEntry to internal list.

        Arguments are directly passed on to CacheEntry (cf constructor).

        Returns:
            new CacheEntry.
        """
        entry = CacheEntry(*args)
        self._entries.append(entry)
        return entry

    def __getitem__(self, index: int) -> CacheEntry:
        """
        Get operator for internal list using index.

        Arguments:
            index integer where CacheEntry is located at.

        Returns:
            indexed CacheEntry.
        """
        return self._entries[index]

    def __iter__(self) -> Iterator[CacheEntry]:
        """
        Iteration operator.
        Iteration is done by iterating over the storage dictionary.
        """
        self._iterator = iter(self._entries)
        return self

    def __next__(self) -> CacheEntry:
        """
        Next operator.
        When iterating over a dictionary keys are returned,
        here we return the corresponding _ParserCache objects.
        """
        if self._iterator is None:
            raise StopIteration
        return next(self._iterator)

    def is_empty(self) -> bool:
        """Empty test method for internal CacheEntry list."""
        return len(self._entries) == 0


class FormatterCache:
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

    def __init__(self) -> None:
        """Constructor for FormatterCache."""
        self._cache = {}
        self._iterator = None

    def add(self, parser_name: str) -> None:
        """
        Method to add new ParserCache to internal dictionary.

        Arguments:
            parser_name: string name of Parser to create a ParserCache for.
        """
        if parser_name not in self._cache:
            self._cache[parser_name] = ParserCache()
        else:
            LOG.debug("Parser name '%s'", parser_name)
            raise KeyError("Parser already exists in cache.")

    def drop(self, parser_name: str) -> None:
        """
        Method to drop ParserCache from internal dictionary.

        Arguments:
            parser_name: string name of Parser to drop its ParserCache for.
        """
        self._cache.pop(parser_name)

    def __getitem__(self, parser_name: str) -> ParserCache:
        """
        Get operator for internal dictionary using Parser names.

        Arguments:
            parser_name: string name of Parser to fetch from internal dictionary.
        """
        return self._cache[parser_name]

    def __iter__(self) -> Iterator[ParserCache]:
        """
        Iteration operator.
        Iteration is done by iterating over the storage dictionary.
        """
        self._iterator = iter(self._cache)
        return self

    def __next__(self) -> ParserCache:
        """
        Next operator.
        When iterating over a dictionary keys are returned,
        here we return the corresponding _ParserCache objects.
        """
        if self._iterator is None:
            raise StopIteration
        return self._cache[next(self._iterator)]

    def is_empty(self) -> bool:
        """Empty test method for internal ParserCache dictionary."""
        return len(self._cache) == 0


class ParserIndexes:
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
        self._prs_indexes = {}
        self._ifp_indexes = {}
        self._scp_indexes = {}

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
            return self._prs_indexes
        if storage in ifp_patterns:
            return self._ifp_indexes
        if storage in scp_patterns:
            return self._scp_indexes

        LOG.debug(
            "storage value '%s' , accepted values '%s'",
            storage,
            str(prs_patterns + ifp_patterns + scp_patterns),
        )
        raise ValueError("Incorrect value for storage name.")

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
                "prs": self._prs_indexes.get(parser_name),
                "ifp": self._ifp_indexes.get(parser_name),
                "scp": self._scp_indexes.get(parser_name),
            }
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
            "prs": self._prs_indexes.pop(parser_name),
            "ifp": self._ifp_indexes.pop(parser_name),
            "scp": self._scp_indexes.pop(parser_name),
        }


class SchemaEntry:
    """
    Convenience superset of dictionary class.
    Container class for nested dictionary structure to serve as an intermediary between schema and metadata file.
    Contains additional context dictionary for a given tree level and the name of the root node.
    For initial root node, no name is defined, however for subsequent nodes there should always be a name.
    Get, set, and iteration access is redirected to internal storage.

    Attributes:
        key: schema key used as entry name.
        key_path: sequence of keys from schema used as entry name. Built by recursion in interpretation.
        context: dictionary containing information of schema properties where entry is created.

    Methods:
        items: returns key value pair item view of entry content.
        is_empty: returns True is entry content is empty.
        inherit: returns a new instance of SchemaEntry with extended attributes.
    """

    def __init__(
        self,
        key: Optional[str] = None,
        key_path: Optional[list] = None,
        context: Optional[dict] = None,
    ) -> None:
        """
        Constructor for schema entry.

        Arguments:
            key: schema key used as entry name.
            context: dictionary containing information of schema properties where entry is created.
        """

        self.key = key
        self.key_path = key_path if key_path is not None else []
        self.context = context if context is not None else {}
        self._content = {}
        self._iterator = None

    def __getitem__(self, key: str) -> Any:
        """Value retrieval method for entry content using key."""
        return self._content[key]

    def __setitem__(self, key: str, value: Any) -> None:
        """Value insertion method for entry content using key."""
        self._content[key] = value

    def __contains__(self, key: str) -> bool:
        """Key presence test for entry content."""
        return key in self._content

    def items(self) -> ItemsView[str, Any]:
        """Entry content items get method."""
        return self._content.items()

    def is_empty(self) -> bool:
        """Entry empty content test."""
        return len(self._content) == 0

    def inherit(
        self, key: str, key_path: Optional[list], context: Optional[dict]
    ) -> "SchemaEntry":
        """Instance inheritance function with attribute extension."""
        return SchemaEntry(
            key=key,
            key_path=self.key_path + key_path,
            context=merge_dicts(context, self.context),
        )


class SchemaInterpreter:
    """
    Functionality class used for interpreting the schema.
    When defining the JSON schema with additional directives,
    the object is cannot be used directly for structuring.
    To this end, this class is used to generate an intermediary structure
    that respects the schema and its directives while being functionally
    usable as a mirror for structuring the final metadata file.

    Attributes:
        schema: dictionary containing schema to interpret.
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
            LOG.debug(
                "schema type '%s' , expected type '%s'", str(type(schema)), str(dict)
            )
            raise TypeError("Incorrect schema used for iterator.")
        if "properties" not in schema or not isinstance(schema["properties"], dict):
            if is_debug():
                LOG.debug("schema = %s", dumps(schema, indent=4, default=vars))
            raise ValueError(
                "Incorrect schema structure, root is expected to contain properties dictionary."
            )
        if "$defs" not in schema or not isinstance(schema["$defs"], dict):
            if is_debug():
                LOG.debug("schema = %s", dumps(schema, indent=4, default=vars))
            raise ValueError(
                "Incorrect schema structure, root is expected to contain $defs dictionary."
            )

        self.schema = schema
        self.structure = SchemaEntry()

    def interpret_schema(
        self,
        properties: dict,
        _parent_key: Optional[str] = None,
        _relative_root: Optional[SchemaEntry] = None,
    ) -> SchemaEntry:
        """
        Recursive method to explore JSON schema.
        Following the technical assumptions made (cf. README.md/SchemaInterpreter),
        only the properties at the root of the schema are interpreted (recursively so),
        items of the property are of type key[str] -> value[dict|literal],
        any other type is currently ignored as NotImplemented feature.
        When interpreting we generate a SchemaEntry with nested tree structure.

        - When processing dictionaries, these can either be simple properties,
        special properties or intermediate structures.
        If the dictionary is a simple property then recursion is called on its contents
        without creating a new branch.
        If the dictionary is a special property then: either it is a composite directive
        e.g. !parsing in which case context is added then the current recursion will
        continue until arriving at a leaf (literal) and leaf processing is in charge of using
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
            _relative_root: relative SchemaEntry where method was called. Recursion variable.
                            Defaults to self contained structure.
        """

        if _relative_root is None:
            _relative_root = self.structure

        # For all the properties in the given schema
        for key, val in properties.items():

            # If key is a known ignored keyword
            if key in IGNORED_ITERABLE_KEYWORDS:
                LOG.debug("Ignoring schema keyword '%s'", key)

            # If the key is known as an interpretation rule
            # call the function mapped into the INTERPRETATION_RULE dictionary
            elif key in INTERPRETATION_RULES:
                # This error is only raised if an interpretation rule is found at root of schema properties
                # rules must be defined in individual items of the properties, hence a parent key should
                # always be present.
                if _parent_key is None:
                    if is_debug():
                        LOG.debug(
                            "current structure = %s",
                            dumps(_relative_root, indent=4, default=vars),
                        )
                    raise RuntimeError("Cannot interpret rule without parent key.")
                _relative_root = INTERPRETATION_RULES[key](
                    self, val, key, _parent_key, _relative_root
                )

            else:
                # Case dict i.e. branch
                if isinstance(val, dict):
                    _relative_root[key] = self.interpret_schema(
                        val,
                        key,
                        _relative_root.inherit(
                            key=key,
                            key_path=[key],
                            context={},
                        ),
                    )

                # Case literal i.e. leaf
                elif isinstance(val, (str, bool, int, float)):
                    LOG.debug("Ignoring key value pair ('%s', '%s')", key, str(val))

                # Else not-implemented
                else:
                    LOG.debug("Unknown iterable type '%s'", str(type(val)))
                    raise NotImplementedError("Unknown iterable type.")

        return _relative_root

    def generate(self) -> SchemaEntry:
        """
        Convenience function to launch interpretation recursion over the schema.
        Results is also internally stored for future access.

        Returns:
            self contained SchemaEntry
        """
        if is_debug():
            # Passing through dumps for pretty printing,
            # however can be costly, so checking if debug is enabled first
            LOG.debug(
                "Initial structure = %s", dumps(self.schema, indent=4, default=vars)
            )

        if self.structure.is_empty():
            self.structure = self.interpret_schema(self.schema["properties"])

        if is_debug():
            # Passing through dumps for pretty printing,
            # however can be costly, so checking if debug is enabled first
            LOG.debug(
                "Interpreted structure = %s",
                dumps(self.structure, indent=4, default=vars),
            )

        return self.structure


# Class level method to register interpretation rules
SchemaInterpreter.register_rule = register_interpretation_rule
