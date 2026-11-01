"""BUG 500798：报表大屏代理费到账排行，按案源人、开庭律师分别统计，口径同客户ROI。"""
import unittest
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

import app.main  # noqa: F401  注册全部模型
from app.core.agency_fee_ranking import NO_HEARING_LAWYER, agency_fee_rankings, case_count_rankings
from app.core.person_names import refresh_person_names
from app.database import Base
from app.models import BusinessRecord, IncomingPayment, User


class AgencyFeeRankingTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

    async def asyncTearDown(self):
        await self.engine.dispose()

    async def test_agency_fee_by_source_person_and_hearing_lawyer(self):
        def receipt(no, received, amount, payer, customer, allocations):
            return IncomingPayment(source_kind="test", receipt_no=no, received_date=date.fromisoformat(received), amount=amount,
                                   payer_name=payer, status="已分配", claimed_customer=customer, allocated_amount=amount,
                                   operator="admin", allocations=allocations)
        async with self.sessions() as db:
            db.add_all([User(username="srca", display_name="案源甲", password_hash="x", role="staff"),
                        User(username="hla", display_name="开庭乙", password_hash="x", role="staff")])
            case_a = BusinessRecord(module="case", serial_no="AG-CASE-A", title="A", customer="客户甲", status="一审立案受理", owner="owner-a", department="诉讼部",
                                    data={"business_owner": "srca", "hearing_lawyer": "hla"})
            case_t = BusinessRecord(module="case", serial_no="AG-CASE-T", title="T", customer="测试11.13", status="一审立案受理", owner="owner-a", department="诉讼部",
                                    data={"business_owner": "srca", "hearing_lawyer": "hla"})
            contract = BusinessRecord(module="contract", serial_no="AG-CON-1", title="合同", customer="客户乙", status="已签订", owner="owner-c", department="诉讼部", data={})
            db.add_all([case_a, case_t, contract])
            await db.flush()
            db.add_all([
                receipt("R1", "2026-03-01", 1000, "客户甲", "客户甲", [{"amount": 1000, "case_id": case_a.id, "case_no": "AG-CASE-A", "fee_type": "代理费"}]),
                # 客户已直接付了代理费，公司之间转款里的代理费不再算。
                receipt("R2", "2026-03-02", 500, "上海恒达知识产权代理有限公司", "客户甲", [{"amount": 500, "case_no": "AG-CASE-A", "fee_type": "代理费", "fee_id": 1}]),
                receipt("R3", "2026-03-03", 300, "测试", "测试11.13", [{"amount": 300, "case_no": "AG-CASE-T", "fee_type": "代理费"}]),
                receipt("R4", "2026-03-04", 200, "客户甲", "客户甲（代收代付）", [{"amount": 200, "case_no": "AG-CASE-A", "fee_type": "代理费"}]),
                receipt("R5", "2026-03-05", 100, "客户甲", "客户甲", [{"amount": 100, "case_no": "AG-CASE-A", "fee_type": "官费", "is_refund": True}]),
                receipt("R6", "2025-12-31", 700, "客户甲", "客户甲", [{"amount": 700, "case_no": "AG-CASE-A", "fee_type": "代理费"}]),
                receipt("R7", "2026-04-01", 400, "客户乙", "客户乙", [{"amount": 400, "contract_no": "AG-CON-1", "fee_type": "代理费"}]),
            ])
            await db.commit()
            await refresh_person_names(db, force=True)
            result = await agency_fee_rankings(db, [], date(2026, 1, 1), date(2026, 12, 31))
        self.assertEqual(result["total"], 1400)
        self.assertEqual(result["by_source_person"], [{"name": "案源甲", "value": 1000}, {"name": "owner-c", "value": 400}])
        self.assertEqual(result["by_hearing_lawyer"], [{"name": "开庭乙", "value": 1000}, {"name": NO_HEARING_LAWYER, "value": 400}])
        # 18:14：案件数也按案源人、开庭律师分别统计，多人各算一次。
        counts = case_count_rankings([case_a, case_t, BusinessRecord(module="case", serial_no="X", owner="owner-x", data={"source_person": "srca", "hearing_lawyer": "hla,hlb"})])
        self.assertEqual(counts["by_source_person"], [{"name": "案源甲", "value": 3}])
        self.assertEqual(counts["by_hearing_lawyer"], [{"name": "开庭乙", "value": 3}, {"name": "hlb", "value": 1}])


if __name__ == "__main__":
    unittest.main()
