"""BUG20261102011：合同附件只在 OSS、本机没有缓存时，申请用印要先取回再复制，不能报“来源文件不存在”。"""

import asyncio
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app.core import storage


class SealCopyOssSourceTest(unittest.TestCase):
    def test_uncached_oss_source_is_fetched_then_copied(self):
        root = Path(tempfile.mkdtemp())
        source = SimpleNamespace(
            id=1, record_id=10, invoice_record_id=None, original_name="合同.xls",
            stored_name="legacy-oss-1", content_type="application/vnd.ms-excel", size=3,
            path="oss://oabeifen3217/HZ.CRM/ContractFiles/a.xls", document_date=None,
        )
        source_record = SimpleNamespace(id=10, module="contract", serial_no="HT-1")
        target_record = SimpleNamespace(id=20)
        added = []
        db = SimpleNamespace(
            scalars=AsyncMock(return_value=SimpleNamespace(all=lambda: [source])),
            add=added.append, flush=AsyncMock(), rollback=AsyncMock(),
        )

        async def fake_bytes(item):
            return b"xls"

        with patch.object(storage, "UPLOAD_ROOT", root), \
                patch("app.core.oss_attachments.oss_attachment_bytes", fake_bytes), \
                patch("app.core.permissions._ensure_attachment_record_visible", AsyncMock(return_value=source_record)), \
                patch("app.core.permissions._ensure_record_module", AsyncMock()), \
                patch("app.core.documents._sync_seal_document_names", AsyncMock()):
            self.assertIsNone(storage._attachment_storage_path(source))
            targets = asyncio.run(storage._copy_seal_source_attachments(target_record, [1], {"username": "fwl"}, db))
        self.assertEqual(len(targets), 1)
        self.assertEqual(targets[0].read_bytes(), b"xls")
        self.assertEqual(added[0].original_name, "合同.xls")
        self.assertEqual(added[0].record_id, 20)


if __name__ == "__main__":
    unittest.main()
