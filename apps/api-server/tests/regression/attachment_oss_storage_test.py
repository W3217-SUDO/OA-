"""附件以 OSS 为准：后台同步切换路径、本机文件只做缓存、按需从 OSS 取回、在线编辑新版本写 OSS。"""

import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import AsyncMock, patch

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.core import attachment_oss_sync, storage
from app.core.oss_attachments import oss_editor_revision_key
from app.database import Base
from app.models import BusinessRecord, FileAttachment

OSS = {"ai_oss_bucket": "huzhi3217", "ai_oss_credentials_file": "/x.csv", "ai_oss_endpoint": "oss-cn-beijing.aliyuncs.com",
       "attachment_oss_prefix": "附件"}


class AttachmentOssStorageTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.temporary = tempfile.TemporaryDirectory(prefix="CODEX-oss-")
        self.root = Path(self.temporary.name)
        self.patches = [patch.object(storage, "UPLOAD_ROOT", self.root),
                        *(patch.object(settings, name, value) for name, value in OSS.items())]
        for item in self.patches:
            item.start()
        attachment_oss_sync._failed.clear()
        self.puts = []

        async def put(bucket, key, content, content_type, *, credentials_file, endpoint, metadata=None, tags=None):
            self.puts.append({"bucket": bucket, "key": key, "content": content, "metadata": metadata, "tags": tags})
            return True
        self.put_patch = patch("app.core.oss_attachments.oss_put_object", put)
        self.put_patch.start()

    async def asyncTearDown(self):
        self.put_patch.stop()
        for item in self.patches:
            item.stop()
        await self.engine.dispose()
        self.temporary.cleanup()

    async def add_attachment(self, name, content, *, age_seconds=600, record=None, **extra):
        stored = f"{name}.pdf"
        (self.root / stored).write_bytes(content)
        async with self.sessions() as db:
            item = FileAttachment(record_id=record, category="案件文档", original_name=f"{name}.pdf", stored_name=stored,
                                  content_type="application/pdf", size=len(content), path=str(self.root / stored), uploader="tgn",
                                  created_at=datetime.now(timezone.utc) - timedelta(seconds=age_seconds), **extra)
            db.add(item)
            await db.commit()
            return item.id

    async def test_sync_moves_settled_attachments_to_oss_and_keeps_local_cache(self):
        settled = await self.add_attachment("settled", b"%PDF settled")
        fresh = await self.add_attachment("fresh", b"%PDF fresh", age_seconds=5)
        locked = await self.add_attachment("locked", b"%PDF locked", word_editor_lock_token="lease",
                                           word_editor_lock_expires_at=datetime.now(timezone.utc) + timedelta(minutes=5))
        async with self.sessions() as db:
            moved = await attachment_oss_sync.sync_once(db)
        self.assertEqual(moved, 1)
        self.assertEqual(self.puts[0]["key"], f"附件/案件文档/{datetime.now(timezone.utc):%Y-%m}/{settled}_settled.pdf")
        self.assertEqual((self.puts[0]["metadata"]["attachment-id"], self.puts[0]["tags"]), (settled, {"source": "oa-attachment"}))
        async with self.sessions() as db:
            items = {item.id: item for item in (await db.get(FileAttachment, settled), await db.get(FileAttachment, fresh), await db.get(FileAttachment, locked))}
        self.assertTrue(items[settled].path.startswith("oss://huzhi3217/附件/案件文档/"))
        self.assertFalse(items[fresh].path.startswith("oss://"))   # 刚上传的稍后再同步
        self.assertFalse(items[locked].path.startswith("oss://"))  # 正在在线编辑的不切换
        self.assertEqual(items[settled].stored_name, "settled.pdf")
        cached = storage._attachment_storage_path(items[settled])  # 本机原文件仍作为缓存读取
        self.assertEqual(cached, (self.root / "settled.pdf").resolve())
        self.assertEqual(storage.attachment_local_path(items[settled]), cached)

    async def test_editor_version_record_follows_the_new_oss_path(self):
        async with self.sessions() as db:
            record = BusinessRecord(module="case", serial_no="C1", title="案件", customer="", owner="tgn", department="", status="", data={})
            db.add(record)
            await db.commit()
            record_id = record.id
        attachment_id = await self.add_attachment("edited", b"PK docx", record=record_id)
        async with self.sessions() as db:
            item = await db.get(FileAttachment, attachment_id)
            record = await db.get(BusinessRecord, record_id)
            record.data = {"libreoffice_documents": {str(attachment_id): {"path": item.path, "version": "v1", "versions": []}}}
            await db.commit()
        async with self.sessions() as db:
            await attachment_oss_sync.sync_once(db)
        async with self.sessions() as db:
            item = await db.get(FileAttachment, attachment_id)
            record = await db.get(BusinessRecord, record_id)
        self.assertEqual(record.data["libreoffice_documents"][str(attachment_id)]["path"], item.path)
        self.assertTrue(item.path.startswith("oss://"))

    async def test_missing_local_file_is_skipped_and_not_retried(self):
        broken = await self.add_attachment("broken", b"%PDF x")
        (self.root / "broken.pdf").unlink()
        async with self.sessions() as db:
            self.assertEqual(await attachment_oss_sync.sync_once(db), 0)
            self.assertEqual(await attachment_oss_sync.sync_once(db), 0)
        self.assertIn(broken, attachment_oss_sync._failed)
        self.assertEqual(self.puts, [])

    async def test_uncached_oss_attachment_is_fetched_into_cache_on_demand(self):
        item = FileAttachment(id=99, category="案件文档", original_name="远程.pdf", stored_name="legacy-name.pdf", size=9,
                              path="oss://huzhi3217/附件/案件文档/2026-10/99_远程.pdf")
        self.assertIsNone(storage._attachment_storage_path(item))
        with patch("app.core.oss_attachments.oss_attachment_bytes", AsyncMock(return_value=b"%PDF from")) as fetch:
            path = await storage.ensure_attachment_local(item)
            again = await storage.ensure_attachment_local(item)
        self.assertEqual(path.read_bytes(), b"%PDF from")
        self.assertEqual((path, fetch.await_count), (again, 1))  # 第二次直接读缓存
        self.assertEqual(path.parent.name, storage.OSS_CACHE_DIR)
        self.assertEqual(storage._attachment_storage_path(item), path)

    def test_online_edit_revisions_default_to_the_attachment_folder(self):
        with patch.object(settings, "office_oss_write_prefix", ""):
            key = oss_editor_revision_key(5, "a" * 32, "b" * 64)
        self.assertEqual(key, f"附件/在线编辑/5/{'a' * 32}/{'b' * 64}.docx")


if __name__ == "__main__":
    unittest.main()
