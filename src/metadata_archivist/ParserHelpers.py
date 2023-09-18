#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""

Collection of helper classes for Parser module.

Authors: Jose V., Matthias K.

"""

from pathlib import Path
from copy import deepcopy
from json import load, dumps
from re import match, fullmatch
from collections.abc import Iterable
from typing import Optional, Any, Dict, Union

from .Logger import LOG, is_debug

#class Hierachy:
#    """
#    helperclass, representing the hierachy in the schema
#    """
#
#    def __init__(self):
#        self._hierachy = []
#
#    def add(self, entry, level):
#        try:
#            self._hierachy[level] = entry
#            return level + 1
#        except IndexError:
#            if len(self._hierachy) == level:
#                self._hierachy.append(entry)
#                return level + 1
#            else:
#                raise RuntimeError(
#                    f'''Hierachy list corrupted, cannot append {entry} at index: {level}
#                Hierachy list:
#                {self._hierachy}
#                ''')
#
#    @property
#    def extractor_name(self):
#        if isinstance(self._hierachy[-1], ExtractorDirective):
#            return self._hierachy[-1].name
#        else:
#            return None
#
#    @property
#    def extractor_directive(self):
#        if isinstance(self._hierachy[-1], ExtractorDirective):
#            return self._hierachy[-1]
#        else:
#            return None
#
#    @property
#    def regexps(self):
#        return_list = []
#        for y in self._hierachy[:-1]:
#            if isinstance(y, DirectoryDirective):
#                return_list.append(y.regexp)
#        return return_list
#
#    def match_path(self, file_path: Path):
#        '''
#        check if given file_path matches the file path of the directive by:
#        - matching directory by directory in reverse order
#        - if the Directive has not path it always matches
#        '''
#        if isinstance(self._hierachy[-1], ExtractorDirective):
#            directive = self._hierachy[-1]
#            if not directive.path:
#                return True
#            else:
#                directive_path_list = list(Path(directive.path).parts)
#                directive_path_list.reverse()
#                file_path_list = list(file_path.parts)
#                file_path_list.reverse()
#                for i, x in enumerate(directive_path_list):
#                    if x == '*' and (i + 1) == len(directive_path_list):
#                        return True
#                    elif x == '*' and not match('.*', file_path_list[i]):
#                        return False
#                    # for the varname match
#                    elif fullmatch('.*{[a-zA-Z0-9_]+}.*', x):
#                        for j, y in enumerate(self._hierachy[:-1]):
#                            if isinstance(y, DirectoryDirective) and x.find(
#                                    '{' + f'{y.varname}' + '}') != -1:
#                                # TODO: add multiple regexp for x
#                                if not match(
#                                        x.format(**{y.varname: y.regexp}),
#                                        file_path_list[i]):
#                                    return False
#                                else:
#                                    self._hierachy[j].name = file_path_list[i]
#                    elif not match(x, file_path_list[i]):
#                        return False
#                return True
#        else:
#            raise NotImplementedError(
#                'currently only metadata from extractors can be added to the schema'
#            )
#        
#    def is_empty(self) -> bool:
#        return len(self._hierachy) == 0


#class HierachyEntry:
#    """
#    entry in the Hierachy
#    """
#
#    def __init__(self, add_to_metadata: Optional[bool] = False, **kwargs):
#        self._add_to_metadata = add_to_metadata
#        if 'name' in kwargs.keys():
#            self.name = kwargs['name']
#        else:
#            self.name = None
#        if 'description' in kwargs.keys():
#            self.description = kwargs['description']
#        else:
#            self.description = None
#
#    @property
#    def add_to_metadata(self):
#        if self.name is None:
#            raise RuntimeError(
#                f'add_to_metadata is set to True but name is None')
#        else:
#            return self.name
#
#
#class DirectoryDirective(HierachyEntry):
#
#    def __init__(self,
#                 varname,
#                 regexp,
#                 add_to_metadata: Optional[bool] = True,
#                 **kwargs):
#        super().__init__(add_to_metadata, **kwargs)
#        self.varname = varname
#        self.regexp = regexp
#
#
#class ExtractorDirective(HierachyEntry):
#    """
#    helperclass to handle extractor directives in archivist schema
#    """
#
#    def __init__(self,
#                 name,
#                 add_to_metadata: Optional[bool] = False,
#                 **kwargs):
#        super().__init__(add_to_metadata, **kwargs)
#        self.name = name
#        self.path = kwargs.pop('path', None)
#        self.keys = kwargs.pop('keys', None)

    # def parse_metadata(self, metadata):
    #     if self.keys is None:
    #         return metadata
    #     else:
    #         return_dict = {}
    #         for kk in self.keys:
    #             kk_list = kk.split('/')
    #             dd = return_dict
    #             if len(kk_list) > 1:
    #                 for node in kk_list[:-1]:
    #                     if node not in dd.keys():
    #                         dd[node] = {}
    #             dd[kk_list[-1]] = deep_get(metadata, *kk.split('/'))
    #         return return_dict


