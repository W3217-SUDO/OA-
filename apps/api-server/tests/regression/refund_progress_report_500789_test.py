"""BUG 500789：退费进度按律师助理统计，每人一行、横向退费进度，只算未归档案件。"""
import unittest

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

import app.main  # noqa: F401  注册全部模型
from app.core.progress_reports import UNASSIGNED_PERSON, refund_progress_cases, refund_progress_report
from app.database import Base
from app.models import BusinessRecord


ADMIN = {"username": "admin", "role": "admin"}


class RefundProgressReportTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            connect_args={"check_same_thread": False}, poolclass=StaticPool,
        )
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

    async def asyncTearDown(self):
        await self.engine.dispose()

    async def _seed(self, db):
        def case(no, status, assistant):
            return BusinessRecord(module="case", serial_no=no, title=no, customer="客户" + no, status=status, owner="admin", department="诉讼部", data={"assistant": assistant})
        a, b, archived, blank = case("C-A", "一审待客户回款", "梁晨宇,周子怡"), case("C-B", "执行受理", "梁晨宇"), case("C-ARCH", "已归档", "梁晨宇"), case("C-BLANK", "文书准备", "")
        db.add_all([a, b, archived, blank])
        await db.flush()

        def fee(case_record, code, amount=100, n=[0]):
            n[0] += 1
            return BusinessRecord(module="finance", serial_no=f"F-{case_record.serial_no}-{code}-{n[0]}", title="诉讼费", customer=case_record.customer, status="已到账", owner="admin", department="诉讼部",
                                  data={"case_record_id": case_record.id, "refund_status": int(code), "refund_amount": amount, f"refund_status{code}_start_time": "2026-10-01T00:00:00"})
        db.add_all([fee(a, "10"), fee(a, "30"), fee(a, "30"), fee(b, "30"), fee(archived, "10"), fee(blank, "40"), fee(b, "100")])
        await db.commit()
        return a, b

    async def test_rows_are_assistants_and_columns_are_refund_stages(self):
        async with self.sessions() as db:
            await self._seed(db)
            report = await refund_progress_report(ADMIN, db)
        self.assertEqual(report["stages"], ["准备材料", "客户盖章", "已提交法院", "待法院现场办理", "退费到客户", "回款待分配"])
        rows = {row["person"]: row for row in report["rows"]}
        # 已归档案件、不再办理（100）不算；同一案件两笔“已提交法院”只算一件。
        self.assertEqual(rows["梁晨宇"]["counts"]["准备材料"], 1)
        self.assertEqual(rows["梁晨宇"]["counts"]["已提交法院"], 2)
        self.assertEqual(rows["梁晨宇"]["total"], 2)
        self.assertEqual(rows["周子怡"]["total"], 1)  # 多位助理各算一次
        self.assertEqual(rows[UNASSIGNED_PERSON]["counts"]["退费到客户"], 1)
        self.assertEqual(report["rows"][-1]["person"], UNASSIGNED_PERSON)
        self.assertEqual(report["totals"]["已提交法院"], 2)
        self.assertEqual(report["total"], 3)

    async def test_number_click_lists_cases_and_fees(self):
        async with self.sessions() as db:
            a, _ = await self._seed(db)
            listing = await refund_progress_cases(ADMIN, db, person="周子怡", stage="已提交法院")
        self.assertEqual(listing["case_count"], 1)
        self.assertEqual({item["case_no"] for item in listing["items"]}, {a.serial_no})
        self.assertEqual(len(listing["items"]), 2)
        self.assertEqual(listing["items"][0]["stage_started"], "2026-10-01")


if __name__ == "__main__":
    unittest.main()
