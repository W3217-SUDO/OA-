"""BUG20261030011：OSS 附件改由服务器转交后，本机缓存按天数和总量清理，只动缓存目录。"""

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.core import storage


class OssCachePruneTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.cache = self.root / storage.OSS_CACHE_DIR
        self.cache.mkdir()
        self.outside = self.root / "kept-original.png"
        self.outside.write_bytes(b"x" * 10)

    def make(self, name: str, size: int, age_seconds: int, now: float) -> Path:
        path = self.cache / name
        path.write_bytes(b"x" * size)
        os.utime(path, (now - age_seconds, now - age_seconds))
        return path

    def test_removes_expired_and_oldest_over_limit_only_in_cache(self):
        now = 1_800_000_000.0
        old = self.make("old.png", 10, storage.OSS_CACHE_MAX_AGE_SECONDS + 60, now)
        older_recent = self.make("a.png", 40, 300, now)
        newer_recent = self.make("b.png", 40, 60, now)
        temp = self.make(".writing.tmp", 10, storage.OSS_CACHE_MAX_AGE_SECONDS + 60, now)
        with patch.object(storage, "UPLOAD_ROOT", self.root), patch.object(storage, "OSS_CACHE_MAX_BYTES", 50):
            removed = storage.prune_oss_cache(now)
        self.assertEqual(removed, 2)
        self.assertFalse(old.exists())
        self.assertFalse(older_recent.exists())
        self.assertTrue(newer_recent.exists())
        self.assertTrue(temp.exists())
        self.assertTrue(self.outside.exists())

    def test_missing_cache_directory_is_noop(self):
        with patch.object(storage, "UPLOAD_ROOT", self.root / "nowhere"):
            self.assertEqual(storage.prune_oss_cache(), 0)


if __name__ == "__main__":
    unittest.main()
