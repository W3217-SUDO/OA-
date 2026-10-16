"""有限 ID 的财务查询在数据库筛选，并保持既有结果与顺序。"""

import os
import unittest
from datetime import date, datetime, timezone
from uuid import uuid4

import httpx
import xlrd
from fastapi import FastAPI
from sqlalchemy import event, text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.finance import _general_settlement_rows, _invoice_list_rows
from app.areas.finance.settlements import router
from app.database import Base, get_db
from app.models import (
    BusinessRecord, IncomingPayment, LegacyFinanceAllocation,
    LegacyFinanceRecord, SystemParameter, User,
)
from app.security import current_identity


POSTGRES_URL = os.environ.get("FINANCE_SELECTED_TEST_POSTGRES_URL", "")


class SelectedQueryAssertions:
    async def asyncSetUp(self):
        if self.database_url:
            if make_url(self.database_url).database != "oa_test_enterprise_commands":
                raise RuntimeError("有限 ID 财务查询测试只能使用专用 PostgreSQL 测试库")
            self.schema = f"oa_test_enterprise_selected_{uuid4().hex[:12]}"
            self.admin_engine = create_async_engine(self.database_url)
            async with self.admin_engine.begin() as connection:
                await connection.execute(text(f"CREATE SCHEMA {self.schema}"))
            self.engine = create_async_engine(
                self.database_url,
                connect_args={"server_settings": {"search_path": self.schema}},
            )
        else:
            self.engine = create_async_engine(
                "sqlite+aiosqlite:///:memory:",
                connect_args={"check_same_thread": False},
                poolclass=StaticPool,
            )
        async with self.engine.begin() as connection:
            await connection.run_sync(lambda sync_connection: Base.metadata.create_all(
                sync_connection,
                tables=[
                    BusinessRecord.__table__, IncomingPayment.__table__, User.__table__,
                    LegacyFinanceRecord.__table__, LegacyFinanceAllocation.__table__,
                    SystemParameter.__table__,
                ],
            ))
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)

    async def asyncTearDown(self):
        await self.engine.dispose()
        if self.database_url:
            async with self.admin_engine.begin() as connection:
                await connection.execute(text(f"DROP SCHEMA {self.schema} CASCADE"))
            await self.admin_engine.dispose()

    @staticmethod
    def identity():
        username = "selected-query-admin"
        return {
            "username": username,
            "role": "admin",
            "_actual_role_ids": ["admin"],
            "_finance_scope": "firm",
            "_conflict_review_permission": (username, True),
            "_invoice_permissions": {
                "username": username,
                "firm": {"review": True, "issue": True},
                "platform": {"review": True, "issue": True},
            },
        }

    async def test_selected_invoices_keep_order_and_payload(self):
        async with self.sessions() as db:
            db.add_all([
                BusinessRecord(
                    module="invoice", serial_no=f"ENTERPRISE-SELECTED-INVOICE-{index:03d}",
                    title=f"发票 {index}", customer="客户甲", status="已开票",
                    owner="selected-query-admin", data={"invoice_no": str(index)},
                    updated_at=datetime(2026, 9, 1 + index % 20, tzinfo=timezone.utc),
                )
                for index in range(102)
            ])
            await db.commit()
            invoice_ids = list((await db.scalars(
                text("SELECT id FROM business_records WHERE module = 'invoice' ORDER BY id DESC LIMIT 2")
            )).all())
        selected_ids = set(invoice_ids)
        kwargs = dict(
            scope="company", customer="", application_no="", invoice_type="",
            invoice_title="", invoice_no="", invoice_status="",
            invoiced_from=None, invoiced_to=None, case_no="",
        )
        async with self.sessions() as db:
            all_rows = await _invoice_list_rows(self.identity(), db, **kwargs)
        expected = [row for row in all_rows if row["id"] in selected_ids]
        self.assertEqual(len(all_rows), 102)
        self.assertEqual(len(expected), 2)

        loaded = []
        async with self.sessions() as db:
            event.listen(db.sync_session, "loaded_as_persistent", lambda _session, item: (
                loaded.append(item.id) if isinstance(item, BusinessRecord) else None
            ))
            selected = await _invoice_list_rows(self.identity(), db, ids=selected_ids, **kwargs)
        self.assertEqual(selected, expected)
        self.assertEqual(loaded, [row["id"] for row in expected])

    async def test_selected_receipts_keep_order_and_settlement_details(self):
        async with self.sessions() as db:
            case = BusinessRecord(
                module="case", serial_no="ENTERPRISE-SELECTED-CASE", title="测试案件",
                customer="客户甲", status="办理中", owner="selected-query-admin", data={},
            )
            db.add(case)
            await db.flush()
            payments = [
                IncomingPayment(
                    receipt_no=f"ENTERPRISE-SELECTED-RECEIPT-{index:03d}",
                    finance_scope="firm",
                    received_date=date(2026, 9, 1), amount=1,
                    payer_name="无关付款人", operator="selected-query-admin",
                )
                for index in range(100)
            ]
            payments.extend([
                IncomingPayment(
                    receipt_no=f"ENTERPRISE-SELECTED-RECEIPT-VALID-{index}",
                    finance_scope="firm",
                    received_date=date(2026, 9, 2 + index), amount=10 + index,
                    allocated_amount=10 + index, payer_name="相关付款人",
                    claimed_customer="客户甲", operator="selected-query-admin",
                    allocations=[{
                        "case_id": case.id, "case_no": case.serial_no,
                        "amount": 10 + index,
                        "settlement_items": [{
                            "amount": 10 + index, "fee_type": "其他费用",
                            "settlement_amount": 10 + index,
                        }],
                    }],
                )
                for index in range(2)
            ])
            db.add_all(payments)
            await db.commit()
            selected_ids = {payment.id for payment in payments[-2:]}

        async with self.sessions() as db:
            all_rows = await _general_settlement_rows(self.identity(), db)
        expected = [row for row in all_rows if row["id"] in selected_ids]
        self.assertEqual(len(expected), 2)
        self.assertEqual([row["serial_no"] for row in expected], [
            "ENTERPRISE-SELECTED-RECEIPT-VALID-1", "ENTERPRISE-SELECTED-RECEIPT-VALID-0",
        ])

        loaded = []
        async with self.sessions() as db:
            event.listen(db.sync_session, "loaded_as_persistent", lambda _session, item: (
                loaded.append(item.id) if isinstance(item, IncomingPayment) else None
            ))
            selected = await _general_settlement_rows(
                self.identity(), db, receipt_ids=selected_ids,
            )
        self.assertEqual(selected, expected)
        self.assertEqual(set(loaded), selected_ids)
        self.assertEqual(len(loaded), 2)


