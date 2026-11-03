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
        # 501222：没填开庭律师时和案件详情页一样取第一位经办律师，不再提示“未指定开庭律师”。
        self.assertIn({"role": "开庭律师", "username": "lawyer", "name": "范文玲"}, result["people"])
        self.assertNotIn("开庭律师", result["case_check"]["a_case_elements"]["missing"])
        self.assertEqual(result["relationships"]["clues"][0]["serial_no"], "XS-SPACE-001")
        self.assertEqual(result["relationships"]["investigations"][0]["serial_no"], "DC-SPACE-001")
        self.assertIn("converted_to_case", {item["type"] for item in result["relationships"]["edges"]})
        self.assertIn("supports_case", {item["type"] for item in result["relationships"]["edges"]})
        self.assertFalse(result["agent"]["enabled"])
        self.assertTrue(result["agent"]["write_requires_approval"])

    async def test_stage_overdue_from_legacy_history_and_switch(self):
        # 501222：旧系统迁来的案件按旧系统阶段记录算进入时间；“旧系统迁来的案件也提醒”关掉后不提醒。
        from datetime import datetime
        from sqlalchemy import update
        from app.models import LegacyCasePhaseHistory, SystemConfig, SystemParameter
        async with self.sessions() as db:
            case = await self._seed(db)
            case_id = case.id
            data = {key: value for key, value in (case.data or {}).items() if key not in {"phase_changed_at", "phase_visits"}}
            await db.execute(update(BusinessRecord.__table__).where(BusinessRecord.__table__.c.id == case_id).values(
                status="文书准备", data={**data, "case_phase_id": "101011"}))
            db.add_all([
                SystemParameter(category="case_phase", code="101011", name="文书准备", extra={"case_type": "民事争议", "expected_days": 60}),
                LegacyCasePhaseHistory(legacy_phase_id=9001, case_record_id=case_id, legacy_phase_code="101011", is_active="T",
                                       legacy_created_at=datetime(2026, 1, 1, 9, 0)),
            ])
            await db.commit()
            db.expire_all()
            result = await get_case_space_context(case_id, {"username": "lawyer", "role": "user"}, db)
            overdue = result["case_check"]["b_tasks"]["stage_overdue"]
            self.assertEqual(overdue["entered_at"], "2026-01-01")
            self.assertIn("案件在文书准备阶段已", overdue["message"])
            db.add(SystemConfig(key="case_stage_overdue", label="案件阶段超期提醒", group="业务配置", value={"remind_legacy_cases": False}))
            await db.commit()
            db.expire_all()
            result = await get_case_space_context(case_id, {"username": "lawyer", "role": "user"}, db)
            self.assertIsNone(result["case_check"]["b_tasks"]["stage_overdue"], "关掉开关后旧系统迁来的案件不提醒")

    async def test_stage_entered_falls_back_to_last_legacy_change(self):
        # 旧系统记录里没有当前阶段时，取最后一次阶段变化时间，仍算旧系统迁来的案件。
        from datetime import datetime
        from sqlalchemy import update
        from app.models import LegacyCasePhaseHistory, SystemParameter
        async with self.sessions() as db:
            case = await self._seed(db)
            case_id = case.id
            data = {key: value for key, value in (case.data or {}).items() if key not in {"phase_changed_at", "phase_visits"}}
            await db.execute(update(BusinessRecord.__table__).where(BusinessRecord.__table__.c.id == case_id).values(
                status="文书准备", data={**data, "case_phase_id": "101011"}))
            db.add_all([
                SystemParameter(category="case_phase", code="101011", name="文书准备", extra={"expected_days": 60}),
                LegacyCasePhaseHistory(legacy_phase_id=9101, case_record_id=case_id, legacy_phase_code="101010", is_active="T",
                                       legacy_created_at=datetime(2026, 3, 2, 23, 30)),
                LegacyCasePhaseHistory(legacy_phase_id=9102, case_record_id=case_id, legacy_phase_code="101001", is_active="T",
                                       legacy_created_at=datetime(2026, 2, 1, 9, 0)),
            ])
            await db.commit()
            db.expire_all()
            result = await get_case_space_context(case_id, {"username": "lawyer", "role": "user"}, db)
            self.assertEqual(result["case_check"]["b_tasks"]["stage_overdue"]["entered_at"], "2026-03-02")

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
