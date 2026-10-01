"""Contract tests for the agent-ready case-space aggregation boundary."""

import unittest
from datetime import date

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.main import get_case_space_context
from app.models import (
    BusinessRecord,
    ContractObject,
    FileAttachment,
    HearingSchedule,
    IncomingPayment,
    ReceivablePlan,
    User,
)


class CaseSpaceContextContractTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

    async def asyncTearDown(self):
        await self.engine.dispose()

    async def _seed(self, db: AsyncSession) -> BusinessRecord:
        db.add_all([
            User(username="lawyer", display_name="范文玲", department="上海", password_hash="x", role="user"),
            User(username="outsider", display_name="外部员工", department="北京", password_hash="x", role="user"),
        ])
        customer = BusinessRecord(
            module="customer", serial_no="KH-SPACE-001", title="案件空间客户", customer="案件空间客户",
            status="在办", owner="lawyer", department="上海", data={},
        )
        contract = BusinessRecord(
            module="contract", serial_no="HT-SPACE-001", title="案件空间合同", customer="案件空间客户",
            status="审批通过", owner="lawyer", department="上海", data={"amount": 100000},
        )
        db.add_all([customer, contract])
        await db.flush()
        case = BusinessRecord(
            module="case", serial_no="SHMS2600999", title="案件空间测试案件", customer="案件空间客户",
            status="一审准备开庭", owner="lawyer", department="上海",
            data={
                "customer_id": customer.id, "contract_id": contract.id, "case_type": "民事案件",
                "handling_lawyers": ["范文玲"], "handling_lawyer_usernames": ["lawyer"],
                "business_owner": "lawyer", "case_creation_step": "completed",
                "case_creation_approval_status": "自动通过",
            },
        )
        db.add(case)
        await db.flush()
        investigation = BusinessRecord(
            module="investigation", serial_no="DC-SPACE-001", title="案件关联调查任务", customer=case.customer,
            status="调查中", owner="lawyer", department="上海",
            data={"case_record_id": case.id, "case_no": case.serial_no, "contract_record_id": contract.id},
        )
        db.add(investigation)
        await db.flush()
        clue = BusinessRecord(
            module="clue", serial_no="XS-SPACE-001", title="案件关联调查线索", customer=case.customer,
            status="已转案件", owner="lawyer", department="上海",
            data={"converted_case_id": case.id, "investigation_record_id": investigation.id, "investigation_no": investigation.serial_no},
        )
        db.add(clue)
        await db.flush()
        finance = BusinessRecord(
            module="finance", serial_no="FY-SPACE-001", title="案件诉讼费", customer=case.customer,
            status="待付款", owner="lawyer", department="上海",
            data={"case_id": case.id, "case_no": case.serial_no, "amount": 5000},
        )
        invoice = BusinessRecord(
            module="invoice", serial_no="FP-SPACE-001", title="案件发票", customer=case.customer,
            status="已开票", owner="lawyer", department="上海",
            data={"case_no": case.serial_no, "amount": 3000, "invoice_no": "INV-001"},
        )
        task = BusinessRecord(
            module="task", serial_no="RW-SPACE-001", title="提交证据", customer=case.customer,
            status="处理中", owner="lawyer", department="上海",
            data={"case_record_id": case.id, "case_no": case.serial_no, "deadline": "2026-08-20", "initiator": "lawyer"},
        )
        reminder = BusinessRecord(
            module="case_reminder", serial_no="TX-SPACE-001", title="上诉期限", customer=case.customer,
            status="有效", owner="lawyer", department="上海",
            data={"case_id": case.id, "case_no": case.serial_no, "reminder_date": "2026-08-18", "deadline": "2026-08-20"},
        )
        db.add_all([finance, invoice, task, reminder])
        db.add_all([
            ContractObject(contract_record_id=contract.id, case_record_id=case.id, fee_type="代理费", amount=100000, remark="一审", created_by="lawyer", updated_by="lawyer"),
            ReceivablePlan(contract_record_id=contract.id, phase="首付款", due_date=date(2026, 8, 15), amount=50000, received_amount=30000, status="部分收款", payer=case.customer),
            HearingSchedule(case_record_id=case.id, hearing_date=date(2026, 9, 1), hearing_time="09:30", court="上海法院", courtroom="第一法庭", hearing_type="一审开庭", hearing_lawyer="范文玲"),
            IncomingPayment(receipt_no="HK-SPACE-001", received_date=date(2026, 8, 10), amount=30000, payer_name=case.customer, bank_reference="BANK-SPACE-001", status="已认领", contract_record_id=contract.id, contract_no=contract.serial_no, case_no=case.serial_no, operator="lawyer"),
        ])
        await db.flush()
        db.add_all([
            FileAttachment(record_id=case.id, category="证据材料", original_name="证据.pdf", stored_name="space-case.pdf", path="/tmp/space-case.pdf", uploader="lawyer"),
            FileAttachment(record_id=contract.id, category="合同附件", original_name="合同.pdf", stored_name="space-contract.pdf", path="/tmp/space-contract.pdf", uploader="lawyer"),
        ])
        await db.commit()
        return case

    async def test_context_aggregates_authorized_case_resources(self):
        async with self.sessions() as db:
            case = await self._seed(db)
            result = await get_case_space_context(
                case.id, {"username": "lawyer", "role": "user"}, db,
            )

        self.assertEqual(result["schema_version"], "1.1")
        self.assertEqual(result["space"]["id"], f"case:{case.id}")
        self.assertEqual(result["space"]["kind"], "business_graph")
        self.assertEqual(result["case"]["serial_no"], "SHMS2600999")
        self.assertEqual(result["customer"]["title"], "案件空间客户")
        self.assertEqual(result["contracts"][0]["serial_no"], "HT-SPACE-001")
        self.assertEqual(result["contracts"][0]["objects"][0]["amount"], 100000)
        self.assertIsNone(result["contracts"][0]["receivables"][0]["amount"])
        self.assertIsNone(result["finances"]["fees"][0]["data"].get("amount"))
        self.assertEqual({item["original_name"] for item in result["documents"]}, {"证据.pdf", "合同.pdf"})
        self.assertEqual({item["type"] for item in result["deadlines"]}, {"案件提醒", "开庭排期", "案件任务"})
        self.assertIn({"role": "案件负责人", "username": "lawyer", "name": "范文玲"}, result["people"])
        self.assertEqual(result["relationships"]["clues"][0]["serial_no"], "XS-SPACE-001")
        self.assertEqual(result["relationships"]["investigations"][0]["serial_no"], "DC-SPACE-001")
        self.assertIn("converted_to_case", {item["type"] for item in result["relationships"]["edges"]})
        self.assertIn("supports_case", {item["type"] for item in result["relationships"]["edges"]})
        self.assertFalse(result["agent"]["enabled"])
        self.assertTrue(result["agent"]["write_requires_approval"])

    async def test_context_rejects_user_without_case_visibility(self):
        async with self.sessions() as db:
            case = await self._seed(db)
            with self.assertRaises(HTTPException) as raised:
                await get_case_space_context(
                    case.id, {"username": "outsider", "role": "user"}, db,
                )
        self.assertEqual(raised.exception.status_code, 404)


if __name__ == "__main__":
    unittest.main()
