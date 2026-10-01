import os
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"

import unittest

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database import Base, get_db
from app.main import app
from app.models import BusinessRecord, RolePermission, SystemParameter, User, WorkflowEvent
from app.security import current_identity


class CustomerShareReplacementTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.identity = {"username": "share-owner", "role": "admin"}
        async with self.sessions() as db:
            for name in ("share-owner", "share-one", "share-two", "share-three", "share-left", "share-disabled"):
                db.add(User(username=name, display_name=name, role="admin" if name == "share-owner" else "user",
                            department="CODEX-share", password_hash="test-only", is_active=name != "share-disabled"))
                db.add(BusinessRecord(module="hr", serial_no=f"CODEX-HR-{name}", title=name,
                                      owner=name, status="离职" if name == "share-left" else "在职", data={"username": name}))
            db.add(RolePermission(role="user", display_name="CODEX", data_scope="本人及共享数据",
                                  menu_keys=["customer-shared"], field_keys=["*"]))
            db.add(SystemParameter(category="customer_type", code="customer", name="客户", is_active=True))
            customer = BusinessRecord(module="customer", serial_no="CODEX-SHARE-REPLACE", title="CODEX shared customer",
                                      owner="share-owner", status="正常", data={"customer_type": "客户",
                                      "customer_managers": ["share-owner"], "shared_with": ["share-one", "share-two"], "is_shared": "是"})
            db.add(customer)
            await db.commit()
            self.customer_id = customer.id

        async def override_db():
            async with self.sessions() as db:
                yield db

        self.overrides = dict(app.dependency_overrides)
        app.dependency_overrides[get_db] = override_db
        app.dependency_overrides[current_identity] = lambda: self.identity
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://customer-share.test")

    async def asyncTearDown(self):
        await self.client.aclose()
        app.dependency_overrides.clear()
        app.dependency_overrides.update(self.overrides)
        await self.engine.dispose()

    async def share(self, recipients):
        return await self.client.post(f"{settings.api_prefix}/customers/{self.customer_id}/share",
                                      json={"recipients": recipients, "comment": "CODEX save selection"})

    async def snapshot(self):
        async with self.sessions() as db:
            row = await db.get(BusinessRecord, self.customer_id)
            events = list(await db.scalars(select(WorkflowEvent).where(WorkflowEvent.record_id == row.id).order_by(WorkflowEvent.id)))
            return dict(row.data), [(event.action, event.comment) for event in events]

    async def shared_ids(self, username):
        before = self.identity
        self.identity = {"username": username, "role": "user"}
        try:
            response = await self.client.get(f"{settings.api_prefix}/customers", params={"scope": "shared", "customer_type": "客户"})
            self.assertEqual(response.status_code, 200, response.text)
            return [item["id"] for item in response.json()["items"]]
        finally:
            self.identity = before

    async def test_removing_one_recipient_updates_saved_list_and_recipient_page(self):
        self.assertIn(self.customer_id, await self.shared_ids("share-one"))
        response = await self.share(["share-two"])
        self.assertEqual(response.status_code, 200, response.text)
        data, events = await self.snapshot()
        self.assertEqual(data["shared_with"], ["share-two"])
        self.assertEqual(data["is_shared"], "是")
        self.assertNotIn(self.customer_id, await self.shared_ids("share-one"))
        self.assertIn(self.customer_id, await self.shared_ids("share-two"))
        self.assertIn("share-one", events[-1][1])
        self.assertIn("share-two", events[-1][1])
        self.assertIn("CODEX save selection", events[-1][1])

    async def test_explicit_empty_list_cancels_all_sharing(self):
        response = await self.share([])
        self.assertEqual(response.status_code, 200, response.text)
        data, events = await self.snapshot()
        self.assertEqual(data["shared_with"], [])
        self.assertEqual(data["is_shared"], "否")
        self.assertEqual(len(events), 1)
        self.assertEqual(await self.shared_ids("share-one"), [])
        self.assertEqual(await self.shared_ids("share-two"), [])

    async def test_replace_add_and_remove_together_is_idempotent(self):
        for _ in range(2):
            response = await self.share(["share-two", "share-three", "share-two"])
            self.assertEqual(response.status_code, 200, response.text)
            data, _ = await self.snapshot()
            self.assertEqual(data["shared_with"], ["share-two", "share-three"])
            self.assertEqual(data["customer_managers"], ["share-owner"])

    async def test_missing_and_blank_recipients_never_cancel_sharing(self):
        before = await self.snapshot()
        for body in ({}, {"recipients": None}, {"recipients": ["  ", ""]}):
            response = await self.client.post(f"{settings.api_prefix}/customers/{self.customer_id}/share", json=body)
            self.assertEqual(response.status_code, 422, response.text)
            self.assertEqual(await self.snapshot(), before)

    async def test_invalid_left_disabled_owner_and_mixed_recipients_do_not_change_data(self):
        before = await self.snapshot()
        for recipients in (["missing"], ["share-left"], ["share-disabled"], ["share-owner"], ["share-three", "missing"]):
            response = await self.share(recipients)
            self.assertEqual(response.status_code, 200, response.text)
            self.assertFalse(response.json()["IsSuccess"])
            self.assertEqual(await self.snapshot(), before)

    async def test_public_and_recycled_customers_remain_blocked(self):
        for status in ("公海", "已回收"):
            async with self.sessions() as db:
                row = await db.get(BusinessRecord, self.customer_id)
                row.status = status
                await db.commit()
            before = await self.snapshot()
            response = await self.share([])
            self.assertEqual(response.status_code, 200, response.text)
            self.assertFalse(response.json()["IsSuccess"])
            self.assertEqual(await self.snapshot(), before)

    async def test_invisible_customer_cannot_be_unshared(self):
        self.identity = {"username": "share-three", "role": "user"}
        before = await self.snapshot()
        response = await self.share([])
        self.assertEqual(response.status_code, 404, response.text)
        self.assertIn("detail", response.json())
        self.assertEqual(await self.snapshot(), before)


if __name__ == "__main__":
    unittest.main()
