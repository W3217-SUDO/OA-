import asyncio
import unittest
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.main import FinanceFeeInput, FinanceFeeCommissionDetailInput, _finance_fee_commission_details
from app.models import Base, User


class AgencyFeeEmployeeCommissionRow24Test(unittest.TestCase):
    def test_agency_fee_commission_uses_active_employee_and_limits_total(self):
        async def scenario():
            engine = create_async_engine("sqlite+aiosqlite:///:memory:")
            async with engine.begin() as connection:
                await connection.run_sync(Base.metadata.create_all)
            session_factory = async_sessionmaker(engine, expire_on_commit=False)
            async with session_factory() as session:
                session.add(User(username="codex-812-row24-a", display_name="测试提成员工", password_hash="x", is_active=True))
                await session.commit()
                body = FinanceFeeInput(
                    title="CODEX-812-ROW24-代理费",
                    amount=1000,
                    fee_type="代理费",
                    handler="admin",
                    commission_details=[FinanceFeeCommissionDetailInput(employee_username="codex-812-row24-a", amount=300, remark="测试")],
                )
                details = await _finance_fee_commission_details(body, 1000, session)
                self.assertEqual(details[0]["employee_username"], "codex-812-row24-a")
                self.assertEqual(details[0]["employee_display_name"], "测试提成员工")
                self.assertEqual(details[0]["amount"], 300)
                self.assertEqual((await session.scalars(select(User).where(User.username == "codex-812-row24-a"))).one().display_name, "测试提成员工")
            await engine.dispose()
        asyncio.run(scenario())

    def test_non_agency_fee_rejects_commission_details(self):
        async def scenario():
            engine = create_async_engine("sqlite+aiosqlite:///:memory:")
            async with engine.begin() as connection:
                await connection.run_sync(Base.metadata.create_all)
            session_factory = async_sessionmaker(engine, expire_on_commit=False)
            async with session_factory() as session:
                body = FinanceFeeInput(title="x", amount=100, fee_type="其他费用", handler="admin", commission_details=[FinanceFeeCommissionDetailInput(employee_username="x", amount=1)])
                with self.assertRaisesRegex(Exception, "只有代理费"):
                    await _finance_fee_commission_details(body, 100, session)
            await engine.dispose()
        asyncio.run(scenario())


if __name__ == "__main__":
    unittest.main()
