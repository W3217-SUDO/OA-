"""8.14 row 15: show every unpaid customer case and split one plan across cases."""

from __future__ import annotations

from datetime import date
import unittest

import httpx
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database import Base, get_db
from app.main import app
from app.models import BusinessRecord, IncomingPayment, ReceivablePlan, User
from app.security import current_identity


API = settings.api_prefix
ADMIN = {
    "username": "row15-admin",
    "role": "admin",
    "display_name": "Row 15 Admin",
    "department": "Finance",
}


class IncomingAllocationCasesRow15Test(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.sessions = async_sessionmaker(
            self.engine, expire_on_commit=False, class_=AsyncSession,
        )
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with self.sessions() as db:
            db.add(User(
                username="row15-admin", display_name="Row 15 Admin",
                department="Finance", role="admin", password_hash="x", is_active=True,
            ))
            customer = BusinessRecord(
                module="customer", serial_no="CODEX-814-R15-CUSTOMER",
                title="CODEX Row 15 Customer", customer="CODEX Row 15 Customer",
                status="签约", owner="row15-admin", department="Finance", data={},
            )
            contract = BusinessRecord(
                module="contract", serial_no="CODEX-814-R15-CONTRACT",
                title="CODEX Row 15 Contract", customer="CODEX Row 15 Customer",
                status="审批通过", owner="row15-admin", department="Finance", data={},
            )
            db.add_all([customer, contract])
            await db.flush()
            case_one = BusinessRecord(
                module="case", serial_no="CODEX-814-R15-CASE-1",
                title="Row 15 Case One", customer=contract.customer,
                status="一审立案受理", owner="row15-admin", department="Finance",
                data={"contract_id": contract.id, "plaintiff": "原告甲", "defendant": "被告甲", "case_stage": "一审立案受理"},
            )
            case_two = BusinessRecord(
                module="case", serial_no="CODEX-814-R15-CASE-2",
                title="Row 15 Case Two", customer=contract.customer,
                status="一审和解结案", owner="row15-admin", department="Finance",
                data={"contract_no": contract.serial_no, "plaintiff": "原告乙", "defendant": "被告乙", "case_stage": "一审和解结案"},
            )
            plan = ReceivablePlan(
                contract_record_id=contract.id, phase="律师代理费",
                due_date=date.today(), amount=3000, received_amount=0,
                status="待收款", payer=contract.customer,
            )
            payment = IncomingPayment(
                receipt_no="CODEX-814-R15-RECEIPT", received_date=date.today(),
                amount=3000, payer_name="CODEX Row 15 Payer",
                bank_reference="CODEX-814-R15-BANK", status="待分配",
                claimed_customer=contract.customer, claimant="row15-admin",
                operator="row15-admin",
            )
            db.add_all([case_one, case_two, plan, payment])
            await db.commit()
            self.payment_id = payment.id
            self.plan_id = plan.id

        self.previous_overrides = dict(app.dependency_overrides)
        app.dependency_overrides[get_db] = self.override_db
        app.dependency_overrides[current_identity] = lambda: ADMIN
        self.client = httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://row15.test",
        )

    async def override_db(self):
        async with self.sessions() as db:
            yield db

    async def asyncTearDown(self) -> None:
        await self.client.aclose()
        app.dependency_overrides.clear()
        app.dependency_overrides.update(self.previous_overrides)
        await self.engine.dispose()

    async def test_candidates_and_split_allocation_cover_all_customer_cases(self) -> None:
        response = await self.client.get(
            f"{API}/finance/incoming-payments/{self.payment_id}/allocation-candidates",
        )
        self.assertEqual(response.status_code, 200, response.text)
        rows = response.json()["items"]
        self.assertEqual({row["case_no"] for row in rows}, {
            "CODEX-814-R15-CASE-1", "CODEX-814-R15-CASE-2",
        })
        self.assertTrue(all(row["remaining_amount"] == 3000 for row in rows))

        allocation = await self.client.post(
            f"{API}/finance/incoming-payments/{self.payment_id}/allocate",
            json={
                "allocations": [
                    {"receivable_plan_id": self.plan_id, "case_no": rows[0]["case_no"], "amount": 1200},
                    {"receivable_plan_id": self.plan_id, "case_no": rows[1]["case_no"], "amount": 1800},
                ],
                "comment": "row 15 split allocation",
            },
        )
        self.assertEqual(allocation.status_code, 200, allocation.text)
        self.assertEqual(allocation.json()["status"], "已分配")
        self.assertEqual(len(allocation.json()["allocations"]), 2)
        async with self.sessions() as db:
            plan = await db.get(ReceivablePlan, self.plan_id)
            self.assertEqual(plan.received_amount, 3000)
            self.assertEqual(plan.status, "已收款")