class Cache:
    """
    Convenience class for caching extraction results.
    For each extractor a _CacheExtractor object is created which will store all extraction results.
    To this end, extractors have to be added through corresponding method.
    Then _CacheExtractor is obtained through index access i.e. ```[key]``` and used to add _CacheEntry objects.
    Iteration is possible by using dictionary iterator on the actual cache storage.
    """

    _cache: dict

    def __init__(self):
        self._cache = dict()
        self._iterator = None

    def add(self, extractor_id) -> None:
        if extractor_id not in self._cache:
            self._cache[extractor_id] = _CacheExtractor()
        else:
            raise KeyError(f"Extractor {extractor_id} already exists in cache")
        
    def drop(self, extractor_id) -> None:
        self._cache.pop(extractor_id, None)

    def __getitem__(self, extractor_id):
        return self._cache[extractor_id]

    def __iter__(self):
        """
        Iteration is done by iterating over the storage dictionary.
        """
        self._iterator = iter(self._cache)
        return self

    def __next__(self):
        """
        When iterating over a dictionary keys are returned,
        here we return the corresponding _CacheExtractor objects.
        """
        if self._iterator is None:
            raise StopIteration
        return self._cache[next(self._iterator)]

    def is_empty(self):
        return len(self._cache) == 0


class _CacheExtractor:
    """
    Convenience class for caching extraction results.
    For each extractor a _CacheExtractor object is created which will store all extraction results.
    _CacheExtractor objects can contain any amount of _CacheEntry objects.
    Iteration is possible by using list iterator on the actual entry storage.
    """

    _entries: list

    def __init__(self):
        self._entries = list()
        self._iterator = None

    def add(self, *args):
        entry = _CacheEntry(*args)
        self._entries.append(entry)
        return entry

    def __getitem__(self, index: int):
        return self._entries[index]

    def __iter__(self):
        """
        Iteration is done by iterating over the storage dictionary.
        """
        self._iterator = iter(self._entries)
        return self

    def __next__(self):
        """
        When iterating over a dictionary keys are returned,
        here we return the corresponding _CacheExtractor objects.
        """
        if self._iterator is None:
            raise StopIteration
        return next(self._iterator)

    def is_empty(self):
        return len(self._entries) == 0


class _CacheEntry:
    """
    Convenience class for caching extraction results.
    For each extractor a _CacheExtractor object is created which will store all extraction results.
    For each file extracted a _CacheEntry object is created, after extraction the results can be
    lazily stored and a meta_path is generated or the metadata can be directly stored in the entry.
    If the results are lazily stored then calling load_metadata would load them to memory.
    """

    decompress_path: Path
    file_path: Path
    metadata: dict
    meta_path: Path


    def __init__(self,
                 decompress_path: Path,
                 file_path: Path,
                 metadata: Optional[dict] = None):
        self.decompress_path = decompress_path
        self.file_path = file_path
        self.metadata = metadata
        if metadata is None:
            self.meta_path = Path(str(file_path) + ".meta")
        else:
            self.meta_path = None

    def load_metadata(self) -> dict:
        """
        If a cache entry does not contain metadata, attempts to load it from the meta_path.
        """
        if self.metadata is None:
            if self.meta_path is None:
                raise RuntimeError(
                    "Cache entry does not contain metadata and meta path not found."
                )
            with self.meta_path.open("r") as f:
                self.metadata = load(f)

            if self.metadata is None:
                raise RuntimeError(f"Failed to load metadata {dumps(self, indent=4, default=vars)}")
            else:
                self.meta_path = None
            
        return self.metadata

    def add_metadata(self, metadata: dict):
        """
        TODO: should we deprecate it in favor of load_metadata?
        """
        if self.metadata is not None:
            raise RuntimeError('metadata already exists')
        self.metadata = metadata

    @property
    def rel_path(self) -> Path:
        """
        Returns the file path relative to the decompression path.
        In practice this means that a unique path relative to the decompression path
        is generated for the extracted file.
        """
        return self.file_path.relative_to(self.decompress_path)


