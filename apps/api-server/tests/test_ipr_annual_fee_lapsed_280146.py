"""280146（高勤兰，tgn 11-04 确认）：沪知老系统迁移来、没有任何后续记录的专利视为已失效，不进年费监控和年费清单。"""
import unittest
from datetime import date

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.areas.ipr import annual_fee_monitor as monitor
from app.database import Base
from app.models import BusinessRecord, IprCaseAnnualFee


def patent(serial, number, source="hz_crm_ipr", **data):
    return BusinessRecord(module="ipr_case", serial_no=serial, title=serial, customer="客户", status="年费监控", owner="admin", department="知产",
                          data={"case_type": "发明专利", "case_phase": "年费监控", "application_no": number, "migration_source": source, **data})


class LapsedLegacyPatentTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)

    async def asyncTearDown(self):
        await self.engine.dispose()

    async def test_only_legacy_without_follow_up_is_lapsed(self):
        async with self.sessions() as db:
            stale = patent("SHPD1711392", "201710000001.1")
            no_number = patent("SHPD1711287", "")
            duplicated = patent("SHPD1700001", "201710000002.2")
            other_case = patent("HDPD1700001", "2017 10000002.2", source="hd_ipr")
            with_fee = patent("SHPD1700003", "201710000003.3")
            with_payment = patent("SHPD1700004", "201710000004.4")
            manual = patent("SHPD1700005", "201710000005.5", annual_fee_monitoring="true")
            hd_case = patent("HDPD1700009", "201710000009.9", source="hd_ipr")
            db.add_all([stale, no_number, duplicated, other_case, with_fee, with_payment, manual, hd_case])
            await db.flush()
            db.add(IprCaseAnnualFee(case_record_id=with_fee.id, fee_year=2026, fee_name="第9年年费", due_date=date(2026, 5, 1), created_by="admin"))
            db.add(BusinessRecord(module="finance", serial_no="F1", title="年费", customer="客户", status="已记录", owner="admin", department="知产",
                                  data={"case_id": str(with_payment.id), "fee_type_name": "发明专利第9年年费"}))  # PostgreSQL 的 ->> 取出来就是文本
            await db.commit()
            records = [stale, no_number, duplicated, other_case, with_fee, with_payment, manual, hd_case]
            lapsed = await monitor._lapsed_legacy_case_ids(records, db)
        self.assertEqual(lapsed, {stale.id, no_number.id}, "有同一专利其他案件、OA 有年费记录、手动加入监控、恒达迁来的都照常监控")


if __name__ == "__main__":
    unittest.main()
