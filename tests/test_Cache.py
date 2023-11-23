"""
Unit tests for the Cache
"""

from pathlib import Path
import unittest
import sys

sys.path.append('src')
from metadata_archivist.FormatterHelpers import Cache, _CacheEntry, _CacheExtractor


class TestCacheEntry(unittest.TestCase):

    def test_cache_entry(self):
        """
        test _CacheEntry class
        """

        decompress_path = Path('path/to/decompress')
        file_path = Path('path/to/decompress/path/to/file.txt')
        metadata = None

        cache_entry_1 = _CacheEntry(decompress_path=decompress_path,
                                    file_path=file_path)

        self.assertEqual(cache_entry_1.decompress_path, decompress_path)
        self.assertEqual(cache_entry_1.file_path, file_path)
        self.assertIsNone(cache_entry_1.metadata)

        self.assertEqual(cache_entry_1.meta_path,
                         Path(str(file_path) + ".meta"))
        self.assertEqual(cache_entry_1.rel_path,
                         file_path.relative_to(decompress_path))

        new_metadata = {'foo': 'bar'}

        cache_entry_1.add_metadata(new_metadata)

        self.assertEqual(cache_entry_1.metadata, new_metadata)
        self.assertIsNone(cache_entry_1.meta_path)


class TestCacheExtractor(unittest.TestCase):

    def test_cache_extractor(self):
        """
        test _CacheExtractor
        """

        #extractor_id = '123'

        #cache_extractor = _CacheExtractor(extractor_id)

        #self.assertEqual(cache_extractor.id, extractor_id)

        cache_extractor = _CacheExtractor()

        # cache entry
        decompress_path = Path('path/to/decompress')
        file_path = Path('path/to/decompress/path/to/file.txt')
        # cache_entry_0 = _CacheEntry(decompress_path=decompress_path,
        #                             file_path=file_path)

        cache_extractor.add(decompress_path=decompress_path,
                            file_path=file_path)

        self.assertEqual(cache_extractor[0].decompress_path, decompress_path)
        self.assertEqual(cache_extractor[0].file_path, file_path)
        # self.assertEqual(cache_extractor[0], cache_entry_0)

        # cache entry
        decompress_path2 = Path('path/to/decompress')
        file_path2 = Path('path/to/decompress/path/to/file.txt')
        metadata2 = {'foo': 'bar'}
        # cache_entry_1 = _CacheEntry(decompress_path=decompress_path,
        #                             file_path=file_path,
        #                             metadata=metadata2)

        cache_extractor.add(decompress_path=decompress_path,
                            file_path=file_path, metadata = metadata2)

        self.assertEqual(cache_extractor[1].decompress_path, decompress_path2)
        self.assertEqual(cache_extractor[1].file_path, file_path2)
        self.assertEqual(cache_extractor[1].metadata, metadata2)
        # self.assertEqual(cache_extractor[1], cache_entry_1)


class TestCache(unittest.TestCase):

    def test_cache_init(self):
        """
        test Cache class
        """
        extractor_id_1 = '123'
        decompress_path = [Path('path/to/decompress'), Path('path/to/decompress')]
        file_path = [Path('path/to/decompress/path/to/file.txt'), Path('path/to/decompress/path/to/file2.txt')]
        metadata = [{'foo': 'bar'}, {'foo2': 'bar2'}]

        cache = Cache()
        cache.add(extractor_id_1)

        cache[extractor_id_1].add(**{'decompress_path': decompress_path[0],
                                 'file_path': file_path[0],
                                 'metadata':metadata[0]})

        cache[extractor_id_1].add(**{'decompress_path': decompress_path[1],
                                 'file_path': file_path[1],
                                 'metadata':metadata[1]})

        extractor_id_2 = '456'
        decompress_path3 = Path('path/to/decompress')
        file_path3 = Path('path/to/decompress/path/to/file3.txt')
        metadata3 = {'foo3': 'bar3'}

        cache.add(extractor_id_2)

        cache[extractor_id_2].add(**{'decompress_path': decompress_path3,
                                 'file_path': file_path3,
                                 'metadata':metadata3})

        self.assertEqual(cache[extractor_id_2][0].file_path, file_path3)
        self.assertEqual(cache[extractor_id_2][0].decompress_path, decompress_path3)
        self.assertEqual(cache[extractor_id_2][0].metadata, metadata3)

        for i, meta_set in enumerate(cache[extractor_id_1]):
            self.assertEqual(meta_set.file_path, file_path[i])
            self.assertEqual(meta_set.decompress_path, decompress_path[i])
            self.assertEqual(meta_set.metadata, metadata[i])

        #ex_ids = [extractor_id_1, extractor_id_2]
        #for i, ex in enumerate(cache):
        #    self.assertEqual(ex.id, ex_ids[i])


if __name__ == "__main__":
    unittest.main()
