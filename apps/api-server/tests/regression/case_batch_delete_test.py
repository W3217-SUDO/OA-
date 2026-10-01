import os
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import httpx
from sqlalchemy import event, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database import Base, get_db
from app.main import app
from app.models import BusinessRecord, FileAttachment, Notification, User, WorkflowEvent
from app.security import current_identity
from app.areas.legal import router as legal


class CaseBatchDeleteTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool)

        @event.listens_for(self.engine.sync_engine, "connect")
        def enable_foreign_keys(connection, _):
            connection.execute("PRAGMA foreign_keys=ON")

        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.temp = tempfile.TemporaryDirectory(prefix="CODEX-case-batch-delete-")
        self.root = Path(self.temp.name)
        self.root_patch = patch.object(legal, "UPLOAD_ROOT", self.root)
        self.root_patch.start()
        self.identity = {"username": "CODEX-BATCH-ADMIN", "role": "admin"}
        async with self.sessions() as db:
            self.cases = [BusinessRecord(module="case", serial_no=f"CODEX-CASE-{n}", title=f"CODEX case {n}",
                                         status="执行", owner=self.identity["username"], data={}) for n in range(3)]
            db.add_all(self.cases)
            await db.flush()
            self.ids = [row.id for row in self.cases]
            task = BusinessRecord(module="task", serial_no="CODEX-TASK", title="CODEX task", status="进行中",
                                  owner=self.identity["username"], data={"case_id": self.ids[0]})
            db.add(task)
            await db.flush()
            self.task_id = task.id
            self.paths = []
            for index, record_id in enumerate([self.ids[0], self.ids[1], task.id, self.ids[2]]):
                path = self.root / f"{index}.txt"
                path.write_text("CODEX temporary attachment", encoding="ascii")
                self.paths.append(path)
                db.add(FileAttachment(record_id=record_id, category="案件文档", original_name=path.name,
                                      stored_name=path.name, content_type="text/plain", size=26,
                                      path=str(path), uploader=self.identity["username"]))
            db.add(Notification(source_key="CODEX-task", source_type="task", source_id=task.id,
                                sender="CODEX", recipient="CODEX", notification_type="系统通知", title="CODEX", content="CODEX"))
            db.add(WorkflowEvent(record_id=task.id, action="CODEX", operator="CODEX"))
            await db.commit()

        async def override_db():
            async with self.sessions() as db:
                yield db

        self.overrides = dict(app.dependency_overrides)
        app.dependency_overrides[get_db] = override_db
        app.dependency_overrides[current_identity] = lambda: self.identity
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app, raise_app_exceptions=False), base_url="http://case-batch.test")

    async def asyncTearDown(self):
        await self.client.aclose()
        app.dependency_overrides.clear()
        app.dependency_overrides.update(self.overrides)
        await self.engine.dispose()
        self.root_patch.stop()
        self.temp.cleanup()

    async def delete_batch(self, ids):
        return await self.client.post(f"{settings.api_prefix}/cases/batch-delete", json={"case_ids": ids})

    async def assert_untouched(self):
        async with self.sessions() as db:
            self.assertEqual(await db.scalar(select(func.count()).select_from(BusinessRecord)), 4)
            self.assertEqual(await db.scalar(select(func.count()).select_from(FileAttachment)), 4)
            self.assertEqual(await db.scalar(select(func.count()).select_from(Notification)), 1)
        self.assertTrue(all(path.is_file() for path in self.paths))

    async def test_deletes_entire_selection_and_owned_task_files_only(self):
        response = await self.delete_batch(self.ids[:2])
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json(), {"deleted": 2, "case_ids": self.ids[:2], "cleanup_pending": 0})
        async with self.sessions() as db:
            self.assertEqual(list(await db.scalars(select(BusinessRecord.id))), [self.ids[2]])
            self.assertEqual(await db.scalar(select(func.count()).select_from(Notification)), 0)
            self.assertEqual(await db.scalar(select(func.count()).select_from(WorkflowEvent)), 0)
            self.assertEqual(await db.scalar(select(func.count()).select_from(FileAttachment)), 1)
        self.assertFalse(any(path.exists() for path in self.paths[:3]))
        self.assertTrue(self.paths[3].is_file())

    async def test_empty_duplicate_negative_and_oversized_selection_rejected(self):
        for ids in ([], [self.ids[0], self.ids[0]], [-1], list(range(1, 202))):
            with self.subTest(ids=ids[:3]):
                response = await self.delete_batch(ids)
                self.assertEqual(response.status_code, 422, response.text)
                await self.assert_untouched()

    async def test_missing_or_non_case_record_prevents_entire_batch(self):
        for invalid in (99999, self.task_id):
            response = await self.delete_batch([self.ids[0], invalid])
            self.assertEqual(response.status_code, 404, response.text)
            await self.assert_untouched()

    async def test_archived_and_merged_second_record_prevent_entire_batch(self):
        for status in ("已归档", "已合并"):
            async with self.sessions() as db:
                record = await db.get(BusinessRecord, self.ids[1])
                record.status = status
                await db.commit()
            response = await self.delete_batch(self.ids[:2])
            self.assertEqual(response.status_code, 409, response.text)
            await self.assert_untouched()

    async def test_role_and_invisible_record_rejected(self):
        self.identity = {"username": "CODEX-NO-ACCESS", "role": "user"}
        response = await self.delete_batch(self.ids[:2])
        self.assertEqual(response.status_code, 403, response.text)
        self.identity["role"] = "manager"
        async with self.sessions() as db:
            db.add(User(username=self.identity["username"], role="manager", role_ids=["manager"],
                        department="CODEX-OTHER", password_hash="test-only"))
            await db.commit()
        response = await self.delete_batch(self.ids[:2])
        self.assertEqual(response.status_code, 404, response.text)
        await self.assert_untouched()

    async def test_second_record_failure_rolls_back_flushed_deletes(self):
        original = legal._delete_case_owned_records

        async def fail_second(record, db):
            if record.id == self.ids[1]:
                raise RuntimeError("CODEX injected failure")
            result = await original(record, db)
            await db.flush()
            return result

        with patch.object(legal, "_delete_case_owned_records", fail_second):
            response = await self.delete_batch(self.ids[:2])
        self.assertEqual(response.status_code, 500, response.text)
        await self.assert_untouched()

    async def test_foreign_key_block_returns_conflict_and_rolls_back(self):
        async with self.engine.begin() as connection:
            await connection.execute(text("CREATE TABLE codex_delete_block (case_id INTEGER REFERENCES business_records(id) ON DELETE RESTRICT)"))
            await connection.execute(text("INSERT INTO codex_delete_block VALUES (:id)"), {"id": self.ids[1]})
        response = await self.delete_batch(self.ids[:2])
        self.assertEqual(response.status_code, 409, response.text)
        await self.assert_untouched()

    async def test_single_delete_remains_compatible(self):
        response = await self.client.delete(f"{settings.api_prefix}/cases/{self.ids[0]}")
        self.assertEqual(response.status_code, 204, response.text)
        async with self.sessions() as db:
            self.assertIsNone(await db.get(BusinessRecord, self.ids[0]))
            self.assertIsNotNone(await db.get(BusinessRecord, self.ids[1]))

    async def test_shared_physical_file_is_not_removed(self):
        async with self.sessions() as db:
            other = await db.scalar(select(FileAttachment).where(FileAttachment.record_id == self.ids[2]))
            other.path = str(self.paths[0])
            await db.commit()
        response = await self.delete_batch(self.ids[:2])
        self.assertEqual(response.status_code, 200, response.text)
        self.assertTrue(self.paths[0].is_file())

    async def test_file_cleanup_failure_does_not_report_database_failure(self):
        with patch.object(Path, "unlink", side_effect=PermissionError("CODEX locked file")):
            response = await self.delete_batch(self.ids[:2])
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["cleanup_pending"], 3)
        async with self.sessions() as db:
            self.assertEqual(list(await db.scalars(select(BusinessRecord.id))), [self.ids[2]])


if __name__ == "__main__":
    unittest.main()
