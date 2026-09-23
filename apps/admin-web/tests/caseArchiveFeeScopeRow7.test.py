"""验证案件归档只以需结清的律所费用作为回款门槛。"""

import unittest
from datetime import date

import httpx
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database import Base, get_db
from app.main import app
from app.models import BusinessRecord, IncomingPayment, User
from app.security import current_identity


APPLICANT = {"username": "CODEX-0922-R7-applicant", "role": "admin", "display_name": "归档申请人", "department": "测试部"}
REVIEWER = {"username": "CODEX-0922-R7-reviewer", "role": "admin", "display_name": "归档审核人", "department": "测试部"}


class CaseArchiveFeeScopeRow7Test(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine(
            "sqlite+aiosqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.sessions = async_sessionmaker(self.engine, class_=AsyncSession, expire_on_commit=False)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

        async def database():
            async with self.sessions() as db:
                yield db

        self.previous_overrides = dict(app.dependency_overrides)
        app.dependency_overrides[get_db] = database
        app.dependency_overrides[current_identity] = lambda: APPLICANT
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://case-archive-row7.test")
        async with self.sessions() as db:
            db.add_all([
                User(username=identity["username"], display_name=identity["display_name"],
                     role="admin", department="测试部", password_hash="test", is_active=True)
                for identity in (APPLICANT, REVIEWER)
            ])
            await db.commit()

    async def asyncTearDown(self):
        await self.client.aclose()
        app.dependency_overrides.clear()
        app.dependency_overrides.update(self.previous_overrides)
        await self.engine.dispose()

    async def create_case_with_fees(self, suffix, fee_specs):
        async with self.sessions() as db:
            case = BusinessRecord(
                module="case", serial_no=f"CODEX-0922-R7-{suffix}", title=f"归档费用{suffix}",
                customer="测试客户", status="一审阶段", owner=APPLICANT["username"],
                department="测试部", data={"case_creation_step": "completed"},
            )
            db.add(case)
            await db.flush()
            fees = []
            for index, spec in enumerate(fee_specs, 1):
                fee = BusinessRecord(
                    module="finance", serial_no=f"CODEX-0922-R7-{suffix}-F{index}",
                    title=spec.get("title", "案件费用"), customer=case.customer,
                    status="草稿", owner=APPLICANT["username"], department="测试部",
                    data={"case_id": case.id, "case_no": case.serial_no, "amount": spec.get("amount", 100), **spec["data"]},
                )
                db.add(fee)
                fees.append(fee)
            await db.commit()
            return case.id, [fee.id for fee in fees]

    async def test_refund_platform_and_internal_fees_do_not_block_submit_or_review(self):
        case_id, _ = await self.create_case_with_fees("EXEMPT", [
            {"title": "律师代理费(退费)", "amount": 20,
             "data": {"fee_type": "代理费", "expense_subtype": "律师代理费(退费)", "expense_scope": "律所", "refund_fee": True}},
            {"title": "律师代理费（退费）", "amount": 20,
             "data": {"fee_type": "代理费", "expense_subtype": "律师代理费（退费）", "expense_scope": "律所"}},
            {"title": "平台代理费", "data": {"fee_type": "代理费", "expense_scope": "平台"}},
            {"title": "内部费用", "data": {"fee_type": "内部费用", "expense_scope": "内部"}},
            {"title": "内部绩效", "data": {"fee_type": "内部绩效"}},
        ])
        readiness = await self.client.get(f"{settings.api_prefix}/cases/{case_id}/archive-readiness")
        self.assertEqual(readiness.status_code, 200, readiness.text)
        self.assertTrue(readiness.json()["checks"]["fees_settled"])
        self.assertEqual(readiness.json()["check_details"]["unsettled_fees"], [])

        submitted = await self.client.post(
            f"{settings.api_prefix}/cases/{case_id}/archive",
            json={"archive_type": "normal", "submit": True},
        )
        self.assertEqual(submitted.status_code, 200, submitted.text)
        self.assertEqual(submitted.json()["record"]["status"], "待归档审核")
        app.dependency_overrides[current_identity] = lambda: REVIEWER
        reviewed = await self.client.post(
            f"{settings.api_prefix}/cases/{case_id}/archive/review",
            json={"approved": True, "comment": "费用已核对", "archive_no": "CODEX-0922-R7-ARCHIVE"},
        )
        self.assertEqual(reviewed.status_code, 200, reviewed.text)
        async with self.sessions() as db:
            case = await db.get(BusinessRecord, case_id)
            self.assertEqual(case.status, "已归档")

    async def test_unpaid_firm_fee_still_blocks_without_persisting_archive(self):
        case_id, _ = await self.create_case_with_fees("UNPAID", [
            {"title": "律师代理费", "data": {"fee_type": "代理费", "expense_scope": "律所"}},
        ])
        response = await self.client.post(
            f"{settings.api_prefix}/cases/{case_id}/archive",
            json={"archive_type": "normal", "submit": True},
        )
        self.assertEqual(response.status_code, 409, response.text)
        self.assertIn("尚差 100.00 元", response.json()["detail"])
        async with self.sessions() as db:
            case = await db.get(BusinessRecord, case_id)
            self.assertEqual(case.status, "一审阶段")
            self.assertNotIn("archive_submitted_at", case.data)

    async def test_legacy_firm_fee_without_scope_still_requires_full_allocation(self):
        case_id, fee_ids = await self.create_case_with_fees("LEGACY", [
            {"title": "第三方费用", "data": {"fee_type": "其他费用"}},
        ])
        async with self.sessions() as db:
            db.add(IncomingPayment(
                receipt_no="CODEX-0922-R7-RECEIPT", received_date=date(2026, 9, 23),
                amount=40, payer_name="测试客户", status="部分分配", operator=APPLICANT["username"],
                allocated_amount=40,
                allocations=[{"fee_record_id": fee_ids[0], "amount": 40}],
            ))
            await db.commit()
        readiness = await self.client.get(f"{settings.api_prefix}/cases/{case_id}/archive-readiness")
        self.assertEqual(readiness.status_code, 200, readiness.text)
        self.assertFalse(readiness.json()["checks"]["fees_settled"])
        self.assertEqual(readiness.json()["check_details"]["unsettled_fees"][0]["outstanding"], 60)

        async with self.sessions() as db:
            db.add(IncomingPayment(
                receipt_no="CODEX-0922-R7-RECEIPT-FINAL", received_date=date(2026, 9, 23),
                amount=60, payer_name="测试客户", status="已分配", operator=APPLICANT["username"],
                allocated_amount=60,
                allocations=[{"fee_record_id": fee_ids[0], "amount": 60}],
            ))
            await db.commit()
        ready_after_allocation = await self.client.get(f"{settings.api_prefix}/cases/{case_id}/archive-readiness")
        self.assertEqual(ready_after_allocation.status_code, 200, ready_after_allocation.text)
        self.assertTrue(ready_after_allocation.json()["checks"]["fees_settled"])
        submitted = await self.client.post(
            f"{settings.api_prefix}/cases/{case_id}/archive",
            json={"archive_type": "normal", "submit": True},
        )
        self.assertEqual(submitted.status_code, 200, submitted.text)
        self.assertEqual(submitted.json()["record"]["status"], "待归档审核")


if __name__ == "__main__":
    unittest.main()