class SQLiteSelectedQueryTest(SelectedQueryAssertions, unittest.IsolatedAsyncioTestCase):
    database_url = ""

    async def test_settlement_export_ignores_payment_vouchers_but_requires_invoice_amounts(self):
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with self.sessions() as db:
            case = BusinessRecord(module="case", serial_no="CODEX-ROW4-MIXED-CASE",
                                  title="混合凭证导出案件", customer="CODEX-ROW4-CUSTOMER",
                                  status="一审", owner="selected-query-admin", data={})
            db.add(case)
            await db.flush()
            fee = BusinessRecord(module="finance", serial_no="CODEX-ROW4-MIXED-FEE",
                                 title="律师代理费", customer=case.customer, status="已核销",
                                 owner="selected-query-admin", data={"case_id": case.id,
                                     "case_no": case.serial_no, "fee_type": "律师代理费",
                                     "expense_scope": "律所", "amount": 25, "cashed_amount": 25})
            db.add(fee)
            await db.flush()
            payment = IncomingPayment(receipt_no="CODEX-ROW4-MIXED-RECEIPT",
                                      finance_scope="firm",
                                      received_date=date(2026, 10, 12), amount=25, allocated_amount=25,
                                      payer_name="CODEX-ROW4-PAYER", claimed_customer=case.customer,
                                      operator="selected-query-admin", allocations=[{
                                          "case_id": case.id, "case_no": case.serial_no, "amount": 25,
                                          "settlement_items": [{"fee_record_id": fee.id, "amount": 25}],
                                      }])
            invoice_data = {"case_id": case.id, "case_no": case.serial_no, "amount": 20, "extra_amount": 3,
                            "invoice_date": "2026-10-12", "invoice_title": "CODEX-ROW4-REAL-TITLE",
                            "invoice_no": "CODEX-ROW4-REAL-INVOICE", "case_fee_ids": [fee.id],
                            "case_fee_allocations": [{"fee_id": fee.id, "amount": 20}]}
            issued = BusinessRecord(module="invoice", serial_no="CODEX-ROW4-ISSUED",
                                    title="真实已开发票", customer=case.customer, status="已开票",
                                    owner="selected-query-admin", data=invoice_data)
            voucher = BusinessRecord(module="invoice", serial_no="CODEX-ROW4-VOUCHER",
                                     title="历史付款凭证", customer=case.customer, status="已开票",
                                     owner="selected-query-admin", data={"case_id": case.id,
                                         "case_no": case.serial_no, "purpose": "付款凭证", "amount": 25,
                                         "invoice_title": "CODEX-ROW4-VOUCHER-TITLE", "invoice_no": "CODEX-ROW4-VOUCHER-NUMBER"})
            db.add_all([payment, issued, voucher])
            await db.commit()
            payment_id, issued_id, voucher_id = payment.id, issued.id, voucher.id

        async def database():
            async with self.sessions() as db:
                yield db

        application = FastAPI()
        application.include_router(router)
        application.dependency_overrides[get_db] = database
        application.dependency_overrides[current_identity] = self.identity
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=application), base_url="http://row4.test",
            params={"finance_scope": "firm"},
        ) as client:
            for voucher_extra in (None, 99):
                if voucher_extra is not None:
                    async with self.sessions() as db:
                        voucher = await db.get(BusinessRecord, voucher_id)
                        voucher.data = {**voucher.data, "extra_amount": voucher_extra}
                        await db.commit()
                for kind in ("case", "settlement", "receipt"):
                    with self.subTest(kind=kind, voucher_extra=voucher_extra):
                        response = await client.get("/api/v1/finance/general-settlements/export", params={"kind": kind, "ids": payment_id})
                        self.assertEqual(response.status_code, 200, response.text if response.status_code != 200 else "")
                        self.assertTrue(response.content.startswith(bytes.fromhex("d0cf11e0a1b11ae1")))
                        sheet = xlrd.open_workbook(file_contents=response.content).sheet_by_index(0)
                        if kind == "receipt":
                            self.assertEqual(sheet.cell_value(1, 16), "CODEX-ROW4-REAL-TITLE")
                            self.assertEqual(sheet.cell_value(1, 17), "CODEX-ROW4-REAL-INVOICE")
                            self.assertEqual(sheet.cell_value(1, 18), 20)
                            self.assertEqual(sheet.cell_value(1, 19), 3)

            async with self.sessions() as db:
                issued = await db.get(BusinessRecord, issued_id)
                issued.data = {key: value for key, value in invoice_data.items() if key != "extra_amount"}
                await db.commit()
            for kind, name in (("case", "案件明细清单"), ("settlement", "结算列表")):
                response = await client.get("/api/v1/finance/general-settlements/export", params={"kind": kind, "ids": payment_id})
                self.assertEqual(response.status_code, 200, response.text if response.status_code != 200 else "")
                self.assertTrue(response.content.startswith(bytes.fromhex("d0cf11e0a1b11ae1")))
                sheet = xlrd.open_workbook(file_contents=response.content).sheet_by_index(0)
                self.assertEqual(sheet.name, name)
                case_rows = [sheet.row_values(index) for index in range(sheet.nrows)
                             if sheet.cell_value(index, 0) == "CODEX-ROW4-MIXED-CASE"]
                self.assertEqual(len(case_rows), 1)
                self.assertEqual((case_rows[0][3], case_rows[0][5]), (25, 25))
            response = await client.get("/api/v1/finance/general-settlements/export", params={"kind": "receipt", "ids": payment_id})
            self.assertEqual(response.status_code, 409, response.text)
            self.assertEqual(response.json()["detail"], "结算关联发票金额未映射完整")

    async def test_selected_receipt_exports_real_workbooks(self):
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with self.sessions() as db:
            case = BusinessRecord(
                module="case", serial_no="CODEX-ROW4-CASE", title="导出验证案件",
                customer="CODEX-ROW4-CUSTOMER", status="一审", owner="selected-query-admin",
                data={},
            )
            db.add(case)
            await db.flush()
            fees = [BusinessRecord(
                module="finance", serial_no=f"CODEX-ROW4-FEE-{index}", title=fee_type,
                customer=case.customer, status="已核销", owner="selected-query-admin",
                data={"case_id": case.id, "case_no": case.serial_no, "fee_type": fee_type,
                      "expense_scope": "律所", "amount": amount, "cashed_amount": amount},
            ) for index, (fee_type, amount) in enumerate((("律师代理费", 20), ("诉讼费", 5)))]
            db.add_all(fees)
            await db.flush()
            payment = IncomingPayment(
                receipt_no="CODEX-ROW4-RECEIPT", received_date=date(2026, 10, 12),
                finance_scope="firm",
                amount=25, allocated_amount=25, payer_name="CODEX-ROW4-PAYER",
                claimed_customer=case.customer, operator="selected-query-admin",
                allocations=[{"case_id": case.id, "case_no": case.serial_no, "amount": 25,
                              "settlement_items": [{"fee_record_id": fee.id, "amount": amount}
                                                   for fee, amount in zip(fees, (20, 5))]}],
            )
            db.add(payment)
            await db.commit()
            payment_id = payment.id

        async def database():
            async with self.sessions() as db:
                yield db

        application = FastAPI()
        application.include_router(router)
        application.dependency_overrides[get_db] = database
        application.dependency_overrides[current_identity] = self.identity
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=application), base_url="http://row4.test",
            params={"finance_scope": "firm"},
        ) as client:
            for kind, name in (("case", "案件明细清单"), ("settlement", "结算列表")):
                with self.subTest(kind=kind):
                    response = await client.get("/api/v1/finance/general-settlements/export", params={"kind": kind, "ids": payment_id})
                    self.assertEqual(response.status_code, 200, response.text if response.status_code != 200 else "")
                    self.assertTrue(response.content.startswith(bytes.fromhex("d0cf11e0a1b11ae1")))
                    sheet = xlrd.open_workbook(file_contents=response.content).sheet_by_index(0)
                    self.assertEqual(sheet.name, name)
                    case_rows = [sheet.row_values(index) for index in range(sheet.nrows)
                                 if sheet.cell_value(index, 0) == "CODEX-ROW4-CASE"]
                    self.assertEqual(len(case_rows), 2)
                    self.assertEqual([row[5] for row in case_rows], [20, 5])
                    self.assertEqual([row[3] for row in case_rows], [20, 5])
                    self.assertEqual([row[9] for row in case_rows], ["CODEX-ROW4-CUSTOMER"] * 2)

            for ids, expected in (("invalid", 422), (str(payment_id + 10000), 409), (f"{payment_id},{payment_id + 10000}", 409)):
                response = await client.get("/api/v1/finance/general-settlements/export", params={"kind": "case", "ids": ids})
                self.assertEqual(response.status_code, expected, response.text)
                self.assertIsInstance(response.json()["detail"], str)

            async with self.sessions() as db:
                data = (await _general_settlement_rows(self.identity(), db, receipt_ids={payment_id}))[0]["data"]
                settlement = BusinessRecord(
                    module="finance_settlement", serial_no="CODEX-ROW4-APPLICATION",
                    title="导出验证结算申请", customer="CODEX-ROW4-CUSTOMER",
                    status="待审批", owner="selected-query-admin", data=data,
                )
                db.add(settlement)
                await db.commit()
                application_id = settlement.id
            for application_status in ("待审批", "待付款", "部分付款", "已付款", "已拒绝", "已驳回", "已退回"):
                async with self.sessions() as db:
                    settlement = await db.get(BusinessRecord, application_id)
                    settlement.status = application_status
                    await db.commit()
                for kind in ("case", "settlement"):
                    response = await client.get("/api/v1/finance/general-settlements/export", params={
                        "kind": kind, "application_ids": application_id,
                    })
                    self.assertEqual(response.status_code, 200, response.text if response.status_code != 200 else "")
                    sheet = xlrd.open_workbook(file_contents=response.content).sheet_by_index(0)
                    case_rows = [sheet.row_values(index) for index in range(sheet.nrows)
                                 if sheet.cell_value(index, 0) == "CODEX-ROW4-CASE"]
                    self.assertEqual([row[5] for row in case_rows], [20, 5])
                response = await client.get("/api/v1/finance/general-settlements/export", params={"kind": "case", "ids": payment_id})
                self.assertEqual(response.status_code, 200 if application_status in {"已拒绝", "已驳回", "已退回"} else 409)

            for invalid_data, expected in (
                ({**data, "receipt_id": None}, "结算申请缺少原回款关系"),
                ({**data, "allocation_details": [{**data["allocation_details"][0], "fee_id": None}]}, "结算分配明细未关联原案件费用"),
            ):
                async with self.sessions() as db:
                    settlement = await db.get(BusinessRecord, application_id)
                    settlement.data = invalid_data
                    await db.commit()
                response = await client.get("/api/v1/finance/general-settlements/export", params={"kind": "case", "application_ids": application_id})
                self.assertEqual(response.status_code, 409, response.text)
                self.assertIn(expected, response.json()["detail"])

            async with self.sessions() as db:
                db.add(User(username="CODEX-ROW4-OTHER", display_name="隔离其他用户",
                            role="lawyer", department="CODEX-ROW4-OTHER", password_hash="test-only", is_active=True))
                await db.commit()
            application.dependency_overrides[current_identity] = lambda: {
                "username": "CODEX-ROW4-OTHER", "role": "lawyer", "department": "CODEX-ROW4-OTHER",
            }
            for params in ({"ids": payment_id}, {"application_ids": application_id}):
                response = await client.get("/api/v1/finance/general-settlements/export", params={"kind": "case", **params})
                self.assertEqual(response.status_code, 409, response.text)


@unittest.skipUnless(POSTGRES_URL, "设置 FINANCE_SELECTED_TEST_POSTGRES_URL 运行独立 PostgreSQL 测试")
class PostgresSelectedQueryTest(SelectedQueryAssertions, unittest.IsolatedAsyncioTestCase):
    database_url = POSTGRES_URL
