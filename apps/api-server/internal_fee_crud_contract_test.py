import unittest

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database import Base, get_db
from app.main import app
from app.models import BusinessRecord, User, WorkflowEvent
from app.security import current_identity


API = settings.api_prefix
ADMIN = {"username": "codex-internal-fee-admin", "role": "admin", "display_name": "Codex Internal Fee Admin", "department": "Finance"}
USER = {"username": "codex-internal-fee-user", "role": "user", "display_name": "Codex Internal Fee User", "department": "Finance"}


class InternalFeeCrudContractTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with self.sessions() as db:
            db.add_all([
                User(username=ADMIN["username"], display_name=ADMIN["display_name"], department=ADMIN["department"], role="admin", password_hash="x", is_active=True),
                User(username=USER["username"], display_name=USER["display_name"], department=USER["department"], role="user", password_hash="x", is_active=True),
            ])
            await db.commit()
        self.identity = ADMIN

        async def override_db():
            async with self.sessions() as db:
                yield db

        self.previous_overrides = dict(app.dependency_overrides)
        app.dependency_overrides[get_db] = override_db
        app.dependency_overrides[current_identity] = lambda: self.identity
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://internal-fee.test")

    async def asyncTearDown(self):
        await self.client.aclose()
        app.dependency_overrides.clear()
        app.dependency_overrides.update(self.previous_overrides)
        await self.engine.dispose()

    @staticmethod
    def payload(**overrides):
        value = {
            "title": "CODEX internal fee", "customer": "CODEX customer", "amount": 125.5,
            "fee_type": "内部费用", "expense_scope": "内部", "expense_subtype": "翻译费",
            "handler": ADMIN["username"], "payee": "CODEX payee", "description": "CODEX create",
        }
        value.update(overrides)
        return value

    async def test_create_update_delete_persist_internal_fee_and_workflow_audit(self):
        created = await self.client.post(f"{API}/finance/internal-fees", json=self.payload())
        self.assertEqual(created.status_code, 201, created.text)
        fee_id = created.json()["id"]
        self.assertEqual(created.json()["data"]["fee_type"], "内部费用")
        self.assertEqual(created.json()["data"]["expense_scope"], "内部")

        updated = await self.client.put(f"{API}/finance/internal-fees/{fee_id}", json=self.payload(title="CODEX internal fee revised", amount=-15.25, description="CODEX update"))
        self.assertEqual(updated.status_code, 200, updated.text)
        self.assertEqual(updated.json()["title"], "CODEX internal fee revised")
        self.assertEqual(updated.json()["data"]["amount"], -15.25)
        self.assertTrue(updated.json()["data"]["is_refund"])

        async with self.sessions() as db:
            fee = await db.get(BusinessRecord, fee_id)
            self.assertIsNotNone(fee)
            events = list((await db.scalars(select(WorkflowEvent).where(WorkflowEvent.record_id == fee_id).order_by(WorkflowEvent.id))).all())
            self.assertEqual([event.action for event in events], ["创建费用", "修改费用草稿"])

        deleted = await self.client.delete(f"{API}/finance/internal-fees/{fee_id}")
        self.assertEqual(deleted.status_code, 204, deleted.text)
        async with self.sessions() as db:
            fee = await db.get(BusinessRecord, fee_id)
            self.assertEqual(fee.status, "已删除")
            events = list((await db.scalars(select(WorkflowEvent).where(WorkflowEvent.record_id == fee_id).order_by(WorkflowEvent.id))).all())
            self.assertEqual([event.action for event in events], ["创建费用", "修改费用草稿", "删除内部费用草稿"])
        listed = await self.client.get(f"{API}/finance/internal-fees")
        self.assertEqual(listed.status_code, 200, listed.text)
        self.assertNotIn(fee_id, [item["id"] for item in listed.json()["items"]])

    async def test_rejects_non_internal_payload_and_cannot_mutate_external_fee_through_internal_route(self):
        invalid = await self.client.post(f"{API}/finance/internal-fees", json=self.payload(fee_type="官方费用", expense_scope="律所"))
        self.assertEqual(invalid.status_code, 422, invalid.text)

        external = await self.client.post(f"{API}/finance/fees", json=self.payload(fee_type="官方费用", expense_scope="律所", expense_subtype="官费"))
        self.assertEqual(external.status_code, 201, external.text)
        hidden = await self.client.put(f"{API}/finance/internal-fees/{external.json()['id']}", json=self.payload())
        self.assertEqual(hidden.status_code, 404, hidden.text)

    async def test_requires_owner_or_manager_permission_for_mutation(self):
        created = await self.client.post(f"{API}/finance/internal-fees", json=self.payload())
        self.assertEqual(created.status_code, 201, created.text)
        self.identity = USER
        response = await self.client.put(
            f"{API}/finance/internal-fees/{created.json()['id']}",
            json=self.payload(handler=USER["username"]),
        )
        self.assertEqual(response.status_code, 403, response.text)
        deleted = await self.client.delete(f"{API}/finance/internal-fees/{created.json()['id']}")
        self.assertEqual(deleted.status_code, 403, deleted.text)
        async with self.sessions() as db:
            fee = await db.get(BusinessRecord, created.json()["id"])
            self.assertEqual(fee.status, "草稿")
            self.assertEqual(fee.title, "CODEX internal fee")

    async def test_submitted_internal_fee_cannot_be_updated_or_deleted(self):
        created = await self.client.post(f"{API}/finance/internal-fees", json=self.payload())
        self.assertEqual(created.status_code, 201, created.text)
        fee_id = created.json()["id"]
        async with self.sessions() as db:
            fee = await db.get(BusinessRecord, fee_id)
            fee.status = "待审批"
            await db.commit()

        updated = await self.client.put(f"{API}/finance/internal-fees/{fee_id}", json=self.payload(title="must not save"))
        self.assertEqual(updated.status_code, 409, updated.text)
        deleted = await self.client.delete(f"{API}/finance/internal-fees/{fee_id}")
        self.assertEqual(deleted.status_code, 409, deleted.text)
        async with self.sessions() as db:
            fee = await db.get(BusinessRecord, fee_id)
            self.assertEqual(fee.status, "待审批")
            self.assertEqual(fee.title, "CODEX internal fee")


if __name__ == "__main__":
    unittest.main()