class IncomingAllocationProjectionTest(unittest.TestCase):
    def setUp(self):
        from app.core.incoming_allocation_projection import normalize_incoming_allocation, normalize_settlement_allocation_times
        self.normalize = normalize_incoming_allocation
        self.snapshot = normalize_settlement_allocation_times

    def legacy(self, **extra):
        return {"fee_id": 101, "case_fee_id": 101, "finance_record_id": 101, "amount": 25,
                "source_object": {"PaymentId": 2134, "SeqId": 6165, "CreateTime": "2023-03-20T09:19:54.027000"}, **extra}

    def test_public_fee_id_resolver_has_one_alias_contract(self):
        from fastapi import HTTPException
        from app.core.incoming_allocation_projection import allocation_fee_id
        for key in ("fee_record_id", "fee_id", "case_fee_id", "finance_record_id"):
            self.assertEqual(allocation_fee_id({key: "101"}), 101)
            for empty in (None, "", 0, "0"):
                self.assertIsNone(allocation_fee_id({key: empty}))
            for invalid in (True, -1, "1.2", "abc", "²"):
                with self.assertRaises(HTTPException):
                    allocation_fee_id({key: invalid})
        with self.assertRaises(HTTPException):
            allocation_fee_id({"fee_id": 101, "finance_record_id": 102})

    def test_aliases_and_precise_legacy_time_do_not_mutate_source(self):
        source = self.legacy()
        result = self.normalize(source, receipt_no="HZ-RCPT-2134")
        self.assertEqual(result["fee_record_id"], 101)
        self.assertEqual(result["allocated_at"], "2023-03-20T09:19:54.027000")
        self.assertEqual(result["allocation_source_id"], 6165)
        self.assertNotIn("allocated_at", source)
        self.assertNotIn("fee_record_id", source)

    def test_conflicting_fee_keys_and_receipt_are_rejected(self):
        from fastapi import HTTPException
        for source, number in ((self.legacy(fee_record_id=102), "HZ-RCPT-2134"), (self.legacy(), "HZ-RCPT-999")):
            with self.assertRaises(HTTPException) as failure:
                self.normalize(source, receipt_no=number)
            self.assertEqual(failure.exception.status_code, 409)

    def test_missing_source_never_uses_receipt_date(self):
        for source in ({"amount": 12}, {"fee_record_id": 101, "received_date": "2023-03-09"}):
            result = self.normalize(source, receipt_no="HZ-RCPT-2134")
            self.assertFalse(result.get("allocated_at"))

    def test_existing_timestamp_keeps_its_timezone_and_precision(self):
        stamp = "2026-10-12T09:01:02.123456+08:00"
        result = self.normalize(self.legacy(allocated_at=stamp), receipt_no="HZ-RCPT-2134")
        self.assertEqual(result["allocated_at"], stamp)

    def test_snapshot_is_idempotent_and_never_guesses_duplicate_fee_events(self):
        source = self.legacy()
        data = {"allocation_details": [{"fee_id": 101, "current_amount": 25, "allocated_at": ""}]}
        normalized = self.snapshot(data, [source], receipt_no="HZ-RCPT-2134")
        self.assertEqual(normalized["allocation_details"][0]["allocated_at"], source["source_object"]["CreateTime"])
        self.assertEqual(normalized, self.snapshot(normalized, [source], receipt_no="HZ-RCPT-2134"))
        self.assertEqual(data["allocation_details"][0]["allocated_at"], "")
        ambiguous = self.snapshot(data, [source, source], receipt_no="HZ-RCPT-2134")
        self.assertEqual(ambiguous["allocation_details"][0]["allocated_at"], "")
        wrong_fee = {"allocation_details": [{"fee_id": 102, "allocation_source_id": 6165}]}
        self.assertNotIn("allocated_at", self.snapshot(wrong_fee, [source], receipt_no="HZ-RCPT-2134")["allocation_details"][0])

    def test_export_preserves_allocation_seconds(self):
        from app.areas.finance.settlement_export_templates import case_values
        self.assertEqual(case_values({"allocated_at": "2023-03-20T09:19:54.027000"})[6], "2023-03-20 09:19:54.027000")


if __name__ == "__main__":
    unittest.main()
