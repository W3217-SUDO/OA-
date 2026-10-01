"""正式自定义文档导入批次的 API 和历史列兼容契约。"""

import importlib
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from uuid import uuid4

import httpx
from fastapi import FastAPI
from sqlalchemy import event, func, inspect, select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database import Base, get_db
from app.main import app
from app.models import (
    BusinessRecord, FileAttachment, IprCaseFileCustomImportBatch,
    IprCaseFileCustomImportCandidate, SystemParameter, User, WorkflowEvent,
)
from app.security import current_identity
from tests.environment import validate_database_url


API = settings.api_prefix


class IprCustomImportBatchContractTest(unittest.IsolatedAsyncioTestCase):
    async def _exercise(self, engine, upload_root: Path) -> None:
        sessions = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
            columns = await connection.run_sync(
                lambda sync_connection: inspect(sync_connection).get_columns("ipr_case_file_custom_import_batches")
            )
        legacy_column = next(column for column in columns if column["name"] == "is_test")
        self.assertFalse(legacy_column["nullable"], "历史 is_test 非空列必须继续兼容插入")

        username = f"oa-test-ipr-{uuid4().hex[:12]}"
        identity = {"username": username, "role": "admin", "display_name": username, "department": "测试部门"}
        async with sessions() as db:
            db.add_all([
                User(username=username, display_name=username, department="测试部门", password_hash="fixture", role="admin"),
                BusinessRecord(
                    module="ipr_case", serial_no=f"IPR-{uuid4().hex[:12]}", title="测试知识产权案件",
                    customer="测试客户", status="在办", owner=username, department="测试部门",
                    data={"legacy_case_no": "123", "case_kind": "专利", "application_no": "TEST-APP-123"},
                ),
                SystemParameter(
                    category="ipr_case_file_type", code="IPR-OTHER", name="普通知识产权案件文档",
                    extra={}, is_active=True,
                ),
            ])
            await db.commit()

        router = importlib.import_module("app.areas.ipr.case_files")
        previous_upload_root = router.UPLOAD_ROOT
        previous_overrides = dict(app.dependency_overrides)
        router.UPLOAD_ROOT = upload_root

        async def override_db():
            async with sessions() as db:
                yield db

        app.dependency_overrides[get_db] = override_db
        app.dependency_overrides[current_identity] = lambda: identity
        client = httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app, raise_app_exceptions=False),
            base_url="http://ipr-custom-import.test",
        )
        try:
            operation = app.openapi()["paths"][f"{API}/ipr/case-files/custom-import-batches"]["post"]
            body_schema = operation["requestBody"]["content"]["multipart/form-data"]["schema"]
            if "$ref" in body_schema:
                body_schema = app.openapi()["components"]["schemas"][body_schema["$ref"].rsplit("/", 1)[-1]]
            self.assertNotIn("test_only", body_schema.get("properties", {}))

            created = await client.post(
                f"{API}/ipr/case-files/custom-import-batches",
                files={"file": ("A123W456.txt", b"formal import source", "text/plain")},
            )
            self.assertEqual(created.status_code, 201, created.text)
            batch_id = created.json()["id"]
            candidate_id = created.json()["candidate"]["id"]
            self.assertEqual(created.json()["candidate"]["status"], "待确认")
            async with sessions() as db:
                batch = await db.get(IprCaseFileCustomImportBatch, batch_id)
                candidate = await db.get(IprCaseFileCustomImportCandidate, candidate_id)
                self.assertIs(batch.is_test, False)
                self.assertEqual(candidate.batch_id, batch_id)
                self.assertEqual(candidate.parsed_case_no, "123")
                self.assertTrue(Path(batch.source_path).is_file())
                self.assertEqual(Path(batch.source_path).read_bytes(), b"formal import source")

            confirmed = await client.post(
                f"{API}/ipr/case-files/custom-import-batches/{batch_id}/confirm",
                json={"candidate_ids": [candidate_id], "comment": "正式批次确认"},
            )
            self.assertEqual(confirmed.status_code, 200, confirmed.text)
            self.assertEqual(confirmed.json()["created"], 1)
            async with sessions() as db:
                candidate = await db.get(IprCaseFileCustomImportCandidate, candidate_id)
                attachment = await db.get(FileAttachment, candidate.attachment_id)
                self.assertEqual(candidate.status, "已导入")
                self.assertEqual(Path(attachment.path).read_bytes(), b"formal import source")
                self.assertEqual(
                    await db.scalar(select(func.count(WorkflowEvent.id)).where(WorkflowEvent.record_id == attachment.record_id)), 1
                )

            before_files = {path.name for path in upload_root.iterdir()}
            repeated = await client.post(
                f"{API}/ipr/case-files/custom-import-batches/{batch_id}/confirm",
                json={"candidate_ids": [candidate_id], "comment": "重复确认"},
            )
            self.assertEqual(repeated.status_code, 409, repeated.text)
            for filename, content in (("invalid.exe", b"invalid"), ("A123W999.txt", b"")):
                rejected = await client.post(
                    f"{API}/ipr/case-files/custom-import-batches",
                    files={"file": (filename, content, "application/octet-stream")},
                )
                self.assertEqual(rejected.status_code, 422, rejected.text)
            self.assertEqual({path.name for path in upload_root.iterdir()}, before_files)
            async with sessions() as db:
                self.assertEqual(await db.scalar(select(func.count(IprCaseFileCustomImportBatch.id))), 1)
                self.assertEqual(await db.scalar(select(func.count(IprCaseFileCustomImportCandidate.id))), 1)
                self.assertEqual(await db.scalar(select(func.count(FileAttachment.id))), 1)
                self.assertEqual(await db.scalar(select(func.count(WorkflowEvent.id))), 1)

            def reject_batch_insert(connection, cursor, statement, parameters, context, executemany):
                if "insert into ipr_case_file_custom_import_batches" in statement.lower():
                    raise RuntimeError("模拟批次数据库写入失败")

            event.listen(engine.sync_engine, "before_cursor_execute", reject_batch_insert)
            try:
                failed_write = await client.post(
                    f"{API}/ipr/case-files/custom-import-batches",
                    files={"file": ("A123W789.txt", b"failure must clean source", "text/plain")},
                )
            finally:
                event.remove(engine.sync_engine, "before_cursor_execute", reject_batch_insert)
            self.assertEqual(failed_write.status_code, 500, failed_write.text)
            self.assertEqual({path.name for path in upload_root.iterdir()}, before_files)
            async with sessions() as db:
                self.assertEqual(await db.scalar(select(func.count(IprCaseFileCustomImportBatch.id))), 1)
                self.assertEqual(await db.scalar(select(func.count(IprCaseFileCustomImportCandidate.id))), 1)

            ignored_legacy_form = await client.post(
                f"{API}/ipr/case-files/custom-import-batches",
                data={"test_only": "true"},
                files={"file": ("A999W888.txt", b"formal despite legacy form", "text/plain")},
            )
            self.assertEqual(ignored_legacy_form.status_code, 201, ignored_legacy_form.text)
            async with sessions() as db:
                batch = await db.get(IprCaseFileCustomImportBatch, ignored_legacy_form.json()["id"])
                self.assertIs(batch.is_test, False)

            smoke_batch = await client.post(
                f"{API}/ipr/case-files/custom-import-batches",
                files={"file": ("A0000000001W0000000001.txt", b"SMOKE custom import valid source", "text/plain")},
            )
            self.assertEqual(smoke_batch.status_code, 201, smoke_batch.text)
            smoke_batch_id = smoke_batch.json()["id"]
            async with sessions() as db:
                smoke_source_path = Path((await db.get(IprCaseFileCustomImportBatch, smoke_batch_id)).source_path)

            # 清理路由只存在于独立测试入口；正式批次必须带烟测源文件标记才可清理。
            from tests import cleanup_router

            cleanup_root = cleanup_router.UPLOAD_ROOT
            cleanup_router.UPLOAD_ROOT = upload_root
            try:
                cleanup_app = FastAPI()
                cleanup_app.include_router(cleanup_router.router)
                cleanup_app.dependency_overrides[get_db] = override_db
                cleanup_app.dependency_overrides[current_identity] = lambda: identity
                async with httpx.AsyncClient(
                    transport=httpx.ASGITransport(app=cleanup_app), base_url="http://ipr-custom-cleanup.test"
                ) as cleanup_client:
                    rejected = await cleanup_client.delete(
                        f"{API}/testing/ipr-case-file-custom-import-batches/{batch_id}"
                    )
                    self.assertEqual(rejected.status_code, 404, rejected.text)
                    removed = await cleanup_client.delete(
                        f"{API}/testing/ipr-case-file-custom-import-batches/{smoke_batch_id}"
                    )
                    self.assertEqual(removed.status_code, 204, removed.text)
            finally:
                cleanup_router.UPLOAD_ROOT = cleanup_root
            self.assertFalse(smoke_source_path.exists())
            async with sessions() as db:
                self.assertIsNone(await db.get(IprCaseFileCustomImportBatch, smoke_batch_id))
                self.assertEqual(
                    await db.scalar(select(func.count(IprCaseFileCustomImportCandidate.id)).where(
                        IprCaseFileCustomImportCandidate.batch_id == smoke_batch_id
                    )), 0,
                )
        finally:
            await client.aclose()
            app.dependency_overrides.clear()
            app.dependency_overrides.update(previous_overrides)
            router.UPLOAD_ROOT = previous_upload_root

    async def test_sqlite_real_api_and_legacy_not_null_column(self) -> None:
        engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool,
        )
        try:
            with TemporaryDirectory(prefix="oa-test-ipr-custom-") as directory:
                await self._exercise(engine, Path(directory))
        finally:
            await engine.dispose()

    async def test_postgres_real_api_and_legacy_not_null_column(self) -> None:
        url = os.environ.get("OA_TEST_POSTGRES_URL", "")
        if not url:
            self.skipTest("需要 OA_TEST_POSTGRES_URL 指向本机 oa_test_* 独立库")
        validate_database_url(url)
        schema = f"oa_test_ipr_{uuid4().hex[:12]}"
        admin_engine = create_async_engine(url)
        engine = None
        schema_created = False
        try:
            async with admin_engine.begin() as connection:
                await connection.execute(text(f"CREATE SCHEMA {schema}"))
            schema_created = True
            engine = create_async_engine(url, connect_args={"server_settings": {"search_path": schema}})
            with TemporaryDirectory(prefix="oa-test-ipr-custom-") as directory:
                await self._exercise(engine, Path(directory))
        finally:
            if engine is not None:
                await engine.dispose()
            if schema_created:
                async with admin_engine.begin() as connection:
                    await connection.execute(text(f"DROP SCHEMA {schema} CASCADE"))
            await admin_engine.dispose()