class Indexes:
    """
    Class to be handled only by Parser class.
    Indexing class for storing per extractor:
        - extractors list index
        - input file patterns list index
        - schema properties list index
    """
    ex_indexes: dict
    ifp_indexes: dict
    sp_indexes: dict

    def __init__(self) -> None:
        self.ex_indexes = {}
        self.ifp_indexes = {}
        self.sp_indexes = {}

    def _get_storage(self, storage: str) -> dict:
        """
        Private method for getting specific storage based on storage name string:
        To determine which storage should the index go to:
            - 'ex' or 'extractors' for extractor index list
            - 'ifp' or 'input_file_patterns' for input file pattern index list
            - 'sp' or 'schema_properties' for schema property list
        """
        ex_patterns = ["ex", "extractors"]
        ifp_patterns = ["ifp", "input_file_patterns"]
        sp_patterns = ["sp", "schema_properties"]
        if storage in ex_patterns:
            return self.ex_indexes
        elif storage in ifp_patterns:
            return self.ifp_indexes
        elif storage in sp_patterns:
            return self.sp_indexes

        raise ValueError(f"Incorrect value for storage name, got {storage}, accepted {ex_patterns + ifp_patterns + sp_patterns}")
        
    
    def set_index(self, extractor_id: Any, storage: str, index: int) -> None:
        """
        Generic set index method for all storages.
        """
        self._get_storage(storage)[extractor_id] = index

    def get_index(self, extractor_id: Any, storage: Optional[str] = None) -> Union[int, Dict[str, int]]:
        """
        Generic get index method for all storages.
        If no storage specified, all stored indexes are returned as a dictionary.
        """
        if storage is None:
            # TODO: Should we raise an error if the id is not in any/all dictionaries?
            return {
                "ex": self.ex_indexes.get(extractor_id, None),
                "ifp": self.ifp_indexes.get(extractor_id, None),
                "sp": self.sp_indexes.get(extractor_id, None),
                }
        else:
            return self._get_storage(storage)[extractor_id]
        
    def drop_indexes(self, extractor_id: Any) -> None:
        """
        Remove method for an extractor_id in all storages.
        TODO: Should we return values?
        TODO: Should we raise if id is not known?
        """
        self.ex_indexes.pop(extractor_id, None)
        self.ifp_indexes.pop(extractor_id, None)
        self.sp_indexes.pop(extractor_id, None)

"""
Constants for schema specific/special values to be considered when parsing.
"""
_KNOWN_PROPERTIES = [
    "properties",
    "unevaluatedProperties",
    "additionalProperties",
]

_SPECIAL_PROPERTIES = [
    "patternProperties",
    "!extractor"
]

_SPECIAL_STRINGS = [
    "$ref",
    "!varname"
]

_KNOWN_REFS = [
    "#/$defs/",
]


class SchemaEntry:
    """
    Convenience superset of dictionary class.
    Used to recursively generate nested dictionary structure to serve as an intermediary between schema and metadata file.
    Contains additional context dictionary for a given tree level and the name of the root node.
    For initial root node, no name is defined, however for subsequent nodes there should always be a name.
    Get, set, and iteration access is redirected to internal storage.
    """

    name: str
    context: dict
    _content: dict

    def __init__(self, name: Optional[str] = None, context: Optional[dict] = None) -> None:
       self.name = name
       self.context = context if context is not None else {}
       self._content = {}
       self._iterator = None

    def __getitem__(self, key) -> Any:
        return self._content[key]
    
    def __setitem__(self, key, value) -> None:
        self._content[key] = value

    def __contains__(self, key) -> bool:
        return key in self._content
    
    def items(self):
        return self._content.items()
    
    def is_empty(self) -> bool:
        return len(self._content) == 0


