"""附件路径在当前目录和可选历史目录中的读取边界。"""

import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from app.core import storage


class AttachmentStoragePathTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="oa-test-attachment-path-")
        self.base = Path(self.temporary.name).resolve()
        self.current = self.base / "current"
        self.legacy = self.base / "legacy"
        self.current.mkdir()
        self.legacy.mkdir()
        self.patchers = [
            patch.object(storage, "UPLOAD_ROOT", self.current),
            patch.object(storage, "LEGACY_UPLOAD_ROOTS", (self.legacy,)),
        ]
        for patcher in self.patchers:
            patcher.start()

    def tearDown(self):
        for patcher in reversed(self.patchers):
            patcher.stop()
        self.temporary.cleanup()

    def test_current_and_readable_legacy_files_remain_available(self):
        current_file = self.current / "current.txt"
        current_file.write_text("current", encoding="utf-8")
        legacy_file = self.legacy / "legacy.txt"
        legacy_file.write_text("legacy", encoding="utf-8")
        self.assertEqual(
            storage._attachment_storage_path(SimpleNamespace(path=str(current_file), stored_name=current_file.name)),
            current_file,
        )
        original_resolve = Path.resolve

        def resolve(path, *args, **kwargs):
            if path == self.legacy:
                raise AssertionError("当前文件已找到时不得访问可选历史目录")
            return original_resolve(path, *args, **kwargs)

        with patch.object(Path, "resolve", resolve):
            self.assertEqual(
                storage._attachment_storage_path(SimpleNamespace(path=str(current_file), stored_name=current_file.name)),
                current_file,
            )
        self.assertEqual(
            storage._attachment_storage_path(SimpleNamespace(path=str(legacy_file), stored_name=legacy_file.name)),
            legacy_file,
        )
        self.assertIsNone(
            storage._attachment_storage_path(SimpleNamespace(path=str(self.current / "missing.txt"), stored_name="missing.txt"))
        )

    def test_untrusted_original_path_is_not_resolved_or_probed(self):
        outside = self.base / "outside" / "outside.txt"
        outside.parent.mkdir()
        outside.write_text("not trusted", encoding="utf-8")
        original_resolve = Path.resolve
        original_is_file = Path.is_file

        def resolve(path, *args, **kwargs):
            if Path(os.path.abspath(path)) == outside:
                raise AssertionError("不受信原路径不得解析")
            return original_resolve(path, *args, **kwargs)

        def is_file(path):
            if path == outside:
                raise AssertionError("不受信原路径不得探测")
            return original_is_file(path)

        with patch.object(Path, "resolve", resolve), patch.object(Path, "is_file", is_file):
            self.assertIsNone(
                storage._attachment_storage_path(SimpleNamespace(path=str(outside), stored_name=outside.name))
            )
            traversal = self.current / ".." / "outside" / outside.name
            self.assertIsNone(
                storage._attachment_storage_path(SimpleNamespace(path=str(traversal), stored_name=outside.name))
            )

        linked = self.current / "linked.txt"

        def resolve_link(path, *args, **kwargs):
            if path == linked:
                return outside
            return original_resolve(path, *args, **kwargs)

        with patch.object(Path, "resolve", resolve_link), patch.object(Path, "is_file", is_file):
            self.assertIsNone(
                storage._attachment_storage_path(SimpleNamespace(path=str(linked), stored_name=linked.name))
            )

    def test_optional_legacy_permission_error_is_logged_and_skipped(self):
        candidate = self.legacy / "blocked.txt"
        original_is_file = Path.is_file

        def is_file(path):
            if path == candidate:
                raise PermissionError(13, "legacy volume denied", str(path))
            return original_is_file(path)

        with patch.object(Path, "is_file", is_file):
            with self.assertLogs("app.main", level="WARNING") as captured:
                self.assertIsNone(storage._attachment_storage_path(SimpleNamespace(path=str(candidate), stored_name=candidate.name)))
        self.assertTrue(any("可选历史附件文件无法访问" in message and "legacy volume denied" in message for message in captured.output))

        original_resolve = Path.resolve

        def resolve(path, *args, **kwargs):
            if path == self.legacy:
                raise PermissionError(13, "legacy root denied", str(path))
            return original_resolve(path, *args, **kwargs)

        with patch.object(Path, "resolve", resolve):
            with self.assertLogs("app.main", level="WARNING") as captured:
                self.assertIsNone(storage._attachment_storage_path(SimpleNamespace(path=str(candidate), stored_name=candidate.name)))
        self.assertTrue(any("可选历史附件目录无法访问" in message and "legacy root denied" in message for message in captured.output))

    def test_legacy_alias_of_current_root_does_not_repeat_file_probe(self):
        alias = self.base / "legacy-alias"
        original_resolve = Path.resolve
        original_is_file = Path.is_file

        def resolve(path, *args, **kwargs):
            if path == alias:
                return self.current
            return original_resolve(path, *args, **kwargs)

        def is_file(path):
            if alias in path.parents:
                raise AssertionError("指向主上传目录的历史别名不得再次探测")
            return original_is_file(path)

        with patch.object(storage, "LEGACY_UPLOAD_ROOTS", (alias,)):
            with patch.object(Path, "resolve", resolve), patch.object(Path, "is_file", is_file):
                self.assertIsNone(
                    storage._attachment_storage_path(SimpleNamespace(path=str(self.current / "missing.txt"), stored_name="missing.txt"))
                )

    def test_current_root_permission_error_and_other_io_errors_propagate(self):
        current_file = self.current / "blocked.txt"
        legacy_file = self.legacy / "broken.txt"
        original_is_file = Path.is_file

        def is_file(path):
            if path == current_file:
                raise PermissionError(13, "current upload root denied", str(path))
            if path == legacy_file:
                raise OSError(5, "legacy input/output failure", str(path))
            return original_is_file(path)

        with patch.object(Path, "is_file", is_file):
            with self.assertRaisesRegex(PermissionError, "current upload root denied"):
                storage._attachment_storage_path(SimpleNamespace(path=str(current_file), stored_name=current_file.name))
            with self.assertRaisesRegex(OSError, "legacy input/output failure"):
                storage._attachment_storage_path(SimpleNamespace(path=str(legacy_file), stored_name=legacy_file.name))

        original_resolve = Path.resolve

        def resolve(path, *args, **kwargs):
            if path == current_file:
                raise PermissionError(13, "current path resolution denied", str(path))
            return original_resolve(path, *args, **kwargs)

        with patch.object(Path, "resolve", resolve):
            with self.assertRaisesRegex(PermissionError, "current path resolution denied"):
                storage._attachment_storage_path(SimpleNamespace(path=str(current_file), stored_name=current_file.name))


if __name__ == "__main__":
    unittest.main()
