"""到账列表筛选下推后仍保持可见范围、汇总与顺序。"""

import os
import unittest
from datetime import date
from uuid import uuid4

import httpx
from sqlalchemy import event, text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.areas.finance.incoming_payments import export_incoming_payments, list_incoming_payments
from app.areas.finance.router import finance_ar_summary, finance_summary, list_receivables
from app.config import settings
from app.database import Base, get_db
from app.main import app
from app.models import BusinessRecord, FinanceTransaction, IncomingPayment, ReceivablePlan
from app.security import current_identity


POSTGRES_URL = os.environ.get("INCOMING_QUERY_TEST_POSTGRES_URL", "")


class IncomingQueryAssertions:
    async def asyncSetUp(self):
        if self.database_url:
            if make_url(self.database_url).database != "oa_test_enterprise_commands":
                raise RuntimeError("到账查询测试只能使用专用 PostgreSQL 测试库")
            self.schema = f"oa_test_enterprise_incoming_{uuid4().hex[:12]}"
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
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)

    async def asyncTearDown(self):
        await self.engine.dispose()
        if self.database_url:
            async with self.admin_engine.begin() as connection:
                await connection.execute(text(f"DROP SCHEMA {self.schema} CASCADE"))
            await self.admin_engine.dispose()

    async def test_scope_status_summary_and_unicode_keyword(self):
        async with self.sessions() as db:
            customer = BusinessRecord(
                module="customer", serial_no="ENTERPRISE-INCOMING-CUSTOMER",
                title="可见客户", customer="", status="正常", owner="alice",
                department="上海", data={},
            )
            db.add(customer)
            await db.flush()
            rows = [
                IncomingPayment(receipt_no=f"ENTERPRISE-INCOMING-{index:03d}",
                                received_date=date(2026, 9, 1), amount=1,
                                payer_name="无关付款人", status="待认领", operator="other")
                for index in range(100)
            ]
            rows.extend([
                IncomingPayment(receipt_no="ENTERPRISE-INCOMING-VISIBLE-1",
                                received_date=date(2026, 9, 2), amount=10,
                                payer_name="可见付款人", status="待认领", operator="alice"),
                IncomingPayment(receipt_no="ENTERPRISE-INCOMING-VISIBLE-2",
                                received_date=date(2026, 9, 3), amount=20,
                                payer_name="K付款人", status="待认领", operator="other",
                                claimed_customer="可见客户"),
                IncomingPayment(receipt_no="ENTERPRISE-INCOMING-OTHER-STATUS",
                                received_date=date(2026, 9, 4), amount=30,
                                payer_name="其他状态", status="已分配", operator="alice"),
            ])
            db.add_all(rows)
            await db.commit()
            customer_id = customer.id

        loaded = []
        async with self.sessions() as db:
            def record_load(_session, instance):
                if isinstance(instance, IncomingPayment):
                    loaded.append(instance.receipt_no)

            event.listen(db.sync_session, "loaded_as_persistent", record_load)
            response = await list_incoming_payments(
                payment_status="待认领", keyword="", bank_source="",
                identity={"username": "alice", "role": "user",
                          "_actual_role_ids": [], "_dashboard_record_ids": [customer_id]},
                db=db,
            )
        self.assertEqual([item["receipt_no"] for item in response["items"]], [
            "ENTERPRISE-INCOMING-VISIBLE-2", "ENTERPRISE-INCOMING-VISIBLE-1",
        ])
        self.assertEqual(response["total"], 2)
        self.assertEqual(response["summary"]["amount"], 30)
        self.assertEqual(response["summary"]["unclaimed"], 2)
        self.assertEqual(len(loaded), 2)

        async with self.sessions() as db:
            unicode_response = await list_incoming_payments(
                payment_status="待认领", keyword="k", bank_source="",
                identity={"username": "alice", "role": "user",
                          "_actual_role_ids": [], "_dashboard_record_ids": [customer_id]},
                db=db,
            )
        self.assertEqual([item["receipt_no"] for item in unicode_response["items"]], [
            "ENTERPRISE-INCOMING-VISIBLE-2",
        ])

        loaded = []
        async with self.sessions() as db:
            event.listen(db.sync_session, "loaded_as_persistent", record_load)
            exported = await export_incoming_payments(
                payment_status="待认领", keyword="k",
                identity={"username": "alice", "role": "user",
                          "_actual_role_ids": [], "_dashboard_record_ids": [customer_id]},
                db=db,
            )
        self.assertEqual(len(loaded), 2)
        self.assertIn(b"ENTERPRISE-INCOMING-VISIBLE-2", exported.body)
        self.assertNotIn(b"ENTERPRISE-INCOMING-VISIBLE-1", exported.body)

    async def test_receivables_and_summary_only_load_visible_rows(self):
        async with self.sessions() as db:
            visible = BusinessRecord(
                module="contract", serial_no="ENTERPRISE-CONTRACT-VISIBLE",
                title="可见合同", customer="客户甲", status="正常", owner="alice",
                department="上海", data={},
            )
            db.add(visible)
            await db.flush()
            visible_id = visible.id
            for index in range(100):
                hidden = BusinessRecord(
                    module="contract", serial_no=f"ENTERPRISE-CONTRACT-HIDDEN-{index:03d}",
                    title="其他合同", customer="客户乙", status="正常", owner="other",
                    department="上海", data={},
                )
                db.add(hidden)
                await db.flush()
                db.add(ReceivablePlan(
                    contract_record_id=hidden.id, phase="一期", due_date=date(2026, 9, 1),
                    amount=1, payer="客户乙",
                ))
            db.add(ReceivablePlan(
                contract_record_id=visible_id, phase="一期", due_date=date(2026, 9, 2),
                amount=100, received_amount=40, payer="客户甲",
            ))
            db.add(FinanceTransaction(
                transaction_type="付款", amount=25, transaction_date=date(2026, 9, 1),
                operator="alice",
            ))
            db.add(FinanceTransaction(
                transaction_type="付款", amount=500, transaction_date=date(2026, 9, 1),
                operator="other",
            ))
            await db.commit()

        identity = {"username": "alice", "role": "user",
                    "_actual_role_ids": [], "_dashboard_record_ids": [visible_id]}
        loaded_plans = []
        async with self.sessions() as db:
            def record_load(_session, instance):
                if isinstance(instance, ReceivablePlan):
                    loaded_plans.append(instance.id)

            event.listen(db.sync_session, "loaded_as_persistent", record_load)
            receivables = await list_receivables(
                keyword="", receivable_status="", identity=identity, db=db,
            )
        self.assertEqual(len(loaded_plans), 1)
        self.assertEqual(receivables["total"], 1)
        self.assertEqual(receivables["summary"]["amount"], 100)
        self.assertEqual(receivables["summary"]["remaining"], 60)
        self.assertEqual(receivables["items"][0]["contract_no"], "ENTERPRISE-CONTRACT-VISIBLE")

        loaded_plans = []
        async with self.sessions() as db:
            event.listen(db.sync_session, "loaded_as_persistent", record_load)
            ar_summary = await finance_ar_summary(identity=identity, db=db)
        self.assertEqual(len(loaded_plans), 1)
        self.assertEqual(ar_summary["total"], 1)
        self.assertEqual(ar_summary["summary"]["amount"], 100)

        loaded_transactions = []
        async with self.sessions() as db:
            def transaction_load(_session, instance):
                if isinstance(instance, FinanceTransaction):
                    loaded_transactions.append(instance.id)

            event.listen(db.sync_session, "loaded_as_persistent", transaction_load)
            summary = await finance_summary(identity=identity, db=db)
        self.assertEqual(len(loaded_transactions), 0)
        self.assertEqual(summary["paid_amount"], 25)

    async def test_summary_api_preserves_counts_history_and_scoped_transactions_without_full_entities(self):
        async with self.sessions() as db:
            records = [
                BusinessRecord(module="finance", serial_no=f"SUMMARY-VISIBLE-{index}",
                               title="费用", owner="alice", status=record_status,
                               data=data)
                for index, (record_status, data) in enumerate([
                    ("草稿", {"fee_type": "官方费用", "amount": 100}),
                    ("待审批", {"fee_type": "官方费用", "amount": "0.25"}),
                    ("部分付款", {"fee_type": "代理费", "amount": True}),
                    ("已付款", {"fee_type": "代理费"}),
                    ("历史状态", {"fee_type": "自定义旧费用", "amount": "非法金额"}),
                ])
            ]
            records.extend([
                BusinessRecord(module="finance", serial_no=f"SUMMARY-BATCH-{index}",
                               title="批量费用", owner="alice", status="草稿",
                               data={"fee_type": "官方费用", "amount": "0.5",
                                     "unrelated": "无关数据" * 1000})
                for index in range(450)
            ])
            invoice = BusinessRecord(module="invoice", serial_no="SUMMARY-INVOICE", title="发票",
                                     owner="alice", status="待审批", data={})
            refund = BusinessRecord(module="refund", serial_no="SUMMARY-REFUND", title="退费",
                                    owner="alice", status="待审批", data={})
            hidden = BusinessRecord(module="finance", serial_no="SUMMARY-HIDDEN", title="隐藏费用",
                                    owner="other", status="草稿",
                                    data={"fee_type": "官方费用", "amount": 999})
            db.add_all([*records, invoice, refund, hidden])
            await db.flush()
            visible_ids = [item.id for item in [*records, invoice, refund]]
            for record_id, kind, amount, operator in [
                (records[0].id, "付款", 3, "other"),
                (invoice.id, "开票", 20, "other"),
                (refund.id, "退费", 7, "other"),
                (None, "付款", 4, "alice"),
                (None, "付款", 500, "other"),
                (hidden.id, "付款", 500, "alice"),
            ]:
                db.add(FinanceTransaction(finance_record_id=record_id, transaction_type=kind,
                                          amount=amount, operator=operator,
                                          transaction_date=date(2026, 9, 1)))
            db.add_all([
                IncomingPayment(receipt_no=f"SUMMARY-INCOMING-{index}",
                                received_date=date(2026, 9, 1), amount=10,
                                payer_name="付款人", operator="alice", status=record_status)
                for index, record_status in enumerate(["待认领", "待分配", "部分分配", "历史状态"])
            ])
            db.add(IncomingPayment(receipt_no="SUMMARY-INCOMING-HIDDEN",
                                   received_date=date(2026, 9, 1), amount=10,
                                   payer_name="其他付款人", operator="other", status="待认领"))
            await db.commit()

        identity = {"username": "alice", "role": "user", "_actual_role_ids": [],
                    "_dashboard_record_ids": visible_ids}
        loaded = []
        commits = []
        async with self.sessions() as db:
            def record_load(_session, instance):
                if isinstance(instance, (BusinessRecord, FinanceTransaction, IncomingPayment)):
                    loaded.append(type(instance).__name__)

            event.listen(db.sync_session, "loaded_as_persistent", record_load)
            event.listen(db.sync_session, "before_commit", lambda _session: commits.append(True))

            async def session_dependency():
                yield db

            old_overrides = app.dependency_overrides.copy()
            app.dependency_overrides[get_db] = session_dependency
            app.dependency_overrides[current_identity] = lambda: identity
            try:
                async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),
                                            base_url="http://test") as client:
                    response = await client.get(f"{settings.api_prefix}/finance/summary")
                    self.assertEqual(response.status_code, 200, response.text)
                    again = await client.get(f"{settings.api_prefix}/finance/summary")
                    self.assertEqual(again.json(), response.json())
            finally:
                app.dependency_overrides.clear()
                app.dependency_overrides.update(old_overrides)
        summary = response.json()
        self.assertEqual((summary["fees"], summary["draft"], summary["pending"],
                          summary["approved"], summary["paid"]), (455, 451, 1, 1, 1))
        self.assertEqual((summary["invoice_applications"], summary["invoice_pending"],
                          summary["refund_applications"], summary["refund_pending"]), (1, 1, 1, 1))
        self.assertEqual(summary["total_fee_amount"], 326.25)
        self.assertEqual(summary["amounts_by_type"]["官方费用"], 325.25)
        self.assertEqual(summary["amounts_by_type"]["代理费"], 1)
        self.assertEqual((summary["paid_amount"], summary["invoice_amount"], summary["refund_amount"]),
                         (7, 20, 7))
        self.assertEqual((summary["incoming_payments"], summary["incoming_unclaimed"],
                          summary["incoming_unallocated"]), (4, 1, 2))
        self.assertEqual(loaded, [])
        self.assertEqual(commits, [])

        async with self.sessions() as db:
            administrator = await finance_summary(identity={**identity, "role": "admin"}, db=db)
        self.assertEqual(administrator["fees"], 455)
        self.assertEqual(administrator["paid_amount"], 1007)
        self.assertEqual(administrator["incoming_payments"], 5)

    async def test_summary_invalid_existing_amount_is_an_explicit_failure(self):
        async with self.sessions() as db:
            fee = BusinessRecord(module="finance", serial_no="SUMMARY-BAD-AMOUNT", title="费用",
                                 owner="alice", data={"fee_type": "官方费用", "amount": None})
            db.add(fee)
            await db.commit()
            fee_id = fee.id
        identity = {"username": "alice", "role": "user", "_actual_role_ids": [],
                    "_dashboard_record_ids": [fee_id]}
        async with self.sessions() as db:
            with self.assertRaises(TypeError):
                await finance_summary(identity=identity, db=db)
            fee = await db.get(BusinessRecord, fee_id)
            self.assertIsNone(fee.data["amount"])


class SQLiteIncomingQueryTest(IncomingQueryAssertions, unittest.IsolatedAsyncioTestCase):
    database_url = ""


@unittest.skipUnless(POSTGRES_URL, "设置 INCOMING_QUERY_TEST_POSTGRES_URL 运行独立 PostgreSQL 测试")
class PostgresIncomingQueryTest(IncomingQueryAssertions, unittest.IsolatedAsyncioTestCase):
    database_url = POSTGRES_URL
