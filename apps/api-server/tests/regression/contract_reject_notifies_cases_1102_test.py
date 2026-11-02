"""陶国南 11-02：合同没审批完也可以立案；合同被驳回时通知已立案件的经办律师和负责人，案件不自动删除。"""

import unittest

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.contracts import _contract_allows_downstream_creation, notify_cases_of_rejected_contract
from app.database import Base
from app.models import BusinessRecord, Notification


class ContractRejectNotifiesCasesTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)

    async def asyncTearDown(self):
        await self.engine.dispose()

    def test_contract_in_approval_can_start_a_case(self):
        self.assertTrue(_contract_allows_downstream_creation(BusinessRecord(module="contract", status="审批中")))
        self.assertFalse(_contract_allows_downstream_creation(BusinessRecord(module="contract", status="草稿")))

    async def test_rejection_notifies_case_team_and_keeps_case(self):
        async with self.sessions() as db:
            contract = BusinessRecord(module="contract", serial_no="HT1", title="合同", status="已拒绝", data={})
            db.add(contract); await db.flush()
            case = BusinessRecord(module="case", serial_no="AJ1", title="案件", status="待分配", owner="lawyer1",
                                  data={"contract_id": contract.id, "handling_lawyer_usernames": ["lawyer1", "lawyer2"]})
            other = BusinessRecord(module="case", serial_no="AJ2", title="别的案件", status="待分配", owner="x", data={"contract_id": 999})
            db.add_all([case, other]); await db.flush()
            sent = await notify_cases_of_rejected_contract(contract, "金额不对", "approver", db)
            await db.commit()
            rows = (await db.scalars(select(Notification))).all()
            self.assertEqual(sent, 2)
            self.assertEqual(sorted(row.recipient for row in rows), ["lawyer1", "lawyer2"])
            self.assertIn("金额不对", rows[0].content)
            self.assertIn("案件没有自动删除", rows[0].content)
            self.assertEqual((await db.get(BusinessRecord, case.id)).status, "待分配")


if __name__ == "__main__":
    unittest.main()
