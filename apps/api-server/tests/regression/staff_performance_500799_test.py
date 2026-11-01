"""BUG 500799：员工业绩统计中心——当年代理费到账、在办、开庭、结案归档，按角色按人统计。"""
import unittest
from datetime import date, datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

import app.main  # noqa: F401  注册全部模型
from app.core.person_names import refresh_person_names
from app.core.staff_performance import staff_performance
from app.database import Base
from app.models import BusinessRecord, IncomingPayment, User


class StaffPerformanceTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

    async def asyncTearDown(self):
        await self.engine.dispose()

    async def test_four_figures_by_role(self):
        def case(no, status, customer="客户甲", **data):
            base = {"business_owner": "srca", "investigator": "inv", "hearing_lawyer": "hla", "assistant": "asa"}
            return BusinessRecord(module="case", serial_no=no, title=no, customer=customer, status=status, owner="owner", department="诉讼部",
                                  created_at=datetime(2025 if no == "C-OLD" else 2026, 3, 1, tzinfo=timezone.utc), data={**base, **data})
        async with self.sessions() as db:
            db.add_all([User(username="srca", display_name="案源甲", password_hash="x", role="staff"),
                        User(username="hla", display_name="开庭乙", password_hash="x", role="staff")])
            active = case("C-ACTIVE", "一审立案受理", first_court_hearing_date="2026-03-01", second_court_hearing_date="2026-06-01",
                          execution_court_hearing_date="2025-12-30")
            judged = case("C-JUDGED", "一审判决结案", first_court_hearing_date="2026-02-01")  # 已结案，不算在办，开庭照算
            reviewing = case("C-REVIEW", "归档审核")  # 归档审核中不算在办，也还不算归档
            archived = case("C-ARCH", "已归档", archive_reviewed_at="2026-05-01T10:00:00")
            loss = case("C-LOSS", "亏损归档", archived_at="2026-07-01")
            old = case("C-OLD", "已归档", archive_reviewed_at="2025-12-01")  # 去年归档不算
            two_lawyers = case("C-TWO", "文书准备", hearing_lawyer="hla、hlb")
            tester = case("C-TEST", "文书准备", customer="测试11.13", first_court_hearing_date="2026-01-05")
            cases = [active, judged, reviewing, archived, loss, old, two_lawyers, tester]
            db.add_all(cases)
            await db.flush()
            db.add(IncomingPayment(source_kind="test", receipt_no="R1", received_date=date(2026, 3, 1), amount=1000, payer_name="客户甲",
                                   status="已分配", claimed_customer="客户甲", allocated_amount=1000, operator="admin",
                                   allocations=[{"amount": 1000, "case_id": active.id, "case_no": "C-ACTIVE", "fee_type": "代理费"}]))
            await db.commit()
            await refresh_person_names(db, force=True)
            today = date(2026, 11, 1)
            hearing = await staff_performance(db, [], cases, year=2026, today=today, role="hearing", amount_visible=True)
            investigator = await staff_performance(db, [], cases, year=2026, today=today, role="investigator", amount_visible=True)
            hidden = await staff_performance(db, [], cases, year=2026, today=today, role="source", name="案源", amount_visible=False)
        self.assertEqual(hearing["totals"]["new_cases"], 6)  # 去年建的 C-OLD 和测试客户不算
        hearing["totals"].pop("new_cases"); [row.pop("new_cases") for row in hearing["rows"]]
        self.assertEqual(hearing["totals"], {"active_cases": 2, "hearings": 3, "archived_cases": 2, "loss_archived_cases": 1, "agency_fee": 1000})
        rows = {row["person"]: row for row in hearing["rows"]}
        self.assertEqual(rows["开庭乙"], {"person": "开庭乙", "active_cases": 2, "hearings": 3, "archived_cases": 2, "loss_archived_cases": 1, "agency_fee": 1000})
        self.assertEqual(rows["hlb"]["active_cases"], 1)  # 同角色多人各算一次
        self.assertEqual({row["person"]: row["agency_fee"] for row in investigator["rows"]}, {"inv": 1000})
        self.assertIsNone(hidden["totals"]["agency_fee"])  # 没有金额权限不给代理费
        self.assertEqual([row["person"] for row in hidden["rows"]], ["案源甲"])
