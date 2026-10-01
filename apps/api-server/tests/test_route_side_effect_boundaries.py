"""验证列表读取只读，以及官文候选导入的文件与数据库原子性。"""

import os
import unittest
from datetime import date, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import httpx
from sqlalchemy import func, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

import app.areas.ipr.router as ipr_router
from app.config import settings
from app.core.system import _run_business_rules_once
from app.database import Base, get_db
from app.main import app
from app.models import (
    BusinessRecord,
    IprCaseWarning,
    IprCaseWarningRule,
    IprOfficialImportBatch,
    IprOfficialImportCandidate,
    Notification,
    User,
    WorkflowEvent,
)
from app.security import current_identity
from tests.environment import validate_database_url


API = settings.api_prefix
POSTGRES_URL = os.environ.get("OA_ROUTE_EFFECTS_POSTGRES_URL", "")
ADMIN = {"username": "route-effects-admin", "role": "admin", "role_ids": ["admin"], "_actual_role_ids": ["admin"]}


class ControlledSession(AsyncSession):
    async def flush(self, objects=None):
        if self.info.get("fail_stage") == "flush" and any(isinstance(row, IprOfficialImportBatch) for row in self.new):
            raise RuntimeError("测试注入官文批次 flush 失败")
        return await super().flush(objects)

    async def commit(self):
        self.info["commit_count"] = self.info.get("commit_count", 0) + 1
        if self.info.get("fail_stage") == "commit":
            raise RuntimeError("测试注入官文批次 commit 失败")
        return await super().commit()


class RouteSideEffectBoundariesTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temporary = TemporaryDirectory(prefix="oa-test-route-effects-")
        self.upload_root = Path(self.temporary.name) / "uploads"
        self.upload_root.mkdir()
        self.schema = ""
        self.admin_engine = None
        if POSTGRES_URL:
            validate_database_url(POSTGRES_URL)
            url = make_url(POSTGRES_URL)
            if url.drivername != "postgresql+asyncpg" or not (url.database or "").startswith("oa_test_"):
                raise RuntimeError("路由副作用测试仅允许本机专用 PostgreSQL 测试库")
            self.schema = f"oa_test_route_effects_{uuid4().hex[:12]}"
            self.admin_engine = create_async_engine(POSTGRES_URL)
            async with self.admin_engine.begin() as connection:
                await connection.execute(text(f"CREATE SCHEMA {self.schema}"))
            self.engine = create_async_engine(
                POSTGRES_URL,
                connect_args={"server_settings": {"search_path": self.schema}},
            )
        else:
            self.engine = create_async_engine(
                "sqlite+aiosqlite:///:memory:",
                connect_args={"check_same_thread": False},
                poolclass=StaticPool,
            )
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=ControlledSession)
        async with self.sessions() as db:
            db.add(User(
                username=ADMIN["username"], display_name="路由边界管理员",
                department="测试部", role="admin", password_hash="test-only-hash", is_active=True,
            ))
            clue = BusinessRecord(
                module="clue", serial_no="ROUTE-EFFECTS-CLUE", title="已取证线索",
                status="待公证", owner=ADMIN["username"], department="测试部", data={},
            )
            case = BusinessRecord(
                module="case", serial_no="ROUTE-EFFECTS-CASE", title="等待公证案件",
                status="等待公证书", owner=ADMIN["username"], department="测试部", data={"case_type": "民事案件"},
            )
            db.add_all([clue, case])
            await db.flush()
            clue.data = {"converted_case_id": case.id}
            notary = BusinessRecord(
                module="notary", serial_no="ROUTE-EFFECTS-NOTARY", title="超期待审核公证",
                status="待审核", owner=ADMIN["username"], department="测试部",
                data={"clue_id": clue.id, "review_due_date": (date.today() - timedelta(days=1)).isoformat()},
            )
            ipr_case = BusinessRecord(
                module="ipr_case", serial_no="ROUTE-EFFECTS-IPR", title="知识产权期限案件",
                status="在办", owner=ADMIN["username"], department="测试部",
                data={"application_no": "ROUTE-EFFECTS-APPLICATION", "case_kind": "专利", "deadline": (date.today() + timedelta(days=2)).isoformat()},
            )
            db.add_all([notary, ipr_case, IprCaseWarningRule(
                name="路由边界期限预警", time_node="case_deadline", days_before=5,
                is_active=True, created_by=ADMIN["username"], updated_by=ADMIN["username"],
            )])
            await db.commit()
            self.case_id = case.id
            self.notary_id = notary.id
            self.clue_id = clue.id
        self.fail_stage = ""
        self.request_sessions = []
        self.previous_overrides = dict(app.dependency_overrides)

        async def override_db():
            async with self.sessions() as db:
                db.info["fail_stage"] = self.fail_stage
                self.request_sessions.append(db)
                yield db

        app.dependency_overrides[get_db] = override_db
        app.dependency_overrides[current_identity] = lambda: ADMIN
        self.upload_patch = patch.object(ipr_router, "UPLOAD_ROOT", self.upload_root)
        self.upload_patch.start()
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://route-effects.test")

    async def asyncTearDown(self):
        await self.client.aclose()
        self.upload_patch.stop()
        app.dependency_overrides.clear()
        app.dependency_overrides.update(self.previous_overrides)
        await self.engine.dispose()
        if self.admin_engine is not None:
            async with self.admin_engine.begin() as connection:
                await connection.execute(text(f"DROP SCHEMA {self.schema} CASCADE"))
            await self.admin_engine.dispose()
        self.temporary.cleanup()

    async def count(self, model):
        async with self.sessions() as db:
            return int(await db.scalar(select(func.count()).select_from(model)) or 0)

    async def test_notary_case_get_is_read_only_and_registered_rule_is_idempotent(self):
        for module in ("notary", "case"):
            response = await self.client.get(f"{API}/records", params={"module": module})
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(self.request_sessions[-1].info.get("commit_count", 0), 0)
        async with self.sessions() as db:
            self.assertEqual((await db.get(BusinessRecord, self.notary_id)).status, "待审核")
            self.assertEqual((await db.get(BusinessRecord, self.case_id)).status, "等待公证书")
            self.assertEqual(await db.scalar(select(func.count()).select_from(WorkflowEvent)), 0)

        with patch("app.core.system.SessionLocal", self.sessions), \
             patch("app.core.tasks._apply_task_auto_completion", AsyncMock(return_value=False)), \
             patch("app.core.tasks._apply_task_overdue_performance", AsyncMock(return_value=False)), \
             patch("app.core.tasks._apply_case_automatic_task_rules", AsyncMock(return_value=False)):
            await _run_business_rules_once()
            async with self.sessions() as db:
                self.assertEqual((await db.get(BusinessRecord, self.notary_id)).status, "审核通过")
                self.assertEqual((await db.get(BusinessRecord, self.case_id)).status, "新案待分配")
                self.assertEqual((await db.get(BusinessRecord, self.clue_id)).status, "已转案件")
                self.assertEqual(await db.scalar(select(func.count()).select_from(WorkflowEvent)), 3)
            await _run_business_rules_once()
        self.assertEqual(await self.count(WorkflowEvent), 3)
        response = await self.client.get(f"{API}/records", params={"module": "notary"})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(self.request_sessions[-1].info.get("commit_count", 0), 0)
        self.assertEqual(await self.count(WorkflowEvent), 3)

    async def test_warning_get_is_read_only_and_explicit_generate_remains_idempotent(self):
        first = await self.client.get(f"{API}/ipr/warnings")
        self.assertEqual(first.status_code, 200, first.text)
        self.assertEqual(first.json()["total"], 0)
        self.assertEqual(self.request_sessions[-1].info.get("commit_count", 0), 0)
        self.assertEqual(await self.count(IprCaseWarning), 0)
        self.assertEqual(await self.count(Notification), 0)

        generated = await self.client.post(f"{API}/ipr/warnings/generate")
        self.assertEqual(generated.status_code, 200, generated.text)
        self.assertEqual(generated.json()["created"], 1)
        self.assertEqual(await self.count(IprCaseWarning), 1)
        self.assertEqual(await self.count(Notification), 1)
        for _ in range(2):
            response = await self.client.get(f"{API}/ipr/warnings")
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(response.json()["total"], 1)
            self.assertEqual(self.request_sessions[-1].info.get("commit_count", 0), 0)
        self.assertEqual(await self.count(IprCaseWarning), 1)
        self.assertEqual(await self.count(Notification), 1)
        repeated = await self.client.post(f"{API}/ipr/warnings/generate")
        self.assertEqual(repeated.status_code, 200, repeated.text)
        self.assertEqual(repeated.json()["created"], 0)

    def official_csv(self):
        return ("申请号,通知书名称,收发文日,办理期限\n"
                f"ROUTE-EFFECTS-APPLICATION,补正通知书,{date.today().isoformat()},{(date.today() + timedelta(days=7)).isoformat()}\n").encode("utf-8")

    async def post_official_csv(self):
        return await self.client.post(
            f"{API}/ipr/official-files/import-batches",
            files={"file": ("route-effects.csv", self.official_csv(), "text/csv")},
        )

    async def test_official_import_retains_file_only_after_commit(self):
        response = await self.post_official_csv()
        self.assertEqual(response.status_code, 201, response.text)
        self.assertEqual(response.json()["total_count"], 1)
        self.assertEqual(response.json()["error_count"], 0)
        async with self.sessions() as db:
            batch = await db.get(IprOfficialImportBatch, response.json()["id"])
            candidate = await db.scalar(select(IprOfficialImportCandidate).where(IprOfficialImportCandidate.batch_id == batch.id))
            self.assertEqual(candidate.status, "待确认")
            self.assertEqual(candidate.application_no, "ROUTE-EFFECTS-APPLICATION")
            self.assertEqual(Path(batch.source_path).read_bytes(), self.official_csv())
        self.assertEqual(len(list(self.upload_root.iterdir())), 1)

    async def test_official_import_flush_and_commit_failures_leave_no_rows_or_file(self):
        for stage in ("flush", "commit"):
            with self.subTest(stage=stage):
                self.fail_stage = stage
                with self.assertRaisesRegex(RuntimeError, f"{stage} 失败"):
                    await self.post_official_csv()
                self.fail_stage = ""
                self.assertEqual(await self.count(IprOfficialImportBatch), 0)
                self.assertEqual(await self.count(IprOfficialImportCandidate), 0)
                self.assertEqual(list(self.upload_root.iterdir()), [])

    async def test_official_import_partial_file_failure_cleans_file_and_database(self):
        original_write = Path.write_bytes

        def fail_after_partial_write(path, content):
            original_write(path, content[:8])
            raise OSError("测试注入源文件写入失败")

        with patch.object(Path, "write_bytes", fail_after_partial_write):
            with self.assertRaisesRegex(OSError, "源文件写入失败"):
                await self.post_official_csv()
        self.assertEqual(await self.count(IprOfficialImportBatch), 0)
        self.assertEqual(await self.count(IprOfficialImportCandidate), 0)
        self.assertEqual(list(self.upload_root.iterdir()), [])
