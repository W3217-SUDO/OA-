"""旧系统迁来、只在 OSS 上的附件：下载/打包/预览都要先取回本机缓存，不能报“文件不存在”或静默漏文件。"""

import asyncio
import io
import tempfile
import unittest
import zipfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException

from app.areas.legal import seals
from app.core import case_invoice_files, storage


def oss_item(item_id: int, name: str, record_id: int = 10, size: int = 3):
    return SimpleNamespace(
        id=item_id, record_id=record_id, original_name=name, stored_name=f"legacy-oss-{item_id}",
        content_type="application/octet-stream", size=size, path=f"oss://oabeifen3217/HZ.CRM/{item_id}/{name}",
    )


class OssAttachmentReadersTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())

    def test_ensure_local_fetches_uncached_oss_file(self):
        item = oss_item(1, "a.pdf")
        with patch.object(storage, "UPLOAD_ROOT", self.root), \
                patch("app.core.oss_attachments.oss_attachment_bytes", AsyncMock(return_value=b"pdf")):
            self.assertIsNone(storage._attachment_storage_path(item))
            path = asyncio.run(storage.ensure_attachment_local(item))
        self.assertEqual(path.read_bytes(), b"pdf")

    def test_invoice_entries_read_oss_file(self):
        item = oss_item(2, "12345678.pdf")
        with patch.object(storage, "UPLOAD_ROOT", self.root), \
                patch("app.core.oss_attachments.oss_attachment_bytes", AsyncMock(return_value=b"inv")):
            _, entries = asyncio.run(case_invoice_files._invoice_file_entries(item))
        self.assertEqual(entries, [("12345678.pdf", b"inv")])

    def test_seal_batch_download_includes_oss_files_and_lists_failures(self):
        ok, broken = oss_item(3, "合同.docx", record_id=7), oss_item(4, "盖章件.pdf", record_id=7)
        record = SimpleNamespace(id=7, serial_no="P261030-1")

        async def fake_bytes(item):
            if item.id == broken.id:
                raise HTTPException(status_code=502, detail="OSS 附件读取失败")
            return b"doc"

        db = SimpleNamespace(scalars=AsyncMock(return_value=SimpleNamespace(all=lambda: [ok, broken])))
        body = SimpleNamespace(application_ids=[7])
        with patch.object(storage, "UPLOAD_ROOT", self.root), \
                patch("app.core.oss_attachments.oss_attachment_bytes", fake_bytes), \
                patch("app.core.permissions._ensure_record_module", AsyncMock(return_value=record)):
            response = asyncio.run(seals.batch_download_seal_files(body, identity={"username": "u"}, db=db))

            async def collect():
                return b"".join([chunk async for chunk in response.body_iterator])
            payload = asyncio.run(collect())
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            names = archive.namelist()
            self.assertIn("P261030-1/3-合同.docx", names)
            self.assertEqual(archive.read("P261030-1/3-合同.docx"), b"doc")
            self.assertIn("盖章件.pdf", archive.read("未能下载的文件.txt").decode())


if __name__ == "__main__":
    unittest.main()
