"""CPI-D tests: explicit in-memory engine only, no application lifespan or business DB."""
import unittest
from datetime import date
from unittest.mock import AsyncMock, patch

from fastapi import FastAPI, HTTPException
from httpx import ASGITransport, AsyncClient
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.areas.finance.router import (
    create_invoice_application, get_invoice_application, invoice_application_context,
    router, update_invoice_application,
)
from app.database import Base, get_db
from app.models import BusinessRecord, FinanceTransaction, IncomingPayment, RolePermission, User, WorkflowEvent
from app.models_shared import InvoiceApplicationInput
from app.security import current_identity
from app.config import settings
from app.core.finance import _invoice_fee_details


ADMIN = {"username": "CODEX-CPI-D", "role": "admin", "display_name": "CODEX-CPI-D", "department": "TEST"}


class InvoiceInputTest(unittest.TestCase):
    def payload(self, **extra):
        return {"customer": "CODEX-CPI-D-CUSTOMER", "invoice_title": "TEST", "taxpayer_id": "TEST",
                "amount": 100, "case_fee_ids": [1, 2], **extra}

    def test_multiple_services_normalized_without_losing_extensions(self):
        value = InvoiceApplicationInput(**self.payload(service_items=[
            {"service_name": "A", "quantity": "2", "unit_price": "30", "tax_rate": 6, "tax_amount": "3.40", "unit": "unit"},
            {"service_name": "B", "quantity": 1, "unit_price": 40},
        ]))
        self.assertEqual([row["amount"] for row in value.service_items], [60, 40])
        self.assertEqual(value.service_items[0]["unit"], "unit")
        self.assertEqual(value.service_items[0]["tax_amount"], 3.4)

    def test_bad_numbers_and_totals_rejected(self):
        base = {"service_name": "A", "quantity": 1, "unit_price": 100}
        for delta in ({"quantity": 0}, {"unit_price": -1}, {"amount": 99}, {"tax_rate": 101},
                      {"tax_amount": -1}, {"tax_amount": "nan"}, {"unit_price": "Infinity"}, {"service_name": " "}):
            with self.subTest(delta=delta), self.assertRaises(ValidationError):
                InvoiceApplicationInput(**self.payload(service_items=[{**base, **delta}]))
        for amount in (float("inf"), float("nan"), 0.001):
            with self.assertRaises(ValidationError):
                InvoiceApplicationInput(**self.payload(amount=amount))
        with self.assertRaises(ValidationError):
            InvoiceApplicationInput(**self.payload(service_items=[{**base, "unit_price": 99}]))

    def test_source_allocation_set_and_sum(self):
        for rows in ([{"fee_id": 1, "amount": 100}], [{"fee_id": 1, "amount": 40}, {"fee_id": 1, "amount": 60}],
                     [{"fee_id": 1, "amount": 40}, {"fee_id": 2, "amount": 50}],
                     [{"fee_id": 1, "amount": -1}, {"fee_id": 2, "amount": 101}]):
            with self.subTest(rows=rows), self.assertRaises(ValidationError):
                InvoiceApplicationInput(**self.payload(case_fee_allocations=rows))


class InvoiceRuntimeTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        tables = [User.__table__, RolePermission.__table__, BusinessRecord.__table__, WorkflowEvent.__table__,
                  FinanceTransaction.__table__, IncomingPayment.__table__]
        async with self.engine.begin() as connection:
            await connection.run_sync(lambda conn: Base.metadata.create_all(conn, tables=tables))
        async with self.sessions() as db:
            db.add(User(username=ADMIN["username"], display_name="TEST", department="TEST", role="admin", password_hash="test", is_active=True))
            self.customer = self.record("customer", "CUSTOMER", {"credit_code": "CODEX-TAX", "contact_address": "CONTACT",
                "registered_address": "REGISTERED", "phone": "000", "bank_name": "BANK", "bank_account": "ACCOUNT"})
            self.customer.title = self.customer.customer
            db.add(self.customer)
            self.contracts, self.cases, self.fees = [], [], []
            for index in range(2):
                contract = self.record("contract", f"CONTRACT-{index}", {"external_contract_no": f"EXT-{index}"})
                case = self.record("case", f"CASE-{index}", {})
                db.add_all([contract, case])
                await db.flush()
                fee = self.record("finance", f"FEE-{index}", {"fee_type": "代理费", "amount": 100,
                    "case_id": case.id, "case_no": case.serial_no, "contract_id": contract.id, "contract_no": contract.serial_no})
                db.add(fee)
                self.contracts.append(contract)
                self.cases.append(case)
                self.fees.append(fee)
            await db.commit()
        self.app = FastAPI()
        self.app.include_router(router)
        async def override_db():
            async with self.sessions() as db:
                yield db
        self.app.dependency_overrides[get_db] = override_db
        self.app.dependency_overrides[current_identity] = lambda: ADMIN

    def record(self, module, suffix, data):
        return BusinessRecord(module=module, serial_no=f"CODEX-CPI-D-{suffix}", title=suffix,
            customer="CODEX-CPI-D-CUSTOMER", status="草稿", owner=ADMIN["username"], department="TEST", data=data)

    def payload(self, **extra):
        return InvoiceApplicationInput(customer=self.customer.customer, invoice_title="TEST", taxpayer_id="TEST",
            **{"amount": 100, "case_fee_ids": [fee.id for fee in self.fees], **extra})

    async def context(self, db, **extra):
        return await invoice_application_context(**{"customer": self.customer.customer, "customer_no": "", "customer_id": None,
            "contract_ids": "", "invoice_id": None, "keyword": "", "page": 1, "page_size": 50,
            "identity": ADMIN, "db": db, **extra})

    async def asyncTearDown(self):
        self.app.dependency_overrides.clear()
        await self.engine.dispose()

    async def test_create_edit_hydrated_detail_and_context(self):
        services = [{"service_name": "A", "quantity": 2, "unit_price": 30}, {"service_name": "B", "quantity": 1, "unit_price": 40}]
        allocations = [{"fee_id": self.fees[0].id, "amount": 30}, {"fee_id": self.fees[1].id, "amount": 70}]
        async with self.sessions() as db:
            result = await create_invoice_application(self.payload(service_items=services, case_fee_allocations=allocations), ADMIN, db)
            self.assertEqual(result["data"]["contract_ids"], [item.id for item in self.contracts])
            result = await update_invoice_application(result["id"], self.payload(remark="edited"), ADMIN, db)
            self.assertEqual(len(result["data"]["service_items"]), 2)
            self.assertEqual([row["amount"] for row in result["data"]["case_fee_allocations"]], [30, 70])
            detail = await get_invoice_application(result["id"], ADMIN, db)
            objects = detail["data"]["invoice_objects"]
            self.assertEqual([row["allocation_amount"] for row in objects], [30, 70])
            self.assertEqual([row["fee_amount"] for row in objects], [100, 100])
            self.assertEqual([row["external_contract_no"] for row in objects], ["EXT-0", "EXT-1"])
            self.assertEqual([row["case_title"] for row in objects], ["CASE-0", "CASE-1"])
            self.assertEqual([row["remaining_invoice_amount"] for row in objects], [70, 30])
            context = await self.context(db, invoice_id=result["id"], page_size=1)
            self.assertEqual(context["total"], 2)
            self.assertEqual(len(context["selected_items"]), 2)
            self.assertEqual(context["items"][0]["data"]["remaining_invoice_amount"], 100)
            self.assertEqual(context["customer_defaults"]["invoice_address"], "CONTACT")
            self.assertEqual(context["customer_defaults"]["taxpayer_id"], "CODEX-TAX")

    async def test_partial_high_allocation_and_repeat_block(self):
        async with self.sessions() as db:
            allocations = [{"fee_id": self.fees[0].id, "amount": 120}, {"fee_id": self.fees[1].id, "amount": 20}]
            result = await create_invoice_application(self.payload(amount=140, case_fee_allocations=allocations), ADMIN, db)
            self.assertEqual(result["data"]["invoice_over_amount"], 20)
            context = await self.context(db)
            self.assertEqual(context["total"], 1)
            self.assertEqual(context["items"][0]["data"]["remaining_invoice_amount"], 80)
            with self.assertRaises(HTTPException) as error:
                await create_invoice_application(self.payload(amount=10, case_fee_ids=[self.fees[0].id]), ADMIN, db)
            self.assertEqual(error.exception.status_code, 409)

    async def test_customer_mismatch_and_locked_edit(self):
        async with self.sessions() as db:
            fee = await db.get(BusinessRecord, self.fees[1].id)
            fee.customer = "OTHER"
            await db.commit()
            with self.assertRaises(HTTPException):
                await create_invoice_application(self.payload(), ADMIN, db)
            await db.rollback()
            self.assertEqual(list((await db.scalars(select(BusinessRecord).where(BusinessRecord.module == "invoice"))).all()), [])
            item = self.record("invoice", "LOCKED", {"amount": 100})
            item.status = "待审批"
            db.add(item)
            await db.commit()
            with self.assertRaises(HTTPException) as error:
                await update_invoice_application(item.id, self.payload(), ADMIN, db)
            self.assertEqual(error.exception.status_code, 409)

    async def test_legacy_missing_services_and_forbidden_source_not_fabricated(self):
        async with self.sessions() as db:
            invoice = self.record("invoice", "LEGACY", {"amount": 100, "case_fee_ids": [999999, 999998]})
            db.add(invoice)
            await db.commit()
            detail = await get_invoice_application(invoice.id, ADMIN, db)
            self.assertEqual(detail["data"]["service_items"], [])
            self.assertTrue(all(row["missing_or_forbidden"] and row["allocation_missing"] for row in detail["data"]["invoice_objects"]))
            self.assertTrue(all(row["amount"] is None for row in detail["data"]["invoice_objects"]))

    async def test_amount_mask_and_http_route(self):
        async with self.sessions() as db:
            item = await create_invoice_application(self.payload(service_items=[{"service_name": "A", "unit_price": 100}]), ADMIN, db)
            with patch("app.core.system._allowed_field_keys", new=AsyncMock(return_value=set())):
                detail = await get_invoice_application(item["id"], ADMIN, db)
            self.assertIsNone(detail["data"]["service_items"][0]["amount"])
            self.assertIsNone(detail["data"]["invoice_objects"][0]["allocation_amount"])
        async with AsyncClient(transport=ASGITransport(app=self.app), base_url="http://test") as client:
            response = await client.get(f"{settings.api_prefix}/finance/invoices/{item['id']}")
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(len(response.json()["data"]["invoice_objects"]), 2)
            response = await client.get(f"{settings.api_prefix}/finance/invoice-context", params={"customer": self.customer.customer, "page_size": 1})
            self.assertEqual(response.status_code, 200, response.text)

    async def test_context_requires_anchor_and_batches_only_customer_sources(self):
        async with self.sessions() as db:
            with self.assertRaises(HTTPException) as error:
                await self.context(db, customer="")
            self.assertEqual(error.exception.status_code, 422)
            other_ids = set()
            for index in range(110):
                fee = self.record("finance", f"BATCH-{index}", dict(self.fees[0].data))
                other = self.record("finance", f"OTHER-{index}", dict(self.fees[0].data))
                other.customer = "OTHER-CUSTOMER"
                db.add_all([fee, other])
                await db.flush()
                other_ids.add(other.id)
            await db.commit()
            with patch("app.core.finance._invoice_fee_details", wraps=_invoice_fee_details) as hydrate:
                result = await self.context(db, page=2, page_size=10)
                self.assertEqual(result["total"], 112)
                self.assertEqual(len(result["items"]), 10)
                self.assertEqual(len(hydrate.call_args_list), 2)
                for call in hydrate.call_args_list:
                    self.assertLessEqual(len(call.kwargs["ids"]), 100)
                    self.assertFalse(call.kwargs["ids"] & other_ids)

    async def test_unknown_amounts_and_hidden_fee_are_not_zero(self):
        async with self.sessions() as db:
            fee = await db.get(BusinessRecord, self.fees[0].id)
            data = dict(fee.data)
            data.pop("amount")
            fee.data = data
            await db.commit()
            rows = await _invoice_fee_details(ADMIN, db, ids={fee.id})
            self.assertIsNone(rows[0]["data"]["amount"])
            self.assertIsNone(rows[0]["data"]["cashed_amount"])
            with patch("app.core.permissions._record_scope_conditions", new=AsyncMock(return_value=[BusinessRecord.module != "finance"])):
                self.assertEqual(await _invoice_fee_details(ADMIN, db, ids={fee.id}), [])

    async def test_receipt_projection_and_ambiguous_case_only_receipt(self):
        async with self.sessions() as db:
            data = dict(self.fees[0].data)
            sibling = self.record("finance", "SIBLING", data)
            db.add(sibling)
            db.add_all([
                IncomingPayment(receipt_no="CODEX-CPI-D-RECEIPT", received_date=date(2026, 9, 14), amount=30,
                    payer_name="CODEX-PAYER", operator=ADMIN["username"], allocations=[{"case_no": self.cases[0].serial_no,
                        "settlement_items": [{"fee_id": self.fees[0].id, "amount": 30}]}]),
                IncomingPayment(receipt_no="CODEX-CPI-D-AMBIGUOUS", received_date=date(2026, 9, 14), amount=70,
                    payer_name="CODEX-PAYER", operator=ADMIN["username"], allocations=[{"case_no": self.cases[0].serial_no, "amount": 70}]),
            ])
            await db.commit()
            rows = await _invoice_fee_details(ADMIN, db, ids={self.fees[0].id})
            self.assertEqual(rows[0]["data"]["cashed_amount"], 30)
            self.assertEqual(rows[0]["data"]["payer"], "CODEX-PAYER")
            self.assertEqual(rows[0]["data"]["received_date"], "2026-09-14")


if __name__ == "__main__":
    unittest.main()
