"""BUG20261029002：内部提成待结算/待归档/待审核按到账、结算、归档分开。

旧系统导入的待审批请款明细（LIP-）只有回款全部结算（SettlementStatus=25）且案件已归档才进待审核；
没有回款或未结算、案件未归档的都不显示。
"""

import unittest

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models import BusinessRecord, LegacyFinanceAllocation, LegacyFinanceRecord

IDENTITY = {"username": "r1029-admin", "role": "admin", "display_name": "R1029", "department": "Admin"}


class InternalCommissionStage1029Test(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with self.sessions() as db:
            self.cases = {}
            for name, status in (("archived", "已归档"), ("open", "一审待客户回款"), ("deficit", "亏损审核")):
                case = BusinessRecord(module="case", serial_no=f"R1029-{name}", title=name, status=status,
                                      owner=IDENTITY["username"], data={})
                db.add(case)
                await db.flush()
                self.cases[name] = case.id
            self.lines = {}
            # (明细, 案件, 旧回款结算状态列表)
            for index, (name, case, statuses) in enumerate((
                ("settled_archived", "archived", ["25", "25"]),
                ("unsettled_archived", "archived", ["25", "10"]),
                ("no_receipt_archived", "archived", []),
                ("settled_open", "open", ["25"]),
                ("settled_deficit", "deficit", ["25"]),
            )):
                case_fee_id = f"R1029-CF-{index}"
                db.add(LegacyFinanceRecord(source_table="FAM_InternalFee", legacy_id=f"R1029-IF-{index}",
                                           record_kind="internal_fee", source_payload={"CaseFeeId": case_fee_id}))
                for receipt_index, status in enumerate(statuses):
                    receipt = LegacyFinanceRecord(source_table="FAM_AR_Payment", legacy_id=f"R1029-RC-{index}-{receipt_index}",
                                                  record_kind="receipt", source_payload={"SettlementStatus": status})
                    db.add(receipt)
                    await db.flush()
                    db.add(LegacyFinanceAllocation(legacy_finance_record_id=receipt.id, source_table="FAM_AR_Payment_Object",
                                                   legacy_key=f"R1029-OBJ-{index}-{receipt_index}", allocation_kind="receipt",
                                                   legacy_case_fee_id=case_fee_id))
                parent = BusinessRecord(module="finance_application", serial_no=f"LIP-R1029-{index}", title=name, status="待审批",
                                        owner=IDENTITY["username"], data={"legacy_kind": "internal_payment", "case_id": self.cases[case]})
                db.add(parent)
                await db.flush()
                line = BusinessRecord(module="finance", serial_no=f"R1029-LINE-{index}", title=name, status="待审批",
                                      owner=IDENTITY["username"], data={
                                          "legacy_kind": "internal_payment_line", "fee_type": "内部费用", "expense_scope": "内部",
                                          "commission_type": "开庭提成", "fee_type_name": "开庭提成", "amount": 100,
                                          "legacy_internal_fee_id": f"R1029-IF-{index}", "internal_application_id": parent.id,
                                          "payment_application_no": f"P-R1029-{index}", "case_id": self.cases[case],
                                          "case_no": f"R1029-{case}", "applicant": IDENTITY["username"], "handler": IDENTITY["username"],
                                      })
                db.add(line)
                await db.flush()
                self.lines[name] = line.id
            await db.commit()

    async def asyncTearDown(self):
        await self.engine.dispose()

    async def test_legacy_line_settled_only_when_all_receipts_settled(self):
        from app.core.internal_commission_stage import legacy_line_settled_ids

        async with self.sessions() as db:
            lines = [(item.id, item.data) for item in [await db.get(BusinessRecord, line_id) for line_id in self.lines.values()]]
            settled = await legacy_line_settled_ids(db, lines)
        self.assertEqual(settled, {self.lines[name] for name in ("settled_archived", "settled_open", "settled_deficit")})

    async def test_review_queue_only_settled_and_archived_legacy_lines(self):
        from app.core.internal_requests import internal_review_rows

        async with self.sessions() as db:
            rows = await internal_review_rows(IDENTITY, db, "commission")
        ids = {row["id"] for row in rows} | {item["id"] for row in rows for item in (row.get("data") or {}).get("application_items") or []}
        # 一审待客户回款、亏损审核（未归档）以及未结算、无回款的旧请款都不进待审核。
        self.assertEqual(ids, {self.lines["settled_archived"]})


if __name__ == "__main__":
    unittest.main()
