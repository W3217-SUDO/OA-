"""待退费、费用查询等费用行的法院显示名称，不显示“冀01”这类代号；对不上的显示原值（501149）。"""
import unittest

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.finance import _invoice_case_fee_rows
from app.database import Base
from app.models import BusinessRecord, SystemParameter

ADMIN = {"username": "admin", "role": "admin", "role_ids": ["admin"]}


def case(serial, court):
    return BusinessRecord(module="case", serial_no=serial, title=serial, customer="上海某科技有限公司", status="已归档",
                          owner="admin", department="上海", data={"court": court, "first_instance_court": court})


def fee(serial, case_no, **data):
    return BusinessRecord(module="finance", serial_no=serial, title="一审诉讼费", customer="上海某科技有限公司", status="已付款",
                          owner="admin", department="上海",
                          data={"case_no": case_no, "fee_type": "官方费用", "amount": 1800, **data})


class FeeCourtNameTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        async with self.sessions() as db:
            db.add_all([
                SystemParameter(category="court", code="冀01", name="河北省石家庄市中级人民法院"),
                SystemParameter(category="court", code="苏0581", name="常熟市人民法院", is_active=False),
                case("GD1", "冀01"), case("GD2", "苏0581"), case("GD3", "黄浦法院"), case("GD4", "X99"),
                fee("F1", "GD1"), fee("F2", "GD2"), fee("F3", "GD3"), fee("F4", "GD4"),
                fee("F5", "GD1", court="冀01", payee="冀01"),
            ])
            await db.commit()

    async def asyncTearDown(self):
        await self.engine.dispose()

    async def test_court_code_shows_name(self):
        async with self.sessions() as db:
            rows = await _invoice_case_fee_rows(ADMIN, db, scope="company", include_all_fee_types=True)
        courts = {row["serial_no"]: row["data"]["court_name"] for row in rows}
        self.assertEqual(courts, {"F1": "河北省石家庄市中级人民法院", "F2": "常熟市人民法院", "F3": "黄浦法院",
                                  "F4": "X99", "F5": "河北省石家庄市中级人民法院"})
        payees = {row["serial_no"]: row["data"]["paid_organization"] for row in rows}
        self.assertEqual(payees["F1"], "河北省石家庄市中级人民法院")
        self.assertEqual(payees["F5"], "河北省石家庄市中级人民法院")


if __name__ == "__main__":
    unittest.main()
