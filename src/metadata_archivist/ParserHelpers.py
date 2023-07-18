#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""

Collection of helper classes for Parser module.

Authors: Jose V., Matthias K.

"""

import re

from pathlib import Path
from typing import Optional, Any, Dict, Union

class Hierachy:
    """
    helperclass, representing the hierachy in the schema
    """

    def __init__(self):
        self._hierachy = []

    def add(self, entry, level):
        try:
            self._hierachy[level] = entry
            return level + 1
        except IndexError:
            if len(self._hierachy) == level:
                self._hierachy.append(entry)
                return level + 1
            else:
                raise RuntimeError(
                    f'''Hierachy list corrupted, cannot append {entry} at index: {level}
                Hierachy list:
                {self._hierachy}
                ''')

    @property
    def extractor_name(self):
        if isinstance(self._hierachy[-1], ExtractorDirective):
            return self._hierachy[-1].name
        else:
            return None

    @property
    def extractor_directive(self):
        if isinstance(self._hierachy[-1], ExtractorDirective):
            return self._hierachy[-1]
        else:
            return None

    @property
    def regexps(self):
        return_list = []
        for y in self._hierachy[:-1]:
            if isinstance(y, DirectoryDirective):
                return_list.append(y.regexp)
        return return_list

    def match_path(self, file_path: Path):
        '''
        check if given file_path matches the file path of the directive by:
        - matching directory by directory in reverse order
        - if the Directive has not path it always matches
        '''
        if isinstance(self._hierachy[-1], ExtractorDirective):
            directive = self._hierachy[-1]
            if not directive.path:
                return True
            else:
                directive_path_list = list(Path(directive.path).parts)
                directive_path_list.reverse()
                file_path_list = list(file_path.parts)
                file_path_list.reverse()
                for i, x in enumerate(directive_path_list):
                    if x == '*' and (i + 1) == len(directive_path_list):
                        return True
                    elif x == '*' and not re.match('.*', file_path_list[i]):
                        return False
                    # for the varname match
                    elif re.fullmatch('.*{[a-zA-Z0-9_]+}.*', x):
                        for j, y in enumerate(self._hierachy[:-1]):
                            if isinstance(y, DirectoryDirective) and x.find(
                                    '{' + f'{y.varname}' + '}') != -1:
                                # TODO: add multiple regexp for x
                                if not re.match(
                                        x.format(**{y.varname: y.regexp}),
                                        file_path_list[i]):
                                    return False
                                else:
                                    self._hierachy[j].name = file_path_list[i]
                    elif not re.match(x, file_path_list[i]):
                        return False
                return True
        else:
            raise NotImplementedError(
                'currently only metadata from extractors can be added to the schema'
            )


class HierachyEntry:
    """
    entry in the Hierachy
    """

    def __init__(self, add_to_metadata: Optional[bool] = False, **kwargs):
        self._add_to_metadata = add_to_metadata
        if 'name' in kwargs.keys():
            self.name = kwargs['name']
        else:
            self.name = None
        if 'description' in kwargs.keys():
            self.description = kwargs['description']
        else:
            self.description = None

    @property
    def add_to_metadata(self):
        if self.name is None:
            raise RuntimeError(
                f'add_to_metadata is set to True but name is None')
        else:
            return self.name


class DirectoryDirective(HierachyEntry):

    def __init__(self,
                 varname,
                 regexp,
                 add_to_metadata: Optional[bool] = True,
                 **kwargs):
        super().__init__(add_to_metadata, **kwargs)
        self.varname = varname
        self.regexp = regexp


class ExtractorDirective(HierachyEntry):
    """
    helperclass to handle extractor directives in archivist schema
    """

    def __init__(self,
                 name,
                 add_to_metadata: Optional[bool] = False,
                 **kwargs):
        super().__init__(add_to_metadata, **kwargs)
        self.name = name
        self.path = kwargs.pop('path', None)
        self.keys = kwargs.pop('keys', None)

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

    def add(self, **kwargs):
        entry = _CacheEntry(**kwargs)
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
    a CacheEntries has metadata the path to the decompression roo and a file path
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

    def add_metadata(self, metadata: dict):
        if self.metadata is not None:
            raise RuntimeError('metadata already exists')
        self.metadata = metadata
        self.meta_path = None

    @property
    def rel_path(self) -> Path:
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
