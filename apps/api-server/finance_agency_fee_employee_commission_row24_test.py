import asyncio
import unittest
from datetime import date
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.cases import _recalculate_case_draft_commissions
from app.core.finance import _finance_fee_commission_details, _finance_fee_commission_payload
from app.models import Base, BusinessRecord, HrSubrecord, User
from app.models_shared import FinanceFeeCommissionDetailInput, FinanceFeeInput


class AgencyFeeEmployeeCommissionRow24Test(unittest.TestCase):
    @staticmethod
    async def _commission_fixture(session, *, rate: float | None = 0.1):
        username = "codex-812-row24-a"
        user = User(username=username, display_name="测试提成员工", password_hash="x", is_active=True)
        employee = BusinessRecord(
            module="hr", serial_no="CODEX-812-ROW24-HR", title="测试提成员工",
            owner=username, data={"username": username},
        )
        case = BusinessRecord(
            module="case", serial_no="CODEX-812-ROW24-CASE", title="测试案件",
            customer="CODEX 客户", owner="admin", data={"hearing_lawyer_username": username},
        )
        session.add_all([user, employee, case])
        await session.flush()
        if rate is not None:
            session.add(HrSubrecord(
                employee_id=employee.id, kind="commission", created_by="admin", updated_by="admin",
                data={"start_date": str(date.today()), "hearing_rate": rate},
            ))
            await session.flush()
        return case, employee, username

    @staticmethod
    def _automatic_fee(case, *, status="草稿", details=None):
        return BusinessRecord(
            module="finance", serial_no=f"CODEX-812-ROW24-FEE-{status}", title="代理费",
            customer=case.customer, status=status, owner="admin",
            data={
                "amount": 1000, "fee_type": "代理费", "case_id": case.id,
                "case_no": case.serial_no, "commission_mode": "automatic",
                "commission_details": details or [], "commission_missing_messages": [],
            },
        )

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

    def test_manual_commission_allows_same_employee_with_distinct_types(self):
        async def scenario():
            engine = create_async_engine("sqlite+aiosqlite:///:memory:")
            async with engine.begin() as connection:
                await connection.run_sync(Base.metadata.create_all)
            session_factory = async_sessionmaker(engine, expire_on_commit=False)
            async with session_factory() as session:
                session.add(User(username="codex-812-row24-a", display_name="测试提成员工", password_hash="x", is_active=True))
                await session.commit()
                body = FinanceFeeInput(
                    title="CODEX-812-ROW24-手工", amount=1000, fee_type="代理费", handler="admin",
                    commission_mode="manual",
                    commission_details=[
                        FinanceFeeCommissionDetailInput(employee_username="codex-812-row24-a", commission_type="案源提成", amount=100),
                        FinanceFeeCommissionDetailInput(employee_username="codex-812-row24-a", commission_type="开庭提成", amount=200),
                    ],
                )
                details = await _finance_fee_commission_details(body, 1000, session)
                self.assertEqual([item["commission_type"] for item in details], ["案源提成", "开庭提成"])
            await engine.dispose()
        asyncio.run(scenario())

    def test_automatic_payload_uses_server_scheme_instead_of_body_details(self):
        async def scenario():
            engine = create_async_engine("sqlite+aiosqlite:///:memory:")
            async with engine.begin() as connection:
                await connection.run_sync(Base.metadata.create_all)
            session_factory = async_sessionmaker(engine, expire_on_commit=False)
            async with session_factory() as session:
                case, _employee, username = await self._commission_fixture(session)
                body = FinanceFeeInput(
                    title="CODEX-812-ROW24-自动", amount=1000, fee_type="代理费", handler="admin",
                    case_record_id=case.id, commission_mode="automatic",
                    commission_details=[FinanceFeeCommissionDetailInput(employee_username=username, amount=999)],
                )
                payload = await _finance_fee_commission_payload(body, 1000, session, case_record=case)
                self.assertEqual(payload["commission_mode"], "automatic")
                self.assertEqual(payload["commission_details"][0]["amount"], 100)
                self.assertEqual(payload["commission_details"][0]["calculation_source"], "case_commission_scheme")
            await engine.dispose()
        asyncio.run(scenario())

    def test_plain_agency_fee_does_not_create_commission_until_dedicated_action(self):
        async def scenario():
            engine = create_async_engine("sqlite+aiosqlite:///:memory:")
            async with engine.begin() as connection:
                await connection.run_sync(Base.metadata.create_all)
            session_factory = async_sessionmaker(engine, expire_on_commit=False)
            async with session_factory() as session:
                case, _employee, _username = await self._commission_fixture(session)
                body = FinanceFeeInput(
                    title="CODEX-812-ROW24-普通代理费",
                    amount=1000,
                    fee_type="代理费",
                    handler="admin",
                    case_record_id=case.id,
                )
                payload = await _finance_fee_commission_payload(body, 1000, session, case_record=case)
                self.assertEqual(payload["commission_mode"], "manual")
                self.assertEqual(payload["commission_details"], [])
                self.assertEqual(payload["commission_missing_messages"], [])
            await engine.dispose()
        asyncio.run(scenario())

    def test_legacy_manual_update_omitting_mode_and_details_preserves_rows(self):
        async def scenario():
            engine = create_async_engine("sqlite+aiosqlite:///:memory:")
            async with engine.begin() as connection:
                await connection.run_sync(Base.metadata.create_all)
            session_factory = async_sessionmaker(engine, expire_on_commit=False)
            async with session_factory() as session:
                body = FinanceFeeInput(title="CODEX-812-ROW24-历史", amount=1000, fee_type="代理费", handler="admin")
                previous = {"commission_details": [{"employee_username": "legacy", "amount": 250, "commission_type": "历史手工"}]}
                payload = await _finance_fee_commission_payload(body, 1000, session, case_record=None, existing_data=previous)
                self.assertEqual(payload["commission_mode"], "manual")
                self.assertEqual(payload["commission_details"], previous["commission_details"])
            await engine.dispose()
        asyncio.run(scenario())

    def test_personnel_recalculation_recovers_missing_automatic_draft_only(self):
        async def scenario():
            engine = create_async_engine("sqlite+aiosqlite:///:memory:")
            async with engine.begin() as connection:
                await connection.run_sync(Base.metadata.create_all)
            session_factory = async_sessionmaker(engine, expire_on_commit=False)
            async with session_factory() as session:
                case, employee, _username = await self._commission_fixture(session, rate=None)
                automatic = self._automatic_fee(case)
                manual = BusinessRecord(
                    module="finance", serial_no="CODEX-812-ROW24-MANUAL", title="代理费", customer=case.customer,
                    status="草稿", owner="admin", data={
                        "amount": 1000, "fee_type": "代理费", "case_id": case.id, "case_no": case.serial_no,
                        "commission_details": [{"employee_username": "manual", "amount": 300}],
                    },
                )
                approved = self._automatic_fee(case, status="已审批", details=[{"amount": 700}])
                paid = self._automatic_fee(case, status="已付款", details=[{"amount": 800}])
                session.add_all([automatic, manual, approved, paid])
                await session.flush()
                first = await _recalculate_case_draft_commissions(case, session, "admin")
                self.assertTrue(first["missing_messages"])
                self.assertEqual(automatic.data["commission_details"], [])
                session.add(HrSubrecord(
                    employee_id=employee.id, kind="commission", created_by="admin", updated_by="admin",
                    data={"start_date": str(date.today()), "hearing_rate": 0.1},
                ))
                await session.flush()
                second = await _recalculate_case_draft_commissions(case, session, "admin")
                self.assertEqual(second["updated_fee_ids"], [automatic.id])
                self.assertEqual(automatic.data["commission_details"][0]["amount"], 100)
                self.assertEqual(manual.data["commission_details"][0]["amount"], 300)
                self.assertEqual(approved.data["commission_details"][0]["amount"], 700)
                self.assertEqual(paid.data["commission_details"][0]["amount"], 800)
            await engine.dispose()
        asyncio.run(scenario())


if __name__ == "__main__":
    unittest.main()