class SchemaInterpreter:
    """
    Functionality class used for interpreting the schema.
    When defining the JSON schema with additional directives,
    the object is cannot be used directly for structuring.
    To this end, this class is used to generate an intermediary structure
    that respects the schema and its directives while being functionally
    usable as a mirror for structuring the final metadata file.
    """

    _schema: dict
    structure: SchemaEntry

    def __init__(self, schema: dict) -> None:
        if not isinstance(schema, dict):
            raise RuntimeError(
                f'Incorrect schema used for iterator {schema}'
            )
        if 'properties' not in schema or not isinstance(
                schema['properties'], dict):
            raise RuntimeError(
                f'Incorrect schema structure, root is expected to contain properties dictionary: {schema}'
            )
        if '$defs' not in schema or not isinstance(
                schema['$defs'], dict):
            raise RuntimeError(
                f'Incorrect schema structure, root is expected to contain $defs dictionary: {schema}'
            )

        self._schema = schema
        self.structure = SchemaEntry()

    def _process_special_dict(self, prop_key: str, prop_val: dict, parent_key: str) -> SchemaEntry:
        """
        Method to interpret special dictionaries in schema.
        Currently only patternProperties and !extractor directives are implemented.
        More can be added as additional elif checks.
        TODO: create a modular system for processing? (instead of if/elif checks?)
        """
        new_entry = SchemaEntry(name=parent_key)

        # Case patternProperties
        # We create a regex context and recurse over the contents of the property.
        if prop_key == "patternProperties":
            new_entry.context = {"useRegex": True}
            return self._interpret_schema(prop_val, prop_key, new_entry)

        # Case !extractor
        # We create an !extractor context but keep on with current recursion level
        # Contents of this dictionary are not supposed to contain additional directives/properties.
        elif prop_key == "!extractor":
            new_entry.context = {prop_key: prop_val}
            return new_entry
        
        # Else not-implemented
        else:
            raise NotImplementedError(f"Unknown special property type: {prop_key}")
        

    def _process_special_strings(self, prop_key: str, prop_val: dict, parent_key: str, entry: SchemaEntry) -> SchemaEntry:
        """
        Method to interpret special string values in schema.
        Currently only $ref and !varname directives are implemented.
        More can be added as additional elif checks.
        TODO: create a modular system for processing? (instead of if/elif checks?)
        """

        # Case $ref
        if prop_key == "$ref":
            # Check if reference is well formed against knowledge base
            if not any(prop_val.startswith(ss) for ss in _KNOWN_REFS):
                raise RuntimeError(f"Malformed reference prop_value: {prop_key}: {prop_val}")
            # If an !extractor was found before then a SchemaEntry with extractor context must be found at parent_key
            # Otherwise create new entry and call _process_refs to check for correctness before creating extraction context.
            if parent_key not in entry:
                entry[parent_key] = SchemaEntry(name=parent_key)
            elif "!extractor" not in entry[parent_key].context:
                raise RuntimeError(f"Parent key exists in relative root but not appropriate context defined {prop_key}, {parent_key}")
            entry[parent_key] = self._process_refs(prop_val, entry[parent_key])

        # Case !varname
        elif prop_key == "!varname":
            # Check if regex context is present in current entry
            if "useRegex" not in entry.context:
                raise RuntimeError("Contextless !varname found")
            # Add a !varname context which contains the name to use
            # and to which expression it corresponds to.
            entry.context.update({prop_key: prop_val, "regexp": parent_key})

        # Else not-implemented
        else:
            raise NotImplementedError(f"Unknown special property type: {prop_key}")
        
        return entry
        
    def _recurse_sub_schema(self, sub_schema: dict, entry: SchemaEntry, filters: Optional[list] = None) -> list:
        # TODO: recursively explore extractor sub-schema and collect entry names and description.
        # List of keys can be passed as filters to select a branch of the extractor sub schema.
        # Resulting list should contain all the #/property that needs to be linked
        # with their respective positions so that _process_refs can take care of creating links
        # and avoid circular dependencies.
        return []

    def _process_refs(self, prop_val: str, entry: SchemaEntry) -> SchemaEntry:

        # Test correctness of reference
        val_split = prop_val.split("/")
        if len(val_split) < 3:
            raise ValueError(f"Malformed reference: {prop_val}")
        ex_id = val_split[2]
        if ex_id not in self._schema["$defs"]:
            raise KeyError(f"Extractor not found: {ex_id}")
        
        # Add identified extractor to context
        LOG.debug(f"processing reference to: {ex_id}")
        entry.context["extractor_id"] = ex_id

        # Further process reference e.g. filters, internal property references -> links
        sub_schema = self._schema["$defs"][ex_id]["properties"]
        links = self._recurse_sub_schema(sub_schema, entry, filters=None if len(val_split) <= 3 else val_split[3:])
        # TODO: take care of linking

        return entry
    
    def _interpret_schema(self,
                         properties: dict,
                         parent_key: Optional[str] = None,
                         relative_root: Optional[SchemaEntry] = None):
        """
        Recursive method to explore JSON schema.
        Following the technical assumptions made (cf. README.md/SchemaInterpreter),
        only the properties of the schema are interpreted (recursively so),
        items of the property are of type str -> dict|str (key -> value),
        any other type is currently ignored as NotImplemented feature.
        When interpreting we generate a data object with a tree structure,
        i.e. nested SchemaEntry.

        - When processing dictionaries, they can either be nested properties,
        in which case a new branch is created i.e. new SchemaEntry and a new
        recursion is called on its contents.
        Otherwise if it is a special directive with multiple instructions e.g. !extractor
        a new entry with additional context is created but is not recursed over,
        in this case the current recursion will continue until arriving at a leaf (str)
        and leaf processing is in charge of using the enriched entry.
        Other dictionaries are not considered as intermediary structures
        hence their contents are recursed over but do not generate a new branch.

        - When processing strings, they can be either JSON schema additional information
        in which case it is ignored or they can be additional directives e.g. $ref or !varname
        Both of which are specially processed to enriched the context.

        """
        if relative_root is None:
            relative_root = self.structure

        # For all the properties in the given schema
        for key, val in properties.items():

            # Case dict i.e. branch
            if isinstance(val, dict):

                # Known simple properties create a new branch without context
                if key in _KNOWN_PROPERTIES:
                    if parent_key is None:
                        raise RuntimeError("Nameless property branch found.")
                    relative_root[parent_key] = self._interpret_schema(val, key, SchemaEntry(name=parent_key))

                # Special properties create a new branch with context
                elif key in _SPECIAL_PROPERTIES:
                    if parent_key is None:
                        raise RuntimeError("Nameless special property branch found.")
                    relative_root[parent_key] = self._process_special_dict(key, val, parent_key)

                # Other dictionaries do no branch but go in depth
                else:
                    relative_root = self._interpret_schema(val, key, relative_root)

            # Case str i.e. leaf            
            elif isinstance(val, str):
                if parent_key is None:
                    raise RuntimeError("Nameless tree leaf found.")
                
                # Special strings add context or represent an extractor
                if key in _SPECIAL_STRINGS:
                    relative_root = self._process_special_strings(key, val, parent_key, relative_root)

                # Others are ignored
                else:
                    LOG.debug(f"Ignoring key value pair: {key}: {val}")

            # Else not-implemented/ignored
            else:
                if isinstance(val, Iterable):
                    raise NotImplementedError(f"Unknown iterable type: {key}: {type(val)}")
                else:
                    LOG.debug(f"Ignoring key value pair: {key}: {val}")

        return relative_root
    
    def generate(self) -> SchemaEntry:
        """
        Convenience function to launch interpretation recursion over the schema.
        Results is also internally stored for future access.
        """
        if is_debug():
            # Passing through dumps for pretty printing,
            # however can be costly, so checking if debug is enabled first
            LOG.debug(dumps(self._schema, indent=4, default=vars))

        if self.structure.is_empty():
            self.structure = self._interpret_schema(self._schema["properties"])

        if is_debug():
            # Passing through dumps for pretty printing,
            # however can be costly, so checking if debug is enabled first
            LOG.debug(dumps(self.structure, indent=4, default=vars))
        
        return self.structure
        