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

    async def test_ordinary_package_restores_previous_status_including_contract_payment(self):
        """501589（shenhe 11-05）：付款管理 › 待核销列表的普通付款包，案件费用、合同付款都退回提交付款单之前的状态。"""
        async with self.sessions() as db:
            package = BusinessRecord(module="finance_package", serial_no="P261105-501589", title="付款申请单", status="待核销",
                                     owner=IDENTITY["username"], data={})
            db.add(package)
            await db.flush()
            fee = BusinessRecord(module="finance", serial_no="FY-589", title="公证费", status="待核销", owner=IDENTITY["username"],
                                 data={"fee_type": "公证费", "amount": 100, "payment_package_id": package.id,
                                       "payment_package_no": package.serial_no, "payment_package_amount": 60,
                                       "writeoff_status": "待核销", "payment_status": "待核销"})
            contract = BusinessRecord(module="contract_payment", serial_no="CP-589", title="合同付款", status="待核销",
                                      owner=IDENTITY["username"], data={"amount": 50, "payment_package_id": package.id,
                                                                        "payment_package_no": package.serial_no,
                                                                        "writeoff_status": "待核销", "payment_status": "待核销"})
            db.add_all([fee, contract])
            await db.flush()
            package.data = {"fee_type": "普通付款包", "fee_ids": [fee.id, contract.id]}
            db.add_all([WorkflowEvent(record_id=fee.id, action="合并提交付款单", from_status="部分付款", to_status="待核销",
                                      operator=IDENTITY["username"], comment=package.serial_no),
                        WorkflowEvent(record_id=contract.id, action="合并提交付款单", from_status="待付款", to_status="待核销",
                                      operator=IDENTITY["username"], comment=package.serial_no)])
            await db.commit()
            ids = package.id, fee.id, contract.id
        app.dependency_overrides[current_identity] = lambda: {**IDENTITY, "role": "admin"}
        response = await self.client.post(f"{API}/finance/payment-packages/{ids[0]}/rollback", json={"comment": "收款账号错了"})
        self.assertEqual(response.status_code, 200, response.text)
        async with self.sessions() as db:
            self.assertEqual((await db.get(BusinessRecord, ids[0])).status, "已回滚")
            fee, contract = await db.get(BusinessRecord, ids[1]), await db.get(BusinessRecord, ids[2])
            self.assertEqual((fee.status, contract.status), ("部分付款", "待付款"))
            self.assertEqual(fee.data.get("payment_status"), "部分付款")
            for item in (fee, contract):
                self.assertNotIn("payment_package_id", item.data)
                self.assertNotIn("payment_package_amount", item.data)
                self.assertNotIn("writeoff_status", item.data)
            events = (await db.execute(select(WorkflowEvent.record_id, WorkflowEvent.to_status, WorkflowEvent.comment).where(
                WorkflowEvent.action == "待核销回滚", WorkflowEvent.record_id.in_(ids)))).all()
            self.assertEqual(sorted(events), sorted([(ids[0], "已回滚", "收款账号错了"), (ids[1], "部分付款", "收款账号错了"),
                                                     (ids[2], "待付款", "收款账号错了")]))


if __name__ == "__main__":
    unittest.main()
