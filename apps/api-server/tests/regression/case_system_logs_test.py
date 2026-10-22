"""案件系统日志真实隔离数据库与 ASGI 接口回归。"""

import os
import tempfile
import unittest
from datetime import datetime, timezone

os.environ["APP_ENV"] = "testing"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["SECRET_KEY"] = "CODEXDOCLOG-isolated-test-secret-key-only"
_uploads = tempfile.TemporaryDirectory(prefix="oa-test-CODEXDOCLOG-")
os.environ["UPLOAD_ROOT"] = _uploads.name

import httpx
from fastapi import FastAPI
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.areas.legal.case_events import router
from app.config import settings
from app.database import Base, get_db
from app.models import BusinessRecord, JobRole, LegacyCaseLog, User, WorkflowEvent
from app.security import create_token, current_identity

ADMIN = {"username": "CODEXDOCLOG-admin", "role": "admin", "department": "CODEXDOCLOG"}
OUTSIDER = {"username": "CODEXDOCLOG-outsider", "role": "user", "department": "CODEXDOCLOG-other"}


class CaseSystemLogsTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.identity = ADMIN
        self.app = FastAPI()
        self.app.include_router(router)
        self.app.dependency_overrides[get_db] = self.session
        self.app.dependency_overrides[current_identity] = lambda: self.identity
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=self.app), base_url="http://CODEXDOCLOG.test")
        async with self.sessions() as db:
            db.add_all([User(username=item["username"], display_name="日志人员", department=item["department"], role=item["role"], password_hash="unused", is_active=True) for item in (ADMIN, OUTSIDER)])
            db.add(JobRole(code="CODEXDOCLOG-denied", name="日志无权岗位", permissions=[], data_scope="本人及共享数据", is_active=True))
            outsider = await db.scalar(select(User).where(User.username == OUTSIDER["username"]))
            outsider.profile = {"permission_role_code": "CODEXDOCLOG-denied"}
            records = [BusinessRecord(module="case", serial_no=f"CODEXDOCLOG-{name}", title=name, owner=ADMIN["username"], department="CODEXDOCLOG", status="在办", data={}) for name in ("root", "merged", "other", "empty")]
            db.add_all(records)
            await db.flush()
            root, merged, other, empty = records
            root.data = {"merged_sources": [{"id": merged.id, "serial_no": merged.serial_no, "data": {}}, {"id": merged.id, "serial_no": merged.serial_no, "data": {}}]}
            self.ids = [record.id for record in records]
            db.add_all([
                WorkflowEvent(id=101, record_id=root.id, action="上传归档材料", operator=ADMIN["username"], comment="CODEXDOCLOG-current", created_at=datetime(2026, 10, 1, 12, tzinfo=timezone.utc)),
                WorkflowEvent(id=102, record_id=merged.id, action="修改法院信息", operator=ADMIN["username"], comment="CODEXDOCLOG-merged", created_at=datetime(2026, 10, 1, 10, tzinfo=timezone.utc)),
                WorkflowEvent(id=103, record_id=other.id, action="其他案件", operator=ADMIN["username"], comment="不可串案"),
            ])
            for log_id, record, log_type, active, hour in [
                (101, root, 2, None, 21), (102, root, 2, "T", 19),
                (103, merged, 2, "T", 18), (104, root, 1, "T", 23),
                (105, root, 2, "F", 23), (-101, root, 2, "T", 23),
                (106, other, 2, "T", 23), (107, root, 2, "T", None),
            ]:
                db.add(LegacyCaseLog(LogId=log_id, CaseNo=record.serial_no, LogType=log_type, IsActived=active, CreateUser=ADMIN["username"], CreateTime=datetime(2026, 10, 1, hour) if hour is not None else None, Content=f"CODEXDOCLOG-{log_id}原始操作"))
            await db.commit()

    async def session(self):
        async with self.sessions() as db:
            yield db

    async def asyncTearDown(self):
        await self.client.aclose()
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.drop_all)
        await self.engine.dispose()

    def url(self, suffix="", index=0):
        return f"{settings.api_prefix}/cases/{self.ids[index]}/system-logs{suffix}"

    async def test_mixed_sources_pagination_sort_names_and_exact_originals(self):
        pages = []
        for page in (1, 2, 3):
            response = await self.client.get(self.url(), params={"page": page, "page_size": 2})
            self.assertEqual(response.status_code, 200, response.text)
            body = response.json()
            self.assertEqual((body["total"], body["page"], body["pages"]), (6, page, 3))
            pages.extend(body["items"])
        self.assertEqual([item["id"] for item in pages], ["legacy:101", "current:101", "legacy:102", "legacy:103", "current:102", "legacy:107"])
        self.assertEqual(len({item["id"] for item in pages}), 6)
        self.assertEqual(pages[0]["created_at"], "2026-10-01T21:00:00+08:00")
        self.assertEqual(pages[1]["created_at"], "2026-10-01T20:00:00+08:00")
        self.assertEqual(pages[0]["operator_display_name"], "日志人员")
        self.assertEqual(pages[0]["comment"], "CODEXDOCLOG-101原始操作")
        self.assertEqual(pages[3]["source_case_no"], "CODEXDOCLOG-merged")

    async def test_detail_checks_source_case_membership_and_log_type(self):
        for source, log_id in [("current", 101), ("legacy", 101), ("legacy", 103)]:
            result = await self.client.get(self.url(f"/{source}/{log_id}"))
            self.assertEqual(result.status_code, 200, result.text)
            self.assertEqual(result.json()["id"], f"{source}:{log_id}")
        for source, log_id in [("legacy", 104), ("legacy", 105), ("legacy", -101), ("legacy", 106), ("current", 103), ("current", 99999)]:
            result = await self.client.get(self.url(f"/{source}/{log_id}"))
            self.assertEqual(result.status_code, 404, result.text)

    async def test_read_permission_denies_list_and_detail(self):
        self.identity = OUTSIDER
        for suffix in ("", "/legacy/101", "/current/101"):
            result = await self.client.get(self.url(suffix))
            self.assertEqual(result.status_code, 404, result.text)
            self.assertEqual(result.json()["detail"], "记录不存在或无权访问")

    async def test_empty_invalid_and_page_boundary(self):
        response = await self.client.get(self.url(index=3))
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json(), {"items": [], "total": 0, "page": 1, "page_size": 15, "pages": 1})
        response = await self.client.get(self.url(), params={"page": 999, "page_size": 2})
        self.assertEqual(response.json()["page"], 3)
        for params in ({"page": 0}, {"page_size": 0}, {"page_size": 101}):
            self.assertEqual((await self.client.get(self.url(), params=params)).status_code, 422)
        self.assertEqual((await self.client.get(self.url("/unknown/101"))).status_code, 422)
        self.assertEqual((await self.client.get(f"{settings.api_prefix}/cases/99999/system-logs")).status_code, 404)

    async def test_reads_preserve_all_rows(self):
        async with self.sessions() as db:
            before = [await db.scalar(select(func.count()).select_from(model)) for model in (BusinessRecord, WorkflowEvent, LegacyCaseLog)]
        await self.client.get(self.url())
        await self.client.get(self.url("/legacy/101"))
        async with self.sessions() as db:
            after = [await db.scalar(select(func.count()).select_from(model)) for model in (BusinessRecord, WorkflowEvent, LegacyCaseLog)]
        self.assertEqual(before, after)
        self.assertEqual(after, [4, 3, 8])

    async def test_real_token_menu_capability_preserves_case_scope(self):
        async with self.sessions() as db:
            db.add(JobRole(code="CODEXDOCLOG-reader", name="日志案件只读岗位", permissions=["case-mine"], data_scope="本人及共享数据", is_active=True))
            db.add(User(username="CODEXDOCLOG-reader", display_name="案件只读人员", department="CODEXDOCLOG", role="user", password_hash="unused", is_active=True, profile={"permission_role_code": "CODEXDOCLOG-reader"}))
            root = await db.get(BusinessRecord, self.ids[0])
            root.owner = "CODEXDOCLOG-reader"
            await db.commit()
        self.app.dependency_overrides.pop(current_identity)
        headers = {"Authorization": "Bearer " + create_token("CODEXDOCLOG-reader", "user")}
        response = await self.client.get(self.url(), headers=headers)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["total"], 6)
        self.assertEqual((await self.client.get(self.url("/legacy/103"), headers=headers)).status_code, 200)
        self.assertEqual((await self.client.get(self.url(index=2), headers=headers)).status_code, 404)
        denied_headers = {"Authorization": "Bearer " + create_token(OUTSIDER["username"], "user")}
        self.assertEqual((await self.client.get(self.url(), headers=denied_headers)).status_code, 404)
        self.assertEqual((await self.client.get(self.url())).status_code, 401)


def tearDownModule():
    _uploads.cleanup()


if __name__ == "__main__":
    unittest.main()
