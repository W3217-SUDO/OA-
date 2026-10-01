"""有限 ID 的财务查询在数据库筛选，并保持既有结果与顺序。"""

import os
import unittest
from datetime import date, datetime, timezone
from uuid import uuid4

from sqlalchemy import event, text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.finance import _general_settlement_rows, _invoice_list_rows
from app.database import Base
from app.models import BusinessRecord, IncomingPayment, User


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
                tables=[BusinessRecord.__table__, IncomingPayment.__table__, User.__table__],
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
                    received_date=date(2026, 9, 1), amount=1,
                    payer_name="无关付款人", operator="selected-query-admin",
                )
                for index in range(100)
            ]
            payments.extend([
                IncomingPayment(
                    receipt_no=f"ENTERPRISE-SELECTED-RECEIPT-VALID-{index}",
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


@unittest.skipUnless(POSTGRES_URL, "设置 FINANCE_SELECTED_TEST_POSTGRES_URL 运行独立 PostgreSQL 测试")
class PostgresSelectedQueryTest(SelectedQueryAssertions, unittest.IsolatedAsyncioTestCase):
    database_url = POSTGRES_URL
