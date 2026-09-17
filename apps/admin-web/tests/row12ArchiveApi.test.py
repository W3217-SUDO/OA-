"""第12行案件归档审核队列的接口与权限回归。"""
import unittest
from unittest.mock import AsyncMock, patch

import httpx
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.core.case_archive import ArchiveSearchInput, search_archive_cases
from app.database import Base, get_db
from app.main import app
from app.models import BusinessRecord, User
from app.security import current_identity


API = settings.api_prefix
ADMIN = {"username": "CODEX-0917-archive-admin", "role": "admin", "display_name": "归档管理员", "department": "测试部"}
REVIEWER = {"username": "CODEX-0917-archive-reviewer", "role": "user", "display_name": "归档审核人", "department": "测试部"}


def archive_case(serial_no, status, data=None, owner="case-owner"):
    return BusinessRecord(
        module="case",
        serial_no=serial_no,
        title=serial_no,
        customer="第12行测试客户",
        status=status,
        owner=owner,
        department="测试部",
        data=data or {},
    )


class CaseArchiveQueueRow12Test(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with self.sessions() as db:
            records = [
                User(username=ADMIN["username"], display_name=ADMIN["display_name"], role="admin", department="测试部", password_hash="x", is_active=True),
                User(username=REVIEWER["username"], display_name=REVIEWER["display_name"], role="user", department="测试部", password_hash="x", is_active=True),
                archive_case("CODEX-0917-ARCHIVE-HISTORY", "归档审核", {"archive_submitter": "legacy-submitter"}),
                archive_case("CODEX-0917-ARCHIVE-PENDING", "待归档审核", {"archive_submitter": "normal-submitter"}),
                archive_case("CODEX-0917-ARCHIVE-INTERNAL", "亏损内审", {"archive_submitter": "loss-submitter"}),
                archive_case("CODEX-0917-ARCHIVE-AUDIT", "亏损审核", {"archive_submitter": "loss-submitter", "archive_internal_reviewer": "other-reviewer"}),
                archive_case("CODEX-0917-ARCHIVE-DONE", "已归档", {"archive_submitter": "normal-submitter"}),
                archive_case("CODEX-0917-ARCHIVE-LOSS-DONE", "亏损归档", {"archive_submitter": "loss-submitter"}),
                archive_case("CODEX-0917-ARCHIVE-REFUSED", "执行", {"archive_submitter": ADMIN["username"], "archive_reject_reason": "正常归档拒绝"}),
                archive_case("CODEX-0917-ARCHIVE-HISTORY-REFUSED", "归档拒绝", {"archive_submitter": "legacy-submitter"}),
                archive_case("CODEX-0917-ARCHIVE-LOSS-REFUSED", "亏损归档拒绝", {"archive_submitter": "loss-submitter"}),
                archive_case("CODEX-0917-ARCHIVE-ASSIGNED", "待归档审核", {"archive_submitter": "normal-submitter", "archive_reviewer": REVIEWER["username"]}),
                archive_case("CODEX-0917-ARCHIVE-OWNED", "待归档审核", {"archive_submitter": "normal-submitter"}, owner=REVIEWER["username"]),
                archive_case("CODEX-0917-ARCHIVE-SELF", "待归档审核", {"archive_submitter": ADMIN["username"]}),
            ]
            db.add_all(records)
            await db.commit()
            self.self_submitted_case_id = next(record.id for record in records if isinstance(record, BusinessRecord) and record.serial_no == "CODEX-0917-ARCHIVE-SELF")
            self.historical_case_id = next(record.id for record in records if isinstance(record, BusinessRecord) and record.serial_no == "CODEX-0917-ARCHIVE-HISTORY")

        async def database():
            async with self.sessions() as db:
                yield db

        self.previous_overrides = dict(app.dependency_overrides)
        app.dependency_overrides[get_db] = database
        app.dependency_overrides[current_identity] = lambda: ADMIN
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://archive-row12.test")

    async def asyncTearDown(self):
        await self.client.aclose()
        app.dependency_overrides.clear()
        app.dependency_overrides.update(self.previous_overrides)
        await self.engine.dispose()

    async def test_seven_menu_queues_are_distinct_and_history_is_visible_to_admin(self):
        expected = {
            "pending": {"CODEX-0917-ARCHIVE-HISTORY", "CODEX-0917-ARCHIVE-PENDING", "CODEX-0917-ARCHIVE-ASSIGNED", "CODEX-0917-ARCHIVE-OWNED", "CODEX-0917-ARCHIVE-SELF"},
            "loss_internal": {"CODEX-0917-ARCHIVE-INTERNAL"},
            "loss_audit": {"CODEX-0917-ARCHIVE-AUDIT"},
            "done": {"CODEX-0917-ARCHIVE-DONE"},
            "loss_done": {"CODEX-0917-ARCHIVE-LOSS-DONE"},
            "refused": {"CODEX-0917-ARCHIVE-REFUSED", "CODEX-0917-ARCHIVE-HISTORY-REFUSED"},
            "loss_refused": {"CODEX-0917-ARCHIVE-LOSS-REFUSED"},
        }
        for view, serial_nos in expected.items():
            response = await self.client.post(f"{API}/cases/archive/search", json={"view": view, "page_size": 100})
            self.assertEqual(response.status_code, 200, response.text)
            payload = response.json()
            self.assertEqual(payload["total"], len(serial_nos), payload)
            self.assertEqual({item["serial_no"] for item in payload["items"]}, serial_nos)

    async def test_non_administrator_sees_only_assigned_or_owned_pending_cases(self):
        async with self.sessions() as db:
            body = ArchiveSearchInput(view="pending", page_size=100)
            with patch("app.core.permissions._require_record_module_menu", new=AsyncMock()), \
                 patch("app.core.permissions._record_scope_conditions", new=AsyncMock(return_value=[])), \
                 patch("app.core.cases._case_action_granted", new=AsyncMock(return_value=True)):
                result = await search_archive_cases(body, REVIEWER, db)
        self.assertEqual(
            {item["serial_no"] for item in result["items"]},
            {"CODEX-0917-ARCHIVE-ASSIGNED", "CODEX-0917-ARCHIVE-OWNED"},
        )

    async def test_export_uses_the_same_loss_internal_queue(self):
        response = await self.client.post(
            f"{API}/cases/archive/export",
            json={"view": "loss_internal", "format": "csv"},
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertIn("CODEX-0917-ARCHIVE-INTERNAL", response.content.decode("utf-8-sig"))

    async def test_administrator_can_see_self_submitted_case_but_review_action_is_rejected_without_writing(self):
        listing = await self.client.post(f"{API}/cases/archive/search", json={"view": "pending", "page_size": 100})
        self.assertEqual(listing.status_code, 200, listing.text)
        self.assertIn("CODEX-0917-ARCHIVE-SELF", {item["serial_no"] for item in listing.json()["items"]})
        response = await self.client.post(
            f"{API}/cases/{self.self_submitted_case_id}/archive/review",
            json={"approved": False, "comment": "本人不能审核"},
        )
        self.assertEqual(response.status_code, 403, response.text)
        async with self.sessions() as db:
            record = await db.get(BusinessRecord, self.self_submitted_case_id)
            self.assertEqual(record.status, "待归档审核")
            self.assertNotIn("archive_reviewer", record.data)

    async def test_historical_archive_review_can_be_rejected_through_the_review_flow(self):
        response = await self.client.post(
            f"{API}/cases/{self.historical_case_id}/archive/review",
            json={"approved": False, "comment": "历史归档审核驳回"},
        )
        self.assertEqual(response.status_code, 200, response.text)
        async with self.sessions() as db:
            record = await db.get(BusinessRecord, self.historical_case_id)
            self.assertEqual(record.status, "执行")
            self.assertEqual(record.data["archive_reviewer"], ADMIN["username"])
            self.assertEqual(record.data["archive_reject_reason"], "历史归档审核驳回")


if __name__ == "__main__":
    unittest.main()
