"""Row 29 contract/fee binding and duplicate invoice application regression tests."""

import unittest

from fastapi import HTTPException
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import InvoiceApplicationInput, app, create_invoice_application, list_invoice_case_fees
from app.models import BusinessRecord, FinanceTransaction, IncomingPayment, RolePermission, User, WorkflowEvent
from app.security import current_identity


IDENTITY = {
    "username": "row29-admin",
    "role": "admin",
    "department": "上海分所",
    "display_name": "第29行管理员",
}


class FinanceInvoiceRow29ContractTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        tables = [
            User.__table__, RolePermission.__table__, BusinessRecord.__table__,
            WorkflowEvent.__table__, FinanceTransaction.__table__, IncomingPayment.__table__,
        ]
        async with self.engine.begin() as conn:
            await conn.run_sync(lambda sync_conn: Base.metadata.create_all(sync_conn, tables=tables))
        async with self.sessions() as db:
            db.add(User(username=IDENTITY["username"], display_name=IDENTITY["display_name"], department=IDENTITY["department"], role="admin", password_hash="test", is_active=True))
            contract = BusinessRecord(module="contract", serial_no="CODEX-812-ROW29-CONTRACT", title="第29行合同", customer="CODEX-812-ROW29-CUSTOMER", status="已生效", owner=IDENTITY["username"], department=IDENTITY["department"], data={})
            case = BusinessRecord(module="case", serial_no="CODEX-812-ROW29-CASE", title="第29行案件", customer=contract.customer, status="办理中", owner=IDENTITY["username"], department=IDENTITY["department"], data={"contract_id": None, "contract_no": contract.serial_no})
            db.add_all([contract, case])
            await db.flush()
            case.data = {"contract_id": contract.id, "contract_no": contract.serial_no}
            fee = BusinessRecord(module="finance", serial_no="CODEX-812-ROW29-FEE", title="第29行代理费", customer=case.customer, status="已付款", owner=IDENTITY["username"], department=IDENTITY["department"], data={"amount": 100, "fee_type": "代理费", "case_id": case.id, "case_no": case.serial_no, "contract_id": contract.id, "contract_no": contract.serial_no})
            db.add(fee)
            await db.commit()
            self.contract_id, self.case_id, self.fee_id = contract.id, case.id, fee.id
        app.dependency_overrides[get_db] = self.override_db
        app.dependency_overrides[current_identity] = lambda: IDENTITY

    async def override_db(self):
        async with self.sessions() as db:
            yield db

    async def asyncTearDown(self):
        app.dependency_overrides.clear()
        await self.engine.dispose()

    def payload(self, **overrides):
        values = {
            "customer": "CODEX-812-ROW29-CUSTOMER",
            "case_no": "CODEX-812-ROW29-CASE",
            "amount": 100,
            "invoice_title": "CODEX-812-ROW29-CUSTOMER",
            "taxpayer_id": "CODEX-812-ROW29-TAX",
            "contract_record_id": self.contract_id,
            "case_record_id": self.case_id,
            "case_fee_ids": [self.fee_id],
        }
        values.update(overrides)
        return InvoiceApplicationInput(**values)

    async def test_candidate_is_bound_and_second_application_is_blocked(self):
        async with self.sessions() as db:
            before = await list_invoice_case_fees(scope="company", invoice_status="未开票", page=1, page_size=15, identity=IDENTITY, db=db)
            self.assertEqual([row["id"] for row in before["items"]], [self.fee_id])
            created = await create_invoice_application(self.payload(), IDENTITY, db)
            self.assertEqual(created["data"]["contract_id"], self.contract_id)
            self.assertEqual(created["data"]["case_fee_ids"], [self.fee_id])
            self.assertEqual(created["data"]["case_fee_allocations"], [{"fee_id": self.fee_id, "amount": 100.0}])
            after = await list_invoice_case_fees(scope="company", invoice_status="未开票", page=1, page_size=15, identity=IDENTITY, db=db)
            self.assertEqual(after["items"], [])
            with self.assertRaises(HTTPException) as duplicate:
                await create_invoice_application(self.payload(), IDENTITY, db)
            self.assertEqual(duplicate.exception.status_code, 409)
            with self.assertRaises(HTTPException) as missing_contract:
                await create_invoice_application(self.payload(contract_record_id=None), IDENTITY, db)
            self.assertEqual(missing_contract.exception.status_code, 422)
            with self.assertRaises(HTTPException) as missing_fee:
                await create_invoice_application(self.payload(case_fee_ids=[]), IDENTITY, db)
            self.assertEqual(missing_fee.exception.status_code, 422)
            invoice_ids = [created["id"]]
            await db.execute(delete(WorkflowEvent).where(WorkflowEvent.record_id.in_(invoice_ids)))
            await db.execute(delete(BusinessRecord).where(BusinessRecord.id.in_(invoice_ids)))
            await db.commit()


if __name__ == "__main__":
    unittest.main()
