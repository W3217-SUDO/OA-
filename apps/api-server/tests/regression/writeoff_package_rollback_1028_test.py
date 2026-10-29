"""BUG20261028007：待核销列表右键回滚，整个付款包退回待付款；付款包保留为“已回滚”。"""

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
IDENTITY = {"username": "r1028-007", "role": "auditor", "display_name": "R007", "department": "财务"}


class WriteoffPackageRollbackTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with self.sessions() as db:
            db.add(User(username=IDENTITY["username"], display_name="R007", department="财务", role="auditor",
                        password_hash="x", is_active=True))
            self.package = BusinessRecord(module="finance_package", serial_no="FK-R007", title="付款包", status="待核销",
                                          owner=IDENTITY["username"], data={})
            db.add(self.package)
            await db.flush()
            self.fees = []
            for index in range(2):
                fee = BusinessRecord(module="finance", serial_no=f"FY-R007-{index}", title="公证费", status="待核销",
                                     owner=IDENTITY["username"], data={
                                         "fee_type": "公证费", "amount": 100, "payment_package_id": self.package.id,
                                         "payment_package_no": "FK-R007", "writeoff_status": "待核销", "payment_status": "待核销",
                                         "payment_requested_amount": 100, "application_date": "2026-10-28",
                                     })
                db.add(fee)
                self.fees.append(fee)
            await db.flush()
            self.package.data = {"fee_ids": [fee.id for fee in self.fees]}
            await db.commit()

        async def override_db():
            async with self.sessions() as db:
                yield db
        self.previous = dict(app.dependency_overrides)
        app.dependency_overrides[get_db] = override_db
        app.dependency_overrides[current_identity] = lambda: IDENTITY
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://r007.test")

    async def asyncTearDown(self):
        await self.client.aclose()
        app.dependency_overrides.clear()
        app.dependency_overrides.update(self.previous)
        await self.engine.dispose()

    async def test_rollback_returns_fees_to_waiting_and_keeps_package(self):
        response = await self.client.post(f"{API}/finance/payment-packages/{self.package.id}/rollback", json={"comment": "打包错了"})
        self.assertEqual(response.status_code, 200, response.text)
        async with self.sessions() as db:
            package = await db.get(BusinessRecord, self.package.id)
            self.assertEqual(package.status, "已回滚")
            self.assertEqual(package.data["rollback_comment"], "打包错了")
            for fee in self.fees:
                current = await db.get(BusinessRecord, fee.id)
                self.assertEqual(current.status, "已审批")
                self.assertNotIn("payment_package_id", current.data)
                self.assertNotIn("writeoff_status", current.data)
                self.assertEqual(current.data["application_date"], "2026-10-28")
            actions = (await db.scalars(select(WorkflowEvent.action).where(WorkflowEvent.action == "待核销回滚"))).all()
            self.assertEqual(len(actions), 3)
        again = await self.client.post(f"{API}/finance/payment-packages/{self.package.id}/rollback", json={})
        self.assertEqual(again.status_code, 409, again.text)

    async def test_written_off_package_cannot_roll_back(self):
        async with self.sessions() as db:
            package = await db.get(BusinessRecord, self.package.id)
            package.status = "已付款"
            await db.commit()
        response = await self.client.post(f"{API}/finance/payment-packages/{self.package.id}/rollback", json={})
        self.assertEqual(response.status_code, 409, response.text)

    async def test_ordinary_user_forbidden(self):
        app.dependency_overrides[current_identity] = lambda: {**IDENTITY, "role": "user"}
        response = await self.client.post(f"{API}/finance/payment-packages/{self.package.id}/rollback", json={})
        self.assertEqual(response.status_code, 403, response.text)


if __name__ == "__main__":
    unittest.main()
