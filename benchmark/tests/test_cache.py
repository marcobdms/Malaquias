import tempfile
import unittest
from pathlib import Path

import numpy as np

from benchmark.cache import EmbeddingCache, encode_with_cache


class FakeEncoder:
    def __init__(self):
        self.calls = 0

    def encode(self, texts, **_kwargs):
        self.calls += 1
        return np.array([[len(text), sum(map(ord, text))] for text in texts], dtype=np.float32)


class CacheTests(unittest.TestCase):
    def test_second_encoding_is_a_cache_hit(self):
        with tempfile.TemporaryDirectory() as temporary:
            encoder = FakeEncoder()
            with EmbeddingCache(Path(temporary) / "cache.sqlite3") as cache:
                first, first_stats = encode_with_cache(encoder, "fake", ["uno", "dos"], cache, 2)
                second, second_stats = encode_with_cache(encoder, "fake", ["uno", "dos"], cache, 2)
            np.testing.assert_array_equal(first, second)
            self.assertEqual(first_stats, {"hits": 0, "misses": 2})
            self.assertEqual(second_stats, {"hits": 2, "misses": 0})
            self.assertEqual(encoder.calls, 1)


if __name__ == "__main__":
    unittest.main()
