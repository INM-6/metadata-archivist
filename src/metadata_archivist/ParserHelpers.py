#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""

Collection of helper classes for Parser module.

Authors: Jose V., Matthias K.

"""
import re

from pathlib import Path
from typing import Optional, List, Tuple, NoReturn, Union

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
    our cache is a dict, containing a key for each extractor (named with extractor id)
    and a list of corresponding CacheEntries
    """

    def __init__(self):
        self._cache = {}

    def __getitem__(self, key):
        return self._cache[key]

    def __setitem__(self, key, kwargs: dict):
        if key not in self._cache.keys():
            self._cache[key] = _CacheExtractor(key)
        self._cache[key].add(**kwargs)

    def __iter__(self):
        self.__i = 0
        self.__keys = list(self._cache.keys())
        return self

    def __next__(self):
        if self.__i >= len(self._cache):
            raise StopIteration
        else:
            i = self.__i
            self.__i += 1
            return self[self.__keys[i]]

    def is_empty(self):
        return len(self._cache) == 0


class _CacheExtractor:
    """
    a Extrctor representation in the cache
    """

    def __init__(self, id: str):
        self.id = id
        self._entries = []

    def __getitem__(self, ind):
        return self._entries[ind]

    def add(self, **kwargs):
        self._entries.append(_CacheEntry(**kwargs))


class _CacheEntry:
    """
    a CacheEntries has metadata the path to the decompression roo and a file path
    """

    def __init__(self,
                 decompress_path: Path,
                 file_path: Path,
                 metadata: Optional[dict] = None):
        self.metadata = metadata
        self.file_path = file_path
        self.decompress_path = decompress_path

    def add_metadata(self, metadata: dict):
        if self.metadata is not None:
            raise RuntimeError('metadata already exists')
        self.metadata = metadata

    @property
    def rel_path(self) -> Path:
        return self.file_path.relative_to(self.decompress_path)

    @property
    def meta_path(self):
        if self.metadata is not None:
            return None
        else:
            _meta_path = Path(str(self.file_path) + ".meta")
            if _meta_path.exists():
                raise FileExistsError(
                    f"Unable to save extracted metadata: {_meta_path} exists")
            return _meta_path
