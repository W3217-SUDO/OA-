"""Ordinary case assisted-fee lifecycle contract."""

from datetime import datetime, timezone
import unittest

import httpx
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database import Base, get_db
from app.main import app
from app.models import BusinessRecord, CaseAssistedFee, User, WorkflowEvent
from app.security import current_identity


API = settings.api_prefix
IDENTITY = {
    "username": "case-assisted-admin",
    "role": "admin",
    "display_name": "Case Assisted Admin",
    "department": "Litigation",
}
DENIED_IDENTITY = {
    "username": "case-assisted-denied",
    "role": "user",
    "display_name": "Case Assisted Denied",
    "department": "Litigation",
}


class CaseAssistedFeeLifecycleContract(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            connect_args={"check_same_thread": False}, poolclass=StaticPool,
        )
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with self.sessions() as db:
            case = BusinessRecord(
                module="case", serial_no="CODEX-ASSISTED-FEE-001", title="assisted fee test",
                customer="CODEX Customer", status="在办", owner=IDENTITY["username"],
                department=IDENTITY["department"], data={"case_type": "民事案件"},
                created_at=datetime(2026, 9, 5, tzinfo=timezone.utc),
            )
            other_case = BusinessRecord(
                module="case", serial_no="CODEX-ASSISTED-FEE-002", title="other case",
                customer="CODEX Customer", status="在办", owner=IDENTITY["username"],
                department=IDENTITY["department"], data={"case_type": "民事案件"},
            )
            denied_case = BusinessRecord(
                module="case", serial_no="CODEX-ASSISTED-FEE-003", title="denied case",
                customer="CODEX Customer", status="在办", owner=DENIED_IDENTITY["username"],
                department=DENIED_IDENTITY["department"], data={"case_type": "民事案件"},
            )
            archived_case = BusinessRecord(
                module="case", serial_no="CODEX-ASSISTED-FEE-004", title="archived case",
                customer="CODEX Customer", status="已归档", owner=IDENTITY["username"],
                department=IDENTITY["department"], data={"case_type": "民事案件"},
            )
            db.add_all([
                case, other_case, denied_case, archived_case,
                User(
                    username=DENIED_IDENTITY["username"], display_name=DENIED_IDENTITY["display_name"],
                    department=DENIED_IDENTITY["department"], password_hash="test", role="user",
                ),
            ])
            await db.commit()
            self.case_id, self.other_case_id = case.id, other_case.id
            self.denied_case_id = denied_case.id
            self.archived_case_id = archived_case.id
        app.dependency_overrides[get_db] = self.override_db
        app.dependency_overrides[current_identity] = lambda: IDENTITY
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://case-assisted.test")

    async def asyncTearDown(self):
        await self.client.aclose()
        app.dependency_overrides.clear()
        await self.engine.dispose()

    async def override_db(self):
        async with self.sessions() as db:
            yield db

    async def test_crud_confirm_is_case_bound_and_audited(self):
        base = f"{API}/cases/{self.case_id}/assisted-fees"
        invalid_type = await self.client.post(base, json={"assisted_type": "   "})
        self.assertEqual(invalid_type.status_code, 422, invalid_type.text)
        invalid_amount = await self.client.post(base, json={"assisted_type": "资助", "amount": -1})
        self.assertEqual(invalid_amount.status_code, 422, invalid_amount.text)

        deletable = await self.client.post(base, json={"assisted_type": "待删除资助"})
        self.assertEqual(deletable.status_code, 201, deletable.text)
        deleted = await self.client.delete(f"{base}/{deletable.json()['id']}")
        self.assertEqual(deleted.status_code, 204, deleted.text)

        created = await self.client.post(base, json={"assisted_type": "上海市资助", "remark": "首次申请"})
        self.assertEqual(created.status_code, 201, created.text)
        row = created.json()
        self.assertIsNone(row["amount"])
        self.assertEqual(row["status"], "待办理")
        fee_id = row["id"]

        updated = await self.client.put(f"{base}/{fee_id}", json={"amount": 1200, "remark": "补充金额"})
        self.assertEqual(updated.status_code, 200, updated.text)
        self.assertEqual(updated.json()["amount"], 1200)
        self.assertEqual(updated.json()["remark"], "补充金额")

        cross_case = await self.client.post(
            f"{API}/cases/{self.other_case_id}/assisted-fees/{fee_id}/confirm", json={},
        )
        self.assertEqual(cross_case.status_code, 404, cross_case.text)

        confirmed = await self.client.post(f"{base}/{fee_id}/confirm", json={"confirmed_date": "2026-09-05", "remark": "已核实"})
        self.assertEqual(confirmed.status_code, 200, confirmed.text)
        self.assertEqual(confirmed.json()["status"], "已办理")
        self.assertEqual(confirmed.json()["confirmed_user"], IDENTITY["username"])
        self.assertEqual(confirmed.json()["confirmed_date"], "2026-09-05")
        self.assertIn("已核实", confirmed.json()["remark"])

        for method, url, kwargs in (
            (self.client.post, f"{base}/{fee_id}/confirm", {"json": {}}),
            (self.client.put, f"{base}/{fee_id}", {"json": {"remark": "不能修改"}}),
            (self.client.delete, f"{base}/{fee_id}", {}),
        ):
            response = await method(url, **kwargs)
            self.assertEqual(response.status_code, 409, response.text)

        listing = await self.client.get(base, params={"page": 1, "page_size": 15})
        self.assertEqual(listing.status_code, 200, listing.text)
        self.assertEqual(listing.json()["total"], 1)
        self.assertEqual(listing.json()["items"][0]["id"], fee_id)

        async with self.sessions() as db:
            actions = list((await db.scalars(select(WorkflowEvent.action).where(
                WorkflowEvent.record_id == self.case_id,
            ))).all())
        self.assertTrue({"新建案件资助费用", "修改案件资助费用", "办理案件资助费用", "删除案件资助费用"}.issubset(actions))

    async def test_dedicated_manage_action_rejects_visible_user_without_grant(self):
        app.dependency_overrides[current_identity] = lambda: DENIED_IDENTITY
        capabilities = await self.client.get(
            f"{API}/cases/action-capabilities", params={"record_ids": self.denied_case_id},
        )
        self.assertEqual(capabilities.status_code, 200, capabilities.text)
        self.assertFalse(capabilities.json()["items"][str(self.denied_case_id)]["can_manage_assisted_fees"])
        created = await self.client.post(
            f"{API}/cases/{self.denied_case_id}/assisted-fees",
            json={"assisted_type": "未授权资助"},
        )
        self.assertEqual(created.status_code, 403, created.text)

        invisible = await self.client.get(f"{API}/cases/{self.case_id}/assisted-fees")
        self.assertEqual(invisible.status_code, 404, invisible.text)

    async def test_archived_case_rejects_write(self):
        response = await self.client.post(
            f"{API}/cases/{self.archived_case_id}/assisted-fees",
            json={"assisted_type": "归档后资助"},
        )
        self.assertEqual(response.status_code, 409, response.text)

    async def test_parent_case_delete_explicitly_removes_assisted_children(self):
        base = f"{API}/cases/{self.other_case_id}/assisted-fees"
        created = await self.client.post(base, json={"assisted_type": "父案件删除清理"})
        self.assertEqual(created.status_code, 201, created.text)
        deleted = await self.client.delete(f"{API}/cases/{self.other_case_id}")
        self.assertEqual(deleted.status_code, 204, deleted.text)
        async with self.sessions() as db:
            remaining = int(await db.scalar(select(func.count()).select_from(CaseAssistedFee).where(
                CaseAssistedFee.case_record_id == self.other_case_id,
            )) or 0)
        self.assertEqual(remaining, 0)


if __name__ == "__main__":
    unittest.main()
