"""8.14 row 15: allocate a customer's unpaid case fee without a prebuilt receivable plan."""

from __future__ import annotations

from datetime import date
import unittest

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.core.finance import _general_settlement_rows, _settlement_amounts_for_fee
from app.database import Base, get_db
from app.main import app
from app.models import BusinessRecord, IncomingPayment, ReceivablePlan, User
from app.security import current_identity


API = settings.api_prefix
ADMIN = {"username": "row15-admin", "role": "admin", "display_name": "Row 15 Admin", "department": "Finance"}


class IncomingPaymentCaseFeeRow15Test(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool,
        )
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with self.sessions() as db:
            admin = User(username="row15-admin", display_name="Row 15 Admin", department="Finance", role="admin", password_hash="x", is_active=True)
            customer = BusinessRecord(module="customer", serial_no="CODEX-814-R15-CUSTOMER", title="CODEX R15 Customer", customer="CODEX R15 Customer", status="active", owner="row15-admin", department="Finance")
            contract = BusinessRecord(module="contract", serial_no="CODEX-814-R15-CONTRACT", title="CODEX R15 Contract", customer="CODEX R15 Customer", status="approved", owner="row15-admin", department="Finance")
            db.add_all([admin, customer, contract])
            await db.flush()
            case_record = BusinessRecord(module="case", serial_no="CODEX-814-R15-CASE", title="CODEX R15 Case", customer="CODEX R15 Customer", status="active", owner="row15-admin", department="Finance", data={"contract_id": contract.id, "contract_no": contract.serial_no, "case_phase": "civil"})
            db.add(case_record)
            await db.flush()
            fee = BusinessRecord(module="finance", serial_no="CODEX-814-R15-FEE", title="CODEX R15 Fee", customer="CODEX R15 Customer", status="pending", owner="row15-admin", department="Finance", data={"amount": 88.0, "fee_type": "agency", "case_id": case_record.id, "case_no": case_record.serial_no})
            payment = IncomingPayment(receipt_no="CODEX-814-R15-RECEIPT", received_date=date.today(), amount=88.0, payer_name="CODEX R15 Payer", bank_reference="CODEX-814-R15-BANK", status="待分配", claimed_customer="CODEX R15 Customer", claimant="row15-admin", operator="row15-admin")
            db.add_all([fee, payment])
            await db.commit()
            self.fee_id = fee.id
            self.payment_id = payment.id
            self.case_id = case_record.id
            self.case_no = case_record.serial_no

        self.previous_overrides = dict(app.dependency_overrides)
        app.dependency_overrides[get_db] = self.override_db
        app.dependency_overrides[current_identity] = lambda: ADMIN
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://row15.test")

    async def override_db(self):
        async with self.sessions() as db:
            yield db

    async def asyncTearDown(self) -> None:
        await self.client.aclose()
        app.dependency_overrides.clear()
        app.dependency_overrides.update(self.previous_overrides)
        await self.engine.dispose()

    async def allocate(self, amount: float = 88.0):
        return await self.client.post(f"{API}/finance/incoming-payments/{self.payment_id}/allocate", json={"allocations": [{
            "receivable_plan_id": None,
            "fee_record_id": self.fee_id,
            "amount": amount,
            "case_no": self.case_no,
            "payment_method": "bank",
            "settlement_items": [{"fee_record_id": self.fee_id, "fee_type": "agency", "amount": amount}],
        }]})

    async def test_unplanned_case_fee_is_selectable_and_allocates(self) -> None:
        candidates = await self.client.get(f"{API}/finance/incoming-payments/{self.payment_id}/allocation-candidates")
        self.assertEqual(candidates.status_code, 200, candidates.text)
        row = next(item for item in candidates.json()["items"] if item["fee_record_id"] == self.fee_id)
        self.assertIsNone(row["receivable_plan_id"])
        self.assertEqual(row["case_no"], self.case_no)
        self.assertEqual(row["remaining_amount"], 88.0)

        allocation = await self.client.post(f"{API}/finance/incoming-payments/{self.payment_id}/allocate", json={"allocations": [{
            "receivable_plan_id": None,
            "fee_record_id": self.fee_id,
            "amount": 88.0,
            "case_no": self.case_no,
            "payment_method": "bank",
            "settlement_items": [{"fee_record_id": self.fee_id, "fee_type": "agency", "amount": 88.0}],
        }]})
        self.assertEqual(allocation.status_code, 200, allocation.text)
        self.assertEqual(allocation.json()["status"], "已分配")
        settlement = allocation.json()["allocations"][0]["settlement_items"][0]
        self.assertEqual(settlement["fee_record_id"], self.fee_id)
        self.assertEqual(settlement["settlement_amount"], 70.4)
        self.assertEqual(settlement["archive_fee"], 7.04)

        async with self.sessions() as db:
            plan = await db.scalar(select(ReceivablePlan))
            self.assertIsNotNone(plan)
            self.assertEqual(plan.amount, 88.0)
            self.assertEqual(plan.received_amount, 88.0)

    async def test_server_ignores_client_settlement_values_and_waives_archive_after_case_archive(self) -> None:
        async with self.sessions() as db:
            case_record = await db.get(BusinessRecord, self.case_id)
            case_record.status = "已归档"
            await db.commit()

        allocation = await self.client.post(f"{API}/finance/incoming-payments/{self.payment_id}/allocate", json={"allocations": [{
            "receivable_plan_id": None,
            "fee_record_id": self.fee_id,
            "amount": 88.0,
            "case_no": self.case_no,
            "payment_method": "bank",
            "settlement_items": [{
                "fee_record_id": self.fee_id,
                "fee_type": "伪造费用类型",
                "amount": 88.0,
                "settlement_amount": 88.0,
                "archive_fee": 66.0,
            }],
        }]})
        self.assertEqual(allocation.status_code, 200, allocation.text)
        settlement = allocation.json()["allocations"][0]["settlement_items"][0]
        self.assertEqual(settlement["fee_type"], "agency")
        self.assertEqual(settlement["settlement_amount"], 70.4)
        self.assertEqual(settlement["archive_fee"], 0.0)

    async def test_pending_settlement_uses_exact_fee_when_legacy_details_are_missing(self) -> None:
        allocation = await self.client.post(f"{API}/finance/incoming-payments/{self.payment_id}/allocate", json={"allocations": [{
            "receivable_plan_id": None,
            "fee_record_id": self.fee_id,
            "amount": 88.0,
            "case_no": self.case_no,
            "payment_method": "bank",
            "settlement_items": [{
                "fee_record_id": self.fee_id,
                "fee_type": "agency",
                "amount": 88.0,
                "settlement_amount": 88.0,
                "archive_fee": 0.0,
            }],
        }]})
        self.assertEqual(allocation.status_code, 200, allocation.text)

        async with self.sessions() as db:
            payment = await db.get(IncomingPayment, self.payment_id)
            allocations = [dict(item) for item in payment.allocations]
            allocations[0]["settlement_items"] = []
            payment.allocations = allocations
            await db.commit()

            rows = await _general_settlement_rows(ADMIN, db)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["data"]["agency_settlement_amount"], 70.4)
            self.assertEqual(rows[0]["data"]["archive_fee"], 7.04)
            self.assertEqual(rows[0]["data"]["actual_settlement_amount"], 63.36)
            self.assertEqual(rows[0]["data"]["allocation_details"][0]["fee_id"], self.fee_id)

    async def test_other_fee_is_not_counted_as_general_settlement_payable(self) -> None:
        async with self.sessions() as db:
            fee = await db.get(BusinessRecord, self.fee_id)
            case_record = await db.get(BusinessRecord, self.case_id)
            fee.data = {**fee.data, "fee_type": "第三方费用"}
            settlement_amount, archive_fee = _settlement_amounts_for_fee(fee, "第三方费用", 88.0, case_record)
            self.assertEqual(settlement_amount, 0.0)
            self.assertEqual(archive_fee, 0.0)

    async def test_partial_receipt_cannot_apply_for_general_settlement(self) -> None:
        allocation = await self.allocate(40)
        self.assertEqual(allocation.status_code, 200, allocation.text)
        response = await self.client.post(f"{API}/finance/general-settlements/apply", json={
            "receipt_ids": [self.payment_id], "comment": "partial",
        })
        self.assertEqual(response.status_code, 409, response.text)
        async with self.sessions() as db:
            settlements = (await db.scalars(select(BusinessRecord).where(BusinessRecord.module == "finance_settlement"))).all()
            self.assertEqual(settlements, [])

    async def test_delete_reverts_fee_received_amount_and_blocks_active_settlement(self) -> None:
        allocation = await self.allocate()
        self.assertEqual(allocation.status_code, 200, allocation.text)
        async with self.sessions() as db:
            fee = await db.get(BusinessRecord, self.fee_id)
            self.assertEqual(fee.data["received_amount"], 88.0)
        deleted = await self.client.delete(f"{API}/finance/incoming-payments/{self.payment_id}")
        self.assertEqual(deleted.status_code, 204, deleted.text)
        async with self.sessions() as db:
            fee = await db.get(BusinessRecord, self.fee_id)
            self.assertEqual(fee.data["received_amount"], 0.0)
            self.assertNotIn("incoming_payment_id", fee.data)

    async def test_paid_settlement_prevents_receipt_deletion(self) -> None:
        allocation = await self.allocate()
        self.assertEqual(allocation.status_code, 200, allocation.text)
        async with self.sessions() as db:
            settlement = BusinessRecord(module="finance_settlement", serial_no="CODEX-814-R15-SETTLED", title="Paid", customer="CODEX R15 Customer", status="已付款", owner=ADMIN["username"], department=ADMIN["department"], data={"receipt_id": self.payment_id})
            db.add(settlement)
            await db.commit()
        deleted = await self.client.delete(f"{API}/finance/incoming-payments/{self.payment_id}")
        self.assertEqual(deleted.status_code, 409, deleted.text)
        async with self.sessions() as db:
            self.assertIsNotNone(await db.get(IncomingPayment, self.payment_id))
            fee = await db.get(BusinessRecord, self.fee_id)
            self.assertEqual(fee.data["received_amount"], 88.0)

    async def test_bulk_revoke_reverts_fee_received_amount(self) -> None:
        allocation = await self.allocate()
        self.assertEqual(allocation.status_code, 200, allocation.text)
        revoked = await self.client.post(f"{API}/finance/incoming-payments/revoke-allocations", json={
            "payment_ids": [self.payment_id], "comment": "revoke",
        })
        self.assertEqual(revoked.status_code, 200, revoked.text)
        self.assertEqual(revoked.json()["revoked"], 1)
        async with self.sessions() as db:
            fee = await db.get(BusinessRecord, self.fee_id)
            payment = await db.get(IncomingPayment, self.payment_id)
            self.assertEqual(fee.data["received_amount"], 0.0)
            self.assertEqual(payment.allocated_amount, 0.0)
            self.assertEqual(payment.allocations, [])

    async def test_reapply_refreshes_snapshot_and_cannot_duplicate_active_application(self) -> None:
        allocation = await self.allocate()
        self.assertEqual(allocation.status_code, 200, allocation.text)
        first = await self.client.post(f"{API}/finance/general-settlements/apply", json={"receipt_ids": [self.payment_id], "comment": "first"})
        self.assertEqual(first.status_code, 201, first.text)
        first_id = first.json()["application_ids"][0]
        async with self.sessions() as db:
            record = await db.get(BusinessRecord, first_id)
            record.status = "已拒绝"
            fee = await db.get(BusinessRecord, self.fee_id)
            fee.data = {**fee.data, "settlement_amount": 44.0}
            await db.commit()
        reapplied = await self.client.post(f"{API}/finance/general-settlements/applications/reapply", json={"application_ids": [first_id], "comment": "refresh"})
        self.assertEqual(reapplied.status_code, 200, reapplied.text)
        async with self.sessions() as db:
            record = await db.get(BusinessRecord, first_id)
            self.assertEqual(record.data["agency_settlement_amount"], 44.0)
            self.assertEqual(record.data["archive_fee"], 4.4)
            record.status = "已拒绝"
            await db.commit()
        second = await self.client.post(f"{API}/finance/general-settlements/apply", json={"receipt_ids": [self.payment_id], "comment": "second"})
        self.assertEqual(second.status_code, 201, second.text)
        duplicate = await self.client.post(f"{API}/finance/general-settlements/applications/reapply", json={"application_ids": [first_id], "comment": "duplicate"})
        self.assertEqual(duplicate.status_code, 409, duplicate.text)

    async def test_review_rejects_stale_settlement_snapshot(self) -> None:
        allocation = await self.allocate()
        self.assertEqual(allocation.status_code, 200, allocation.text)
        created = await self.client.post(f"{API}/finance/general-settlements/apply", json={"receipt_ids": [self.payment_id], "comment": "first"})
        self.assertEqual(created.status_code, 201, created.text)
        application_id = created.json()["application_ids"][0]
        async with self.sessions() as db:
            fee = await db.get(BusinessRecord, self.fee_id)
            fee.data = {**fee.data, "settlement_amount": 44.0}
            await db.commit()
        reviewed = await self.client.post(f"{API}/finance/general-settlements/applications/review", json={
            "application_ids": [application_id], "approved": True, "comment": "approve",
        })
        self.assertEqual(reviewed.status_code, 409, reviewed.text)


if __name__ == "__main__":
    unittest.main()
