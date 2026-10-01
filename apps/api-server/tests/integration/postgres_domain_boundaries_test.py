"""在专用 PostgreSQL 测试库验证结算关联与回款反冲事务。"""

import os
import unittest
from datetime import date
from uuid import uuid4

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.incoming_settlement import _active_settlements_by_receipt, _revert_incoming_allocation
from app.database import Base
from app.models import BusinessRecord, FinanceTransaction, IncomingPayment, ReceivablePlan
from tests.environment import validate_database_url


@unittest.skipUnless(os.environ.get("OA_TEST_POSTGRES_DSN"), "必须显式设置专用 PostgreSQL 测试库")
class PostgresDomainBoundariesTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        dsn = os.environ["OA_TEST_POSTGRES_DSN"]
        validate_database_url(dsn)
        if not dsn.startswith("postgresql+asyncpg://"):
            raise RuntimeError("本测试要求 PostgreSQL asyncpg 专用测试库")
        self.schema = f"oa_test_regression_{uuid4().hex}"
        self.admin_engine = create_async_engine(dsn)
        async with self.admin_engine.begin() as connection:
            database = await connection.scalar(text("select current_database()"))
            if not str(database).startswith("oa_test_"):
                raise RuntimeError("数据库不是 oa_test_* 专用测试库")
            await connection.execute(text(f"CREATE SCHEMA {self.schema}"))
        self.engine = create_async_engine(dsn, connect_args={"server_settings": {"search_path": self.schema}})
        try:
            async with self.engine.begin() as connection:
                await connection.run_sync(lambda sync: Base.metadata.create_all(sync, tables=[
                    BusinessRecord.__table__, ReceivablePlan.__table__, FinanceTransaction.__table__, IncomingPayment.__table__,
                ]))
        except Exception:
            await self._drop_schema()
            raise
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)

    async def asyncTearDown(self) -> None:
        await self._drop_schema()

    async def _drop_schema(self) -> None:
        await self.engine.dispose()
        async with self.admin_engine.begin() as connection:
            await connection.execute(text(f"DROP SCHEMA {self.schema} CASCADE"))
        await self.admin_engine.dispose()

    async def test_historical_settlement_status_and_allocation_rollback(self) -> None:
        async with self.sessions() as db:
            contract = BusinessRecord(module="contract", serial_no="oa-test-regression-contract", title="隔离合同", customer="隔离客户", status="已审批", owner="oa-test-regression", data={})
            fee = BusinessRecord(module="finance", serial_no="oa-test-regression-fee", title="隔离费用", customer="隔离客户", status="已收款", owner="oa-test-regression", data={"received_amount": 100, "cashed_amount": 100})
            db.add_all([contract, fee])
            await db.flush()
            receipt = IncomingPayment(receipt_no="oa-test-regression-receipt", received_date=date.today(), amount=100, payer_name="隔离客户", operator="oa-test-regression", allocations=[])
            plan = ReceivablePlan(contract_record_id=contract.id, phase="代理费", due_date=date.today(), amount=100, received_amount=100, status="已收款")
            transaction = FinanceTransaction(finance_record_id=fee.id, transaction_type="收款", amount=100, transaction_date=date.today(), operator="oa-test-regression")
            db.add_all([receipt, plan, transaction])
            await db.flush()
            fee.data = {**fee.data, "incoming_payment_id": receipt.id, "receipt_no": receipt.receipt_no}
            for index, status in enumerate(("已拒绝", "已驳回", "已退回", "已撤回", "已作废", "待审批"), 1):
                db.add(BusinessRecord(module="finance_settlement", serial_no=f"oa-test-regression-settlement-{index}", title="隔离结算", customer="隔离客户", status=status, owner="oa-test-regression", data={"receipt_id": str(receipt.id)}))
            await db.commit()
            contract_id, fee_id, receipt_id, plan_id, transaction_id = contract.id, fee.id, receipt.id, plan.id, transaction.id

        async with self.sessions() as db:
            active = await _active_settlements_by_receipt(db, {receipt_id})
            self.assertEqual(active[receipt_id].status, "待审批")
            self.assertEqual(await _active_settlements_by_receipt(db, {receipt_id}, exclude_application_ids={active[receipt_id].id}), {})
            await _revert_incoming_allocation({"amount": 100, "receivable_plan_id": plan_id, "fee_record_id": fee_id, "transaction_id": transaction_id}, db, payment_id=receipt_id)
            await db.flush()
            self.assertEqual((await db.get(ReceivablePlan, plan_id)).received_amount, 0)
            await db.rollback()

        async with self.sessions() as db:
            self.assertEqual((await db.get(ReceivablePlan, plan_id)).received_amount, 100)
            self.assertEqual((await db.get(BusinessRecord, fee_id)).data["received_amount"], 100)
            self.assertIsNotNone(await db.get(FinanceTransaction, transaction_id))
            self.assertIsNotNone(await db.get(BusinessRecord, contract_id))


if __name__ == "__main__":
    unittest.main()
