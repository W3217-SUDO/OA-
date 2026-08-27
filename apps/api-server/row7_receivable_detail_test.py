import unittest
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.main import dashboard, list_receivable_details
from app.models import (
    BusinessRecord, ContractObject, FinanceTransaction, IncomingPayment,
    ReceivablePlan, User,
)


IDENTITY = {"username": "admin", "role": "admin"}


class Row7ReceivableDetailTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.sessions = async_sessionmaker(
            self.engine, expire_on_commit=False, class_=AsyncSession,
        )
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

    async def asyncTearDown(self):
        await self.engine.dispose()

    async def test_dashboard_and_detail_share_receivable_projection(self):
        async with self.sessions() as db:
            db.add(User(
                username="case-owner", display_name="案件负责人", department="上海分所",
                password_hash="test-only", role="user", role_ids=["user"],
            ))
            contract = BusinessRecord(
                module="contract", serial_no="CODEX-8.27-7-CONTRACT",
                title="第7行应收合同", customer="第7行客户", status="审批通过",
                owner="case-owner", department="上海分所",
                data={"contract_body": "律所", "source_person": "case-owner"},
            )
            db.add(contract)
            await db.flush()
            case = BusinessRecord(
                module="case", serial_no="CODEX-8.27-7-CASE",
                title="第7行应收案件", customer="第7行客户", status="一审",
                owner="case-owner", department="上海分所",
                data={
                    "contract_id": contract.id, "contract_no": contract.serial_no,
                    "case_stage": "一审", "case_type": "民事案件",
                },
            )
            db.add(case)
            await db.flush()
            contract_object = ContractObject(
                contract_record_id=contract.id, case_record_id=case.id,
                fee_type="一审诉讼费", amount=100, remark="第7行官费标的",
                created_by="admin", updated_by="admin",
            )
            db.add(contract_object)
            await db.flush()
            fee = BusinessRecord(
                module="finance", serial_no="CODEX-8.27-7-FEE",
                title="一审诉讼费", customer="第7行客户", status="已付款",
                owner="cashier", department="财务部",
                data={
                    "fee_type": "官方费用", "expense_subtype": "一审诉讼费",
                    "amount": 100, "case_id": case.id, "case_no": case.serial_no,
                    "contract_id": contract.id,
                    "contract_object_id": contract_object.id,
                },
            )
            db.add(fee)
            await db.flush()

            other_contract = BusinessRecord(
                module="contract", serial_no="CODEX-8.27-7-OTHER-CONTRACT",
                title="其他人员应收合同", customer="第7行其他客户", status="审批通过",
                owner="other-user", department="上海分所", data={"contract_body": "律所"},
            )
            db.add(other_contract)
            await db.flush()
            other_case = BusinessRecord(
                module="case", serial_no="CODEX-8.27-7-OTHER-CASE",
                title="其他人员应收案件", customer="第7行其他客户", status="一审",
                owner="other-user", department="上海分所",
                data={"contract_id": other_contract.id, "case_stage": "一审", "case_type": "民事案件"},
            )
            db.add(other_case)
            await db.flush()
            other_contract_object = ContractObject(
                contract_record_id=other_contract.id, case_record_id=other_case.id,
                fee_type="公证费", amount=50, remark="其他人员官费标的",
                created_by="other-user", updated_by="other-user",
            )
            db.add(other_contract_object)
            await db.flush()
            other_fee = BusinessRecord(
                module="finance", serial_no="CODEX-8.27-7-OTHER-FEE",
                title="公证费", customer="第7行其他客户", status="已付款",
                owner="cashier", department="财务部",
                data={
                    "fee_type": "官方费用", "expense_subtype": "公证费",
                    "amount": 50, "case_id": other_case.id,
                    "case_no": other_case.serial_no,
                    "contract_id": other_contract.id,
                    "contract_object_id": other_contract_object.id,
                },
            )
            db.add(other_fee)
            await db.flush()
            db.add_all([
                FinanceTransaction(
                    finance_record_id=fee.id, transaction_type="付款", amount=70,
                    transaction_date=date(2026, 8, 27), voucher_no="CODEX-8.27-7-PAY",
                    counterparty="法院", operator="admin",
                ),
                IncomingPayment(
                    receipt_no="CODEX-8.27-7-RECEIPT", received_date=date(2026, 8, 27),
                    amount=20, payer_name="第7行客户", bank_reference="CODEX-8.27-7-BANK",
                    status="已认领", claimed_customer="第7行客户",
                    contract_record_id=contract.id, contract_no=contract.serial_no,
                    case_no=case.serial_no, allocated_amount=20,
                    allocations=[{"fee_id": fee.id, "amount": 20}], operator="admin",
                ),
                ReceivablePlan(
                    contract_record_id=contract.id, phase="官费首付款",
                    due_date=date(2026, 9, 1), amount=999, received_amount=0,
                    status="待收款", payer="第7行客户",
                ),
                FinanceTransaction(
                    finance_record_id=other_fee.id, transaction_type="付款", amount=50,
                    transaction_date=date(2026, 8, 27), voucher_no="CODEX-8.27-7-OTHER-PAY",
                    counterparty="公证处", operator="cashier",
                ),
            ])
            await db.commit()

            owner_identity = {"username": "case-owner", "role": "user", "role_ids": ["user"]}
            dashboard_result = await dashboard(owner_identity, db)
            detail_result = await list_receivable_details(owner_identity, db)

        metric = next(
            item for item in dashboard_result["metrics"]
            if item["key"] == "official-fee-unreceived"
        )
        self.assertEqual(metric["value"], "80.00元")
        self.assertEqual(metric["route"], "contract-receivable-detail")
        self.assertEqual(metric["detail_context"], {
            "contract_no": "", "return_view": "contract-receivable-mine",
            "amount_filter": "official-unreceived", "owner": "case-owner",
        })

        self.assertEqual(detail_result["official_unreceived"], 80.0)
        row = next(item for item in detail_result["items"] if item["owner"] == "case-owner")
        self.assertEqual(row["contract_no"], "CODEX-8.27-7-CONTRACT")
        self.assertEqual(row["case_no"], "CODEX-8.27-7-CASE")
        self.assertEqual(row["case_stage"], "一审")
        self.assertEqual(row["case_type"], "民事案件")
        self.assertEqual(row["source_type"], "contract_object")
        self.assertEqual(row["fee_type"], "一审诉讼费")
        self.assertEqual(row["paid_amount"], 70.0)
        self.assertEqual(row["received_amount"], 20.0)
        self.assertEqual(row["remaining_amount"], 80.0)
        self.assertEqual(row["owner"], "case-owner")
        self.assertFalse(any(
            item["contract_no"] == "CODEX-8.27-7-OTHER-CONTRACT"
            for item in detail_result["items"]
        ))
        self.assertFalse(any(item["source_type"] == "receivable_plan" for item in detail_result["items"]))


if __name__ == "__main__":
    unittest.main()
