"""9.1 row 24: my contracts search the resolved customer master name."""

from __future__ import annotations

import unittest

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.main import list_records
from app.models import BusinessRecord, User


IDENTITY = {"username": "Fwl", "role": "user", "display_name": "范文林", "department": "合同部"}


class ContractCustomerNameSearchRow24Test(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool,
        )
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with self.sessions() as db:
            db.add(User(
                username="Fwl", display_name="范文林", department="合同部",
                role="user", password_hash="x", is_active=True,
            ))
            customer = BusinessRecord(
                module="customer", serial_no="KH260083", title="测试客户8.3", customer="测试客户8.3",
                status="正常", owner="Fwl", department="合同部",
            )
            db.add(customer)
            await db.flush()
            relation = {"customer_id": customer.id, "customer_record_id": customer.id, "customer_no": customer.serial_no}
            db.add_all([
                BusinessRecord(
                    module="contract", serial_no="SHHT2673411", title="测试客户8.3合同11",
                    # Simulate a migrated stale denormalized value; list presentation resolves the customer master.
                    customer="KH260083", status="审批通过", owner="Fwl", department="合同部", data=relation,
                ),
                BusinessRecord(
                    module="contract", serial_no="SHHT2673499", title="他人同客户合同",
                    customer="KH260083", status="审批通过", owner="other", department="其他部", data=relation,
                ),
            ])
            await db.commit()

    async def asyncTearDown(self) -> None:
        await self.engine.dispose()

    async def search(self, customer: str) -> list[str]:
        async with self.sessions() as db:
            result = await list_records(
                module="contract", keyword="", record_status="", scope="mine", statuses="",
                customer_id=None, customer=customer, customer_no="", exclude_archived=False,
                title="", serial_no="", record_type="", case_no="", fee_type="",
                contract_body="", source_person="", signed_at_start="", signed_at_end="",
                investigation_view="", archive_view="", pending_approver_only=False,
                page=1, page_size=100, identity=IDENTITY, db=db,
            )
        return [item["serial_no"] for item in result["items"]]

    async def test_full_resolved_customer_name_finds_my_contract(self) -> None:
        self.assertEqual(await self.search("测试客户8.3"), ["SHHT2673411"])

    async def test_partial_customer_name_keeps_mine_scope(self) -> None:
        self.assertEqual(await self.search("客户8.3"), ["SHHT2673411"])


if __name__ == "__main__":
    unittest.main()
