import unittest
from datetime import date
from unittest.mock import patch

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

    async def test_compact_receipts_preserve_binding_pool_and_zero_nested_receipts(self):
        from app.core.finance_summary_query import receivable_payment_projection
        from app.core.formatters import _case_fee_display_type

        async with self.sessions() as db:
            case = BusinessRecord(module="case", serial_no="CODEX-COMPACT-CASE", title="案件",
                                  status="一审", owner="admin", department="测试部", data={})
            db.add(case)
            await db.flush()
            definitions = [("官费", "草稿", 912345), ("代理费", "草稿", 912345),
                           ("官费", "草稿", 0), ("官费", "已删除", 0), ("官费", "草稿", 0)]
            fees = [BusinessRecord(module="finance", serial_no=f"CODEX-COMPACT-FEE-{index}",
                        title=fee_type, status=status, owner="admin", department="测试部",
                        data={"fee_type": fee_type, "case_id": case.id, "case_no": case.serial_no,
                              "legacy_case_fee_id": legacy_id, "amount": 100})
                    for index, (fee_type, status, legacy_id) in enumerate(definitions)]
            db.add_all(fees)
            await db.flush()
            db.add(IncomingPayment(receipt_no="CODEX-COMPACT-RECEIPT", received_date=date(2026, 10, 12),
                amount=500, payer_name="测试客户", status="已认领", operator="admin", allocations=[
                    {"fee_id": fees[0].id, "amount": 99,
                     "settlement_items": [{"fee_id": fees[2].id, "amount": 0}]},
                    {"legacy_case_fee_id": 912345, "amount": 50},
                    {"case_no": case.serial_no, "amount": 88},
                    {"fee_id": fees[0].id, "amount": 0.015},
                    {"fee_id": fees[0].id, "amount": 0.005},
                    {"fee_id": fees[1].id, "amount": 1.234},
                    {"fee_id": fees[3].id, "amount": 99},
                ]))
            await db.commit()
            original = await receivable_payment_projection(fees, IDENTITY, db, record_scope=[], receipts_only=True)
            with patch("app.core.formatters._case_fee_display_type", wraps=_case_fee_display_type) as display:
                compact = await receivable_payment_projection(
                    fees, IDENTITY, db, record_scope=[], receipts_only=True, compact_receipts=True,
                )
                display.assert_not_called()
            self.assertEqual(compact, {
                fees[0].id: {"cashed_amount": 0.02},
                fees[1].id: {"cashed_amount": 1.23},
                fees[2].id: {"cashed_amount": 0.0},
            })
            self.assertNotIn(fees[3].id, original)
            self.assertEqual(original[fees[4].id]["cashed_amount"], 0)
            for fee_id, values in compact.items():
                self.assertEqual(values["cashed_amount"], original[fee_id]["cashed_amount"])
            self.assertTrue(all(set(values) == {"fee_type", "cashed_amount"} for values in original.values()))
            with self.assertRaises(ValueError):
                await receivable_payment_projection(fees, IDENTITY, db, compact_receipts=True)

    async def test_compact_summary_preserves_deleted_type_and_object_claims(self):
        from app.core.finance import _receivable_fee_category
        from app.core.projections import _receivable_detail_projection

        async with self.sessions() as db:
            contract = BusinessRecord(module="contract", serial_no="CODEX-COMPACT-CONTRACT", title="合同",
                                      status="审批通过", owner="admin", department="测试部", data={})
            db.add(contract)
            await db.flush()
            cases = [BusinessRecord(module="case", serial_no=f"CODEX-COMPACT-TYPE-CASE-{index}", title="案件",
                        status="一审", owner="admin", department="测试部", data={"contract_id": contract.id})
                     for index in range(2)]
            db.add_all(cases)
            await db.flush()
            agency = ContractObject(contract_record_id=contract.id, case_record_id=cases[0].id,
                                    fee_type="代理费", amount=100, created_by="admin", updated_by="admin")
            db.add(agency)
            await db.flush()
            definitions = [
                ("草稿", {"fee_type": "官费", "contract_object_id": agency.id}),
                ("草稿", {"fee_type": "代理费", "fee_type_name": "官费", "amount": 100.125,
                          "received_amount": 10.125}),
                ("已删除", {"fee_type": "官费", "fee_type_name": "代理费", "amount": 30, "received_amount": 5}),
                ("草稿", {"fee_type": "官费", "fee_type_name": "代理费"}),
                ("已删除", {"fee_type": "代理费", "fee_type_name": "官费"}),
                ("草稿", {"fee_type": "", "amount": 40}),
            ]
            fees = []
            for index, (status, data) in enumerate(definitions):
                case = cases[0] if index == 0 else cases[1]
                fees.append(BusinessRecord(module="finance", serial_no=f"CODEX-COMPACT-TYPE-FEE-{index}",
                    title="官费", status=status, owner="admin", department="测试部",
                    data={"contract_id": contract.id, "case_id": case.id, "case_no": case.serial_no,
                          "amount": 100, **data}))
            db.add_all(fees)
            await db.commit()
            records = [contract, *cases, *fees]
            identity = {**IDENTITY, "_dashboard_case_ids": {case.id for case in cases}}
            original = await _receivable_detail_projection(
                identity, db, records, summary_only=True, official_only=True,
            )
            with patch("app.core.finance._receivable_fee_category", wraps=_receivable_fee_category) as classify:
                compact = await _receivable_detail_projection(
                    identity, db, records, summary_only=True, official_only=True, dashboard_finance_only=True,
                )
                self.assertEqual(classify.call_count, 2)
            self.assertEqual(compact, original)
            self.assertEqual({row["id"]: row["remaining_amount"] for row in compact}, {
                f"fee:{fees[1].id}": 90.0, f"fee:{fees[2].id}": 25.0, f"fee:{fees[5].id}": 40.0,
            })

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
            dashboard_result = await dashboard(owner_identity, db, section="metrics")
            detail_result = await list_receivable_details("official-fee-unreceived", owner_identity, db)

        metric = next(
            item for item in dashboard_result["metrics"]
            if item["key"] == "official-fee-unreceived"
        )
        self.assertEqual(metric["value"], "80.00元")
        self.assertEqual(metric["route"], "dashboard-queue-official-fee-unreceived")

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
