"""BUG20261101001（tgn 11-01 确认 1B、2、3 年化、4A）：品牌资金运营情况统计四项口径。"""
import unittest
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.roi import brand_charts
from app.database import Base
from app.models import BusinessRecord, IncomingPayment


class BrandReportTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.sessions() as db:
            cases = [
                # 正常归档：垫付 1-01，归档 1-31 → 30 天；代理费到账 1000，官费付 300。
                (1, "已归档", "2026-01-31"),
                # 亏损归档：垫付按通知日期 2-01（没有请款单），归档 3-02 → 29 天；诉讼费付 500 到账 100 → 亏 400。
                (2, "亏损归档", "2026-03-02"),
                # 在办：不算回款时间；公证费付 200 未到账，但不在亏损阶段 → 不算亏损。
                (3, "一审立案", ""),
            ]
            for case_id, status, archived in cases:
                db.add(BusinessRecord(id=case_id, module="case", serial_no=f"AJ{case_id}", title=f"案件{case_id}", status=status,
                                      owner="codex", customer="品牌甲", data={"archived_at": archived}))
            fees = [
                (11, 1, "官方费用", "11010020", 300, "2026-01-05"),
                (12, 1, "代理费", "11020010", 1000, ""),
                (21, 2, "官方费用", "11010020", 500, "2026-02-01"),
                (31, 3, "官方费用", "11010050", 200, "2026-04-01"),
            ]
            for fee_id, case_id, fee_type, code, amount, inform in fees:
                db.add(BusinessRecord(id=fee_id, module="finance", serial_no=f"FY{fee_id}", title=fee_type, status="已通知",
                                      owner="codex", data={"case_id": case_id, "fee_type": fee_type, "case_fee_type_id": code,
                                                           "amount": amount, "inform_date": inform}))
            db.add(BusinessRecord(id=41, module="contract_payment", serial_no="QK1", title="请款", status="已付款", owner="codex",
                                  data={"payment_date": "2026-01-01", "lines": [{"fee_record_id": 11, "amount": 300}]}))
            db.add(BusinessRecord(id=42, module="contract_payment", serial_no="QK2", title="请款", status="已付款", owner="codex",
                                  data={"payment_date": "", "lines": [{"fee_record_id": 21, "amount": 500},
                                                                       {"fee_record_id": 31, "amount": 200}]}))
            db.add(IncomingPayment(receipt_no="R1", received_date=date(2026, 2, 1), amount=1100, payer_name="品牌甲", operator="codex",
                                   status="已分配", allocations=[{"fee_record_id": 12, "amount": 1000},
                                                                 {"fee_record_id": 21, "amount": 100}]))
            await db.commit()

    async def asyncTearDown(self):
        await self.engine.dispose()

    async def test_four_brand_metrics(self):
        async with self.sessions() as db:
            cases = [await db.get(BusinessRecord, case_id) for case_id in (1, 2, 3)]
            fees = [await db.get(BusinessRecord, fee_id) for fee_id in (11, 12, 21, 31)]
            charts, warnings = await brand_charts(cases, fees, db)
        values = {chart["title"]: chart["items"][0]["value"] for chart in charts}
        # 1B：(30 + 29) / 2
        self.assertEqual(values["资金回款周期统计"], 29.5)
        # 2：只算亏损阶段案件里诉讼/保全/公证费的未到账部分。
        self.assertEqual(values["资金亏损金额统计"], 400.0)
        # 3：1000 × 15% ÷ 300 ÷ 29.5 × 365（年化）
        self.assertAlmostEqual(values["资金回报率统计"], round(1000 * 0.15 / 300 / 29.5 * 365 * 100, 2))
        # 4A：400 ÷ 全部已付官费 1000
        self.assertEqual(values["资金亏损率统计"], 40.0)
        self.assertEqual(warnings, [])


if __name__ == "__main__":
    unittest.main()
