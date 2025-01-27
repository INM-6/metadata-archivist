#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""

Unit tests for the Cache helper classes.

Authors: Matthias K., Jose V.

"""

import unittest

from pathlib import Path

from metadata_archivist.helper_classes import CacheEntry, FormatterCache, ParserCache


class TestCacheEntry(unittest.TestCase):

    def test_cache_entry(self):
        """
        test CacheEntry class
        """

        decompress_path = Path("path/to/decompress")
        file_path = Path("path/to/decompress/path/to/file.txt")
        metadata = None

        cache_entry_1 = CacheEntry(explored_path=decompress_path, file_path=file_path)

        self.assertEqual(cache_entry_1.explored_path, decompress_path)
        self.assertEqual(cache_entry_1.file_path, file_path)
        self.assertIsNone(cache_entry_1.metadata)

        self.assertEqual(cache_entry_1.meta_path, Path(str(file_path) + ".meta.pkl"))
        self.assertEqual(cache_entry_1.rel_path, file_path.relative_to(decompress_path))


class TestParserCache(unittest.TestCase):

    def test_parser_cache(self):
        """
        test ParserCache
        """

        parser_cache = ParserCache()

        decompress_path = Path("path/to/decompress")
        file_path = Path("path/to/decompress/path/to/file.txt")

        parser_cache.add(decompress_path, file_path)

        self.assertEqual(parser_cache[0].explored_path, decompress_path)
        self.assertEqual(parser_cache[0].file_path, file_path)

        decompress_path2 = Path("path/to/decompress")
        file_path2 = Path("path/to/decompress/path/to/file.txt")
        metadata2 = {"foo": "bar"}

        parser_cache.add(decompress_path, file_path, metadata2)

        self.assertEqual(parser_cache[1].explored_path, decompress_path2)
        self.assertEqual(parser_cache[1].file_path, file_path2)
        self.assertEqual(parser_cache[1].metadata, metadata2)


class TestFormatterCache(unittest.TestCase):

    def test_cache_init(self):
        """
        test FormatterCache class
        """
        parser_id_1 = "123"
        decompress_path = [Path("path/to/decompress"), Path("path/to/decompress")]
        file_path = [
            Path("path/to/decompress/path/to/file.txt"),
            Path("path/to/decompress/path/to/file2.txt"),
        ]
        metadata = [{"foo": "bar"}, {"foo2": "bar2"}]

        cache = FormatterCache()
        cache.add(parser_id_1)

        cache[parser_id_1].add(decompress_path[0], file_path[0], metadata[0])

        cache[parser_id_1].add(decompress_path[1], file_path[1], metadata[1])

        parser_id_2 = "456"
        decompress_path3 = Path("path/to/decompress")
        file_path3 = Path("path/to/decompress/path/to/file3.txt")
        metadata3 = {"foo3": "bar3"}

        cache.add(parser_id_2)

        cache[parser_id_2].add(decompress_path3, file_path3, metadata3)

        self.assertEqual(cache[parser_id_2][0].file_path, file_path3)
        self.assertEqual(cache[parser_id_2][0].explored_path, decompress_path3)
        self.assertEqual(cache[parser_id_2][0].metadata, metadata3)

        for i, meta_set in enumerate(cache[parser_id_1]):
            self.assertEqual(meta_set.file_path, file_path[i])
            self.assertEqual(meta_set.explored_path, decompress_path[i])
            self.assertEqual(meta_set.metadata, metadata[i])


if __name__ == "__main__":
    unittest.main()
