"""280146（高勤兰 11-05）：最后一个年度缴完后，在专利权到期日前一天再列一行“专利权到期”，年度、年费为 0；阶段失效的不列。"""
import unittest
from datetime import date
from unittest import mock

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.areas.ipr import annual_fee_monitor as monitor
from app.database import Base
from app.models import BusinessRecord


def patent(serial, phase="年费监控", **data):
    return BusinessRecord(module="ipr_case", serial_no=serial, title=serial, customer="客户", status=phase, owner="admin", department="知产",
                          data={"case_type": "国内实用新型专利", "case_phase": phase, "application_no": serial, "migration_source": "ipr_hd_20261030",
                                "application_date": "2016-12-23T00:00:00", "authorization_date": "2017-09-01T00:00:00", "first_annual_year": 1,
                                "annual_fee_monitoring": "true", **data})


class TermExpiryRowTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)

    async def asyncTearDown(self):
        await self.engine.dispose()

    async def _rows(self, start, end):
        async with self.sessions() as db:
            db.add_all([patent("HDPU1600401"), patent("HDPU1600402", phase="失效")])
            await db.commit()
            async def conditions(*_args, **_kwargs):
                return [BusinessRecord.module == "ipr_case"]
            with mock.patch("app.core.ipr._ipr_case_list_conditions", conditions):
                return await monitor._monitored_fee_rows({"username": "admin"}, db, start, end)

    async def test_expiry_row_after_last_year(self):
        rows = await self._rows(date(2026, 10, 1), date(2026, 12, 31))
        self.assertEqual([(row["serial_no"], row["due_date"], row["term_expired"]) for row in rows],
                         [("HDPU1600401", date(2026, 12, 22), True)], "阶段失效的不列")
        row = rows[0]
        self.assertEqual((row["annual_fee"], row["year_no"], row["paid"]), (0, 11, False))
        self.assertEqual(monitor._amounts_text(row), "专利权到期")
        values = monitor._export_values(row)
        self.assertEqual((values[6], values[7], values[10]), ("0", "0", "专利权到期"))
        self.assertEqual((monitor._late_fee(row, date(2027, 3, 1)), monitor._handling_fee(row)), (0, 0))

    async def test_normal_years_unchanged(self):
        rows = await self._rows(date(2025, 12, 1), date(2025, 12, 31))
        self.assertEqual([(row["serial_no"], row["year_no"], row["term_expired"]) for row in rows if row["serial_no"] == "HDPU1600401"], [("HDPU1600401", 10, False)])
        self.assertEqual(monitor._handling_fee(rows[0]), 100)


if __name__ == "__main__":
    unittest.main()
