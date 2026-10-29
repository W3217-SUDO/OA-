"""到账列表筛选下推后仍保持可见范围、汇总与顺序。"""

import os
import unittest
from datetime import date
from uuid import uuid4

import httpx
from sqlalchemy import event, func, select, text
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

    async def test_summary_missing_amount_is_reported_without_changing_source(self):
        async with self.sessions() as db:
            fee = BusinessRecord(module="finance", serial_no="SUMMARY-BAD-AMOUNT", title="费用",
                                 owner="alice", data={"fee_type": "官方费用", "amount": None})
            db.add(fee)
            await db.commit()
            fee_id = fee.id
        identity = {"username": "alice", "role": "user", "_actual_role_ids": [],
                    "_dashboard_record_ids": [fee_id]}
        async with self.sessions() as db:
            summary = await finance_summary(identity=identity, db=db)
            self.assertEqual(summary["fees"], 1)
            self.assertEqual(summary["total_fee_amount"], 0)
            self.assertEqual(summary["missing_amount_count"], 1)
            fee = await db.get(BusinessRecord, fee_id)
            self.assertIsNone(fee.data["amount"])


class RawIncomingBundleAssertions:
    async def _seed_raw_bundle_relations(self):
        async with self.sessions() as db:
            customer = BusinessRecord(module="customer", serial_no="BUNDLE-CUSTOMER", title="独立导入客户", owner="admin", data={})
            contract = BusinessRecord(module="contract", serial_no="BUNDLE-CONTRACT", title="独立导入合同", customer=customer.title, owner="admin", data={})
            case = BusinessRecord(module="case", serial_no="BUNDLE-CASE", title="独立导入案件", customer=customer.title, owner="admin", data={})
            db.add_all([customer, contract, case])
            await db.flush()
            db.add(BusinessRecord(module="finance", serial_no="BUNDLE-FEE", title="独立导入费用", owner="admin", customer=customer.title,
                data={"legacy_case_fee_id": 901, "legacy_record": {"_source_database": "fixture-hz", "CaseFeeId": 901, "GroupId": 10},
                      "case_id": case.id, "contract_id": contract.id, "fee_type": "代理费", "amount": 10}))
            await db.commit()

    def _write_raw_bundle(self, directory, *, applied="10.00", method="原始回款方式"):
        import gzip
        import hashlib
        import json
        import xml.etree.ElementTree as ET
        from scripts import import_legacy_finance as importer

        rows = {
            "BAS_Case_FeeType": [{"FeeTypeId": "-200", "TypeId": "2", "FeeTypeName": "代理费", "IsActived": "F"}],
            "FAM_AR_Payment": [{"PaymentId": "902", "GroupId": "10", "CashedAmount": "10.00", "AppliedAmount": applied,
                "CashedDate": "2026-10-16", "PayerName": "独立付款方", "PaymentModeName": method, "SettlementStatus": "25",
                "ContractNo": "BUNDLE-CONTRACT", "CustomerNo": "BUNDLE-CUSTOMER", "IsActived": "T"}],
            "FAM_AR_CaseFee": [{"CaseFeeId": "901", "GroupId": "10", "Amount": "10.00", "CaseFeeStatus": "1",
                "CaseFeeTypeId": "-200",
                "ContractNo": "BUNDLE-CONTRACT", "CustomerNo": "BUNDLE-CUSTOMER", "CaseNo": "BUNDLE-CASE", "IsActived": "T"}],
            "FAM_AR_Payment_Object": [{"SeqId": "903", "PaymentId": "902", "CaseFeeId": "901", "CaseNo": "BUNDLE-CASE",
                "CashedAmount": "10.00", "SettlementAmount": "8.00", "ArchiveAmount": "1.00",
                "ArchiveAmountSettlementStatus": "30", "IsActived": "T"}],
        }
        manifest = {"source_database": "fixture-hz", "tables": []}
        for table in sorted(importer.SUPPORTED_TABLES):
            root = ET.Element("NewDataSet")
            table_rows = rows.get(table, [])
            for values in table_rows:
                element = ET.SubElement(root, table)
                for key, value in values.items():
                    ET.SubElement(element, key).text = value
            compressed = gzip.compress(ET.tostring(root, encoding="utf-8", xml_declaration=True))
            filename = table + ".xml.gz"
            (directory / filename).write_bytes(compressed)
            manifest["tables"].append({"table": table, "file": filename, "rows": len(table_rows),
                "sha256": hashlib.sha256(compressed).hexdigest()})
        (directory / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")

    async def test_raw_bundle_apply_is_idempotent_and_dry_run_leaves_no_raw_rows(self):
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from unittest.mock import patch
        from sqlalchemy import select, func
        from app.models import LegacyFinanceRecord, LegacyFinanceAllocation
        from scripts import import_legacy_finance as importer

        await self._seed_raw_bundle_relations()
        # 只绑定独立库的真实会话；解析、映射、upsert、提交及回滚均走正式实现。
        with TemporaryDirectory(prefix="oa-incoming-bundle-") as temporary, patch.object(importer, "SessionLocal", self.sessions):
            directory = Path(temporary)
            self._write_raw_bundle(directory, method="回" * 100)
            report = await importer.run(directory, apply=False, promote_hz_incoming=True)
            self.assertFalse(report["business_incoming_updated"])
            async with self.sessions() as db:
                self.assertEqual(await db.scalar(select(func.count(LegacyFinanceRecord.id))), 0)
                self.assertEqual(await db.scalar(select(func.count(IncomingPayment.id))), 0)
            report = await importer.run(directory, apply=True, promote_hz_incoming=True)
            self.assertEqual(report["incoming_promotion"]["created"], 1)
            report = await importer.run(directory, apply=True, promote_hz_incoming=True)
            self.assertEqual(report["incoming_promotion"]["unchanged"], 1)
            async with self.sessions() as db:
                self.assertEqual(await db.scalar(select(func.count(LegacyFinanceRecord.id))), 3)
                self.assertEqual(await db.scalar(select(func.count(LegacyFinanceAllocation.id))), 1)
                self.assertEqual(await db.scalar(select(func.count(IncomingPayment.id))), 1)
                self.assertEqual(await db.scalar(select(IncomingPayment.payment_method)), "回" * 100)

    async def test_raw_bundle_promotion_failure_rolls_back_all_raw_rows(self):
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from unittest.mock import patch
        from sqlalchemy import select, func
        from app.models import LegacyFinanceRecord, LegacyFinanceAllocation
        from scripts import import_legacy_finance as importer

        await self._seed_raw_bundle_relations()
        with TemporaryDirectory(prefix="oa-incoming-bundle-") as temporary, patch.object(importer, "SessionLocal", self.sessions):
            directory = Path(temporary)
            self._write_raw_bundle(directory, applied="9.00")
            with self.assertRaisesRegex(ValueError, "明细合计"):
                await importer.run(directory, apply=True, promote_hz_incoming=True)
            async with self.sessions() as db:
                for model in (LegacyFinanceRecord, LegacyFinanceAllocation, IncomingPayment):
                    self.assertEqual(await db.scalar(select(func.count(model.id))), 0)


class SQLiteIncomingQueryTest(RawIncomingBundleAssertions, IncomingQueryAssertions, unittest.IsolatedAsyncioTestCase):
    database_url = ""

    async def test_current_known_zero_is_mathematical_evidence_not_missing_amount_default(self):
        from types import SimpleNamespace
        from app.core.finance import _incoming_payment_dict
        from app.core.finance_centers import incoming_source_statement
        from app.core.incoming_local_amounts import proven_current_zero

        async with self.sessions() as db:
            header, line, _, payment = await self._seed_legacy_settlement_page(db)
            header.source_payload = {**header.source_payload, "AppliedAmount": None}
            payment.allocated_amount, payment.allocations = 0, [{"amount": "0.00"}]
            original_line = dict(line.source_payload)
            await db.commit()
            row = await db.scalar(incoming_source_statement().where(IncomingPayment.id == payment.id)
                                  .execution_options(populate_existing=True))
            result = _incoming_payment_dict(row)
            self.assertEqual([result[key] for key in ("assigned_official_fee", "assigned_agency_fee", "assigned_other_fee")], [0, 0, 0])
            self.assertEqual(result["allocation_status_label"], "金额已证零，费用身份待核")
            self.assertEqual(_incoming_payment_dict(row, show_amount=False)["allocation_status_label"], "费用身份待核")
            self.assertIsNone(payment.local_allocation_summary)
            self.assertEqual(line.source_payload, original_line)
            for allocation in ({}, {"amount": None}, {"amount": 0, "settlement_items": [{"amount": 1}]},
                               {"amount": 0, "settlement_items": [{}]}):
                payment.allocations = [allocation]
                await db.commit()
                row = await db.scalar(incoming_source_statement().where(IncomingPayment.id == payment.id)
                                      .execution_options(populate_existing=True))
                self.assertIsNone(_incoming_payment_dict(row)["assigned_agency_fee"])
            for allocated, allocations in ((None, []), (False, []), (float("nan"), []), (float("inf"), []),
                                            (0, None), (0, [{"amount": float("nan")}]), (0, [{"amount": 0, "settlement_items": "invalid"}])):
                self.assertFalse(proven_current_zero(SimpleNamespace(allocated_amount=allocated, allocations=allocations)))

    async def test_hz_no_detail_requires_proven_numeric_zero_not_missing_amount(self):
        from app.core.finance import _incoming_payment_dict
        from app.core.finance_centers import incoming_source_statement
        from app.core.incoming_legacy_amounts import ASSIGNED_FIELDS

        async with self.sessions() as db:
            header, line, _, payment = await self._seed_legacy_settlement_page(db)
            await db.delete(line)
            payment.allocations, payment.allocated_amount = [], 0
            for value in (0, "0", "0.0", "0.00", None, ""):
                header.source_payload = {**header.source_payload, "AppliedAmount": value}
                payment.allocations = [{"source_object": {}}] if value in (None, "") else []
                await db.commit()
                row = await db.scalar(incoming_source_statement().where(IncomingPayment.id == payment.id)
                                      .execution_options(populate_existing=True))
                expected = (0, 0, 0) if value not in (None, "") else (None, None, None)
                self.assertEqual(tuple(_incoming_payment_dict(row)[field] for field in ASSIGNED_FIELDS), expected)

    async def test_hz_incoming_type_id_controls_rows_totals_and_historical_projection(self):
        from app.core.finance import _incoming_payment_dict
        from app.core.finance_centers import incoming_source_statement
        from app.core.incoming_legacy_amounts import ASSIGNED_FIELDS
        from app.models import LegacyFinanceRecord
        from app.areas.finance.incoming_query import read_incoming_query
        from app.areas.finance.settlements import list_general_settlement_applications

        async with self.sessions() as db:
            header, line, _, payment = await self._seed_legacy_settlement_page(db)
            dictionary = await db.scalar(select(LegacyFinanceRecord).where(
                LegacyFinanceRecord.source_table == "BAS_Case_FeeType"))
            raw_fee = await db.scalar(select(LegacyFinanceRecord).where(
                LegacyFinanceRecord.source_table == "FAM_AR_CaseFee"))
            identity = {"username": "admin", "role": "admin", "_finance_scope": "firm"}
            payment.allocations = [{**payment.allocations[0], "fee_type": "其他费用"}]
            for type_id, expected in ((1, (10, 0, 0)), (2, (0, 10, 0)), (3, (0, 0, 10)),
                                      (4, (0, 0, 0)), (5, (0, 0, 0)), (None, (None, None, None)),
                                      ("garbage", (None, None, None)), (0, (None, None, None))):
                dictionary.source_payload = {**dictionary.source_payload, "TypeId": type_id}
                await db.commit()
                statement = incoming_source_statement().where(IncomingPayment.id == payment.id)
                row = await db.scalar(statement.execution_options(populate_existing=True))
                self.assertEqual(tuple(_incoming_payment_dict(row)[field] for field in ASSIGNED_FIELDS), expected)
                result = await read_incoming_query(statement, "", "", {}, 1, 1, True, {}, db)
                self.assertEqual(tuple(result["totals"][key] for key in ("已分官费", "已分代理费", "已分其他费用")), expected)
                historical = await list_general_settlement_applications(application_status="已付款", page=1, page_size=10, identity=identity, db=db)
                self.assertEqual(tuple(historical["items"][0]["data"][field] for field in ASSIGNED_FIELDS), expected)
            dictionary.source_payload = {**dictionary.source_payload, "TypeId": 2}
            for active, expected in (("F", (0, 0, 0)), (None, (None, None, None)), ("T", (0, 10, 0))):
                raw_fee.is_active = active != "F"
                raw_fee.source_payload = {**raw_fee.source_payload, "IsActived": active}
                await db.commit()
                row = await db.scalar(incoming_source_statement().where(IncomingPayment.id == payment.id)
                                      .execution_options(populate_existing=True))
                self.assertEqual(tuple(_incoming_payment_dict(row)[field] for field in ASSIGNED_FIELDS), expected)
            line.source_payload = {**line.source_payload, "IsActived": None}
            await db.commit()
            row = await db.scalar(incoming_source_statement().where(IncomingPayment.id == payment.id)
                                  .execution_options(populate_existing=True))
            self.assertIsNone(_incoming_payment_dict(row)["assigned_agency_fee"])
            self.assertEqual(row.allocated_amount, 10)
            header.source_payload = {**header.source_payload, "GroupId": 20}
            payment.finance_scope = "platform"
            await db.commit()
            historical = await list_general_settlement_applications(application_status="已付款", page=1, page_size=10, identity=identity, db=db)
            self.assertEqual(historical["total"], 0)

    async def test_existing_hz_uses_verified_original_dictionary_not_label_or_other_source(self):
        from app.core.finance import _incoming_payment_dict
        from app.core.finance_centers import incoming_source_statement
        from app.models import LegacyFinanceRecord, SystemParameter

        async with self.sessions() as db:
            header, line, _, payment = await self._seed_legacy_settlement_page(db)
            raw_fee = await db.scalar(select(LegacyFinanceRecord).where(
                LegacyFinanceRecord.source_table == "FAM_AR_CaseFee"))
            for row, key in ((header, "902"), (raw_fee, "901")):
                row.legacy_id = key
                row.source_payload = {name: value for name, value in row.source_payload.items() if not name.startswith("_")}
            line.legacy_key, line.parent_legacy_id = "903", "902"
            line.source_payload = {name: value for name, value in line.source_payload.items() if not name.startswith("_")}
            payment.allocations = [{**row,
                "source_header": {key: value for key, value in row["source_header"].items() if not key.startswith("_")},
                "source_object": {key: value for key, value in row["source_object"].items() if not key.startswith("_")},
            } for row in payment.allocations]
            parameter = SystemParameter(category="fee_type", code="-200", name="其他费用", is_active=False,
                extra={"source_table": "BAS_Case_FeeType", "migration_source": "hz_crm_20260930",
                       "legacy_record": {"FeeTypeId": -200, "TypeId": 2, "IsActived": "F"}})
            db.add(parameter)
            await db.commit()
            async def amount():
                row = await db.scalar(incoming_source_statement().where(IncomingPayment.id == payment.id)
                                      .execution_options(populate_existing=True))
                return _incoming_payment_dict(row)["assigned_agency_fee"]
            self.assertEqual(await amount(), 10)
            original_rows = payment.allocations
            original = original_rows[0]
            for changed in (
                {**original, "source_object": {**original["source_object"], "_source_database": "another-source"}},
                {**original, "source_object": {**original["source_object"], "IsActived": "F"}},
                {**original, "amount": 9},
                {"amount": 10, "fee_record_id": original["fee_id"]},
            ):
                payment.allocations = [changed]
                await db.commit()
                self.assertIsNone(await amount())
            payment.allocations, payment.allocated_amount = [], 0
            await db.commit()
            self.assertEqual(await amount(), 0)
            payment.allocations, payment.allocated_amount = original_rows, 10
            await db.commit()
            for extra in ({**parameter.extra, "migration_source": "user_pasted_legacy_api_20261016"},
                          {**parameter.extra, "legacy_record": {"FeeTypeId": -201, "TypeId": 2}}):
                original = parameter.extra
                parameter.extra = extra
                await db.commit()
                self.assertIsNone(await amount())
                parameter.extra = original
            line.source_payload = {**line.source_payload, "CaseFeeId": 999}
            await db.commit()
            self.assertIsNone(await amount())

    async def test_hz_local_allocate_partial_and_full_revoke_preserve_original_baseline(self):
        from app.api_schemas.finance import IncomingPaymentAllocateInput, IncomingPaymentRevokeInput
        from app.areas.finance.incoming_payments import allocate_incoming_payment, revoke_incoming_payment_allocations
        from app.core.finance_centers import incoming_source_statement
        from app.core.finance import _incoming_payment_dict
        from app.core.incoming_allocation_records import AllocationCancelInput, allocation_revision, cancel_allocation_records
        from app.models import LegacyFinanceRecord

        async with self.sessions() as db:
            header, line, fee = await self._seed_promotable_receipt(db)
            case = await db.get(BusinessRecord, line.case_record_id)
            case.data = {"contract_id": header.contract_record_id}
            fee.data = {**fee.data, "expense_scope": "律所", "received_amount": 0}
            fee.data = {**fee.data, "legacy_case_fee_id": "fixture-hz:901"}
            payment = IncomingPayment(source_kind="hz_crm_20260930", legacy_finance_record_id=header.id,
                finance_scope="firm", receipt_no="HZ-RCPT-902", received_date=date(2026, 10, 16),
                amount=20, allocated_amount=0, allocations=[], claimed_customer="晋升客户", payer_name="付款方",
                operator="admin", status="待分配")
            db.add(payment)
            await db.commit()
            original_head, original_line = dict(header.source_payload), dict(line.source_payload)
            identity = {"username": "admin", "role": "admin", "_finance_scope": "firm"}
            before = await db.scalar(incoming_source_statement().where(IncomingPayment.id == payment.id))
            self.assertIsNone(before.local_allocation_summary)
            self.assertEqual(_incoming_payment_dict(before)["assigned_agency_fee"], 0)
            for amount in (3, 2):
                result = await allocate_incoming_payment(payment.id, IncomingPaymentAllocateInput(
                    allocations=[{"fee_record_id": fee.id, "amount": amount}]), identity=identity, db=db)
            self.assertEqual(result["allocated_amount"], 5)
            self.assertEqual(result["assigned_agency_fee"], 5)
            self.assertEqual(payment.allocations[0]["base_fee_type_id"], 2)
            self.assertEqual(payment.allocations[0]["case_fee_type_id"], -200)
            result = await cancel_allocation_records(payment.id, AllocationCancelInput(
                revision=allocation_revision(payment.allocations), indexes=[0]), identity, db)
            self.assertEqual(result["payment"]["allocated_amount"], 2)
            self.assertEqual(result["payment"]["assigned_agency_fee"], 2)
            result = await revoke_incoming_payment_allocations(IncomingPaymentRevokeInput(payment_ids=[payment.id]), identity, db)
            self.assertEqual(result["items"][0]["allocated_amount"], 0)
            self.assertEqual(result["items"][0]["assigned_agency_fee"], 0)
            self.assertEqual(header.source_payload, original_head)
            self.assertEqual(line.source_payload, original_line)
            payment.allocations = [{"fee_record_id": fee.id, "amount": 1}]
            await db.commit()
            refreshed = await db.scalar(incoming_source_statement().where(IncomingPayment.id == payment.id)
                                        .execution_options(populate_existing=True))
            self.assertIsNone(_incoming_payment_dict(refreshed)["assigned_agency_fee"])
            self.assertEqual(await db.scalar(select(func.count(LegacyFinanceRecord.id))), 3)

    async def test_hz_local_summary_missing_or_cross_source_evidence_stays_unknown(self):
        from app.core.incoming_local_amounts import current_hz_summary, stamp_hz_allocation_summary
        from app.models import LegacyFinanceRecord, SystemParameter

        async with self.sessions() as db:
            header, _, fee = await self._seed_promotable_receipt(db)
            raw_fee = await db.scalar(select(LegacyFinanceRecord).where(LegacyFinanceRecord.source_table == "FAM_AR_CaseFee"))
            raw_fee.legacy_id = "901"
            raw_fee.source_payload = {key: value for key, value in raw_fee.source_payload.items() if not key.startswith("_")}
            db.add(SystemParameter(category="fee_type", code="-200", name="代理费",
                extra={"source_table": "BAS_Case_FeeType", "migration_source": "hz_crm_20260930",
                       "legacy_record": {"FeeTypeId": -200, "TypeId": 2}}))
            fee.data = {**fee.data, "legacy_record": dict(raw_fee.source_payload), "legacy_source": "other-source"}
            payment = IncomingPayment(source_kind="hz_crm_20260930", legacy_finance_record_id=header.id,
                receipt_no="HZ-RCPT-902", received_date=date(2026, 10, 16), amount=10, allocated_amount=3,
                payer_name="付款方", operator="admin", allocations=[{"fee_record_id": fee.id, "amount": 3}])
            db.add(payment)
            await db.flush()
            await stamp_hz_allocation_summary(payment, db)
            self.assertIsNone(current_hz_summary(payment)["assigned_agency_fee"])
            fee.data = {**fee.data, "legacy_source": "hz_crm_20260930", "source_table": "FAM_AR_CaseFee", "legacy_kind": "ar_case_fee"}
            await db.flush()
            await stamp_hz_allocation_summary(payment, db)
            self.assertEqual(current_hz_summary(payment)["assigned_agency_fee"], 3)
            payment.allocated_amount = 13
            await stamp_hz_allocation_summary(payment, db)
            self.assertIsNone(current_hz_summary(payment)["assigned_agency_fee"])

    async def test_hz_court_refund_writer_stamps_same_classification_contract(self):
        from app.api_schemas.finance import IncomingPaymentAllocateInput
        from app.areas.finance.incoming_payments import allocate_incoming_payment
        from app.models import LegacyFinanceRecord

        async with self.sessions() as db:
            header, line, fee = await self._seed_promotable_receipt(db)
            dictionary = await db.scalar(select(LegacyFinanceRecord).where(LegacyFinanceRecord.source_table == "BAS_Case_FeeType"))
            dictionary.source_payload = {**dictionary.source_payload, "TypeId": 1}
            fee.data = {**fee.data, "fee_type": "官方费用", "expense_scope": "律所", "refund_amount": 5,
                        "case_no": line.legacy_case_no}
            payment = IncomingPayment(source_kind="hz_crm_20260930", legacy_finance_record_id=header.id,
                finance_scope="firm", receipt_no="HZ-RCPT-902", received_date=date(2026, 10, 16), amount=10,
                allocated_amount=0, allocations=[], claimed_customer="晋升客户", payer_name="法院退款",
                operator="admin", status="待分配")
            db.add(payment)
            await db.commit()
            result = await allocate_incoming_payment(payment.id, IncomingPaymentAllocateInput(
                allocations=[{"fee_record_id": fee.id, "amount": 3, "is_refund": True}]),
                identity={"username": "admin", "role": "admin", "_finance_scope": "firm"}, db=db)
            self.assertEqual(result["assigned_official_fee"], 3)
            self.assertEqual(payment.allocations[0]["base_fee_type_id"], 1)
            self.assertIsNotNone(payment.local_allocation_summary)

    async def test_hz_local_modern_fee_uses_real_configuration_id_and_parent_not_label(self):
        from app.core.incoming_local_amounts import current_hz_summary, stamp_hz_allocation_summary
        from app.models import SystemParameter

        async with self.sessions() as db:
            root = SystemParameter(category="fee_type", code="MODERN-ROOT", name="与类别无关的根名",
                extra={"base_fee_type": "代理费"})
            child = SystemParameter(category="fee_type", code="MODERN-CHILD", name="其他费用",
                extra={"parent_code": "MODERN-ROOT"})
            db.add_all([root, child])
            await db.flush()
            fee = BusinessRecord(module="finance", serial_no="MODERN-FEE", title="官费",
                data={"fee_type_id": child.id, "fee_type_code": child.code, "fee_type": "代理费"})
            db.add(fee)
            await db.flush()
            payment = IncomingPayment(source_kind="hz_crm_20260930", receipt_no="HZ-RCPT-LOCAL",
                received_date=date(2026, 10, 16), amount=10, allocated_amount=3, payer_name="付款方", operator="admin",
                allocations=[{"fee_record_id": fee.id, "amount": 3}])
            db.add(payment)
            await db.flush()
            await stamp_hz_allocation_summary(payment, db)
            self.assertEqual(current_hz_summary(payment)["assigned_agency_fee"], 3)
            self.assertEqual(payment.allocations[0]["fee_type_parameter_id"], child.id)
            fee.data = {**fee.data, "fee_type_code": "不存在的配置"}
            await db.flush()
            await stamp_hz_allocation_summary(payment, db)
            self.assertIsNone(current_hz_summary(payment)["assigned_agency_fee"])
            fee.data = {**fee.data, "fee_type_code": child.code, "fee_type": "官方费用"}
            await db.flush()
            await stamp_hz_allocation_summary(payment, db)
            self.assertIsNone(current_hz_summary(payment)["assigned_agency_fee"])
            root.code, root.extra = "AGENCY", {}
            child.extra = {"parent_code": "AGENCY"}
            fee.data = {**fee.data, "fee_type": "代理费"}
            await db.flush()
            await stamp_hz_allocation_summary(payment, db)
            self.assertEqual(current_hz_summary(payment)["assigned_agency_fee"], 3)
            root.code, root.extra = "OTHER", {}
            child.code, child.extra = "1103010", {"parent_code": "OTHER"}
            fee.data = {**fee.data, "fee_type_code": child.code, "fee_type": "其他费用"}
            await db.flush()
            await stamp_hz_allocation_summary(payment, db)
            self.assertEqual(current_hz_summary(payment)["assigned_other_fee"], 0)

    async def test_hz_allocate_to_modern_configured_fee_matches_incoming_and_settlement_amounts(self):
        from app.api_schemas.finance import IncomingPaymentAllocateInput
        from app.areas.finance.incoming_payments import allocate_incoming_payment
        from app.areas.finance.incoming_query import read_incoming_query
        from app.core.finance_centers import incoming_source_statement
        from app.core.finance import _general_settlement_rows
        from app.models import SystemParameter

        async with self.sessions() as db:
            header, line, _ = await self._seed_promotable_receipt(db)
            case = await db.get(BusinessRecord, line.case_record_id)
            case.data = {"contract_id": header.contract_record_id}
            root = SystemParameter(category="fee_type", code="AGENCY", name="代理根", extra={})
            child = SystemParameter(category="fee_type", code="MODERN-NEW", name="与类别不同的名称", extra={"parent_code": "AGENCY"})
            db.add_all([root, child])
            await db.flush()
            fee = BusinessRecord(module="finance", serial_no="MODERN-LOCAL-FEE", title="新系统代理费", customer="晋升客户", owner="admin",
                data={"fee_type_id": child.id, "fee_type_code": child.code, "fee_type": "代理费", "amount": 10,
                      "expense_scope": "律所", "case_id": case.id, "case_no": case.serial_no, "contract_id": header.contract_record_id})
            payment = IncomingPayment(source_kind="hz_crm_20260930", legacy_finance_record_id=header.id,
                finance_scope="firm", receipt_no="HZ-RCPT-902", received_date=date(2026, 10, 16), amount=20,
                allocated_amount=0, allocations=[], claimed_customer="晋升客户", payer_name="付款方", operator="admin", status="待分配")
            db.add_all([fee, payment])
            await db.commit()
            identity = {"username": "admin", "role": "admin", "_finance_scope": "firm"}
            result = await allocate_incoming_payment(payment.id, IncomingPaymentAllocateInput(
                allocations=[{"fee_record_id": fee.id, "amount": 3}]), identity=identity, db=db)
            self.assertEqual(result["assigned_agency_fee"], 3)
            page = await read_incoming_query(incoming_source_statement().where(IncomingPayment.id == payment.id),
                "", "", {}, 1, 10, True, {}, db)
            self.assertEqual(page["totals"]["已分代理费"], 3)
            settlements = await _general_settlement_rows(identity, db, receipt_detail=True)
            self.assertEqual(settlements[0]["data"]["assigned_agency_fee"], 3)
            self.assertEqual(payment.allocations[0]["fee_type_parameter_id"], child.id)

    async def _seed_legacy_settlement_page(self, db):
        from app.models import LegacyFinanceRecord

        header, line, fee = await self._seed_promotable_receipt(db)
        header.source_payload = {**header.source_payload, "UnAppliedAmount": 0, "CaseOfficeFeeAppliedAmount": 0,
            "CaseNonOfficeFeeAppliedAmount": 10, "CaseCommissionFeeAppliedAmount": 0,
            "CaseNonOfficeFeeSettlementAmount": 8, "CaseFeeArchiveAmount": 1}
        raw_fee = await db.scalar(select(LegacyFinanceRecord).where(LegacyFinanceRecord.legacy_id == "fixture-hz:901"))
        raw_fee.source_payload = {**raw_fee.source_payload, "Amount": 10}
        linked_case = await db.get(BusinessRecord, line.case_record_id)
        linked_case.data = {**linked_case.data, "case_phase_id": 106012, "legacy_record": {"CasePhaseId": 106012}}
        payment = IncomingPayment(source_kind="hz_crm_20260930", receipt_no="HZ-RCPT-902",
            legacy_finance_record_id=header.id, finance_scope="firm", received_date=date(2026, 10, 16),
            amount=10, allocated_amount=10, payer_name="晋升付款方", operator="admin", status="已分配",
            allocations=[{"amount": 10, "fee_id": fee.id, "case_id": line.case_record_id,
                "source_header": dict(header.source_payload), "source_object": dict(line.source_payload)}])
        db.add(payment)
        await db.commit()
        return header, line, linked_case, payment

    async def test_imported_normal_states_are_read_only_scoped_and_exportable(self):
        from sqlalchemy import select
        from app.areas.finance.settlements import list_general_settlement_applications, export_general_settlements

        async with self.sessions() as db:
            header, line, _, payment = await self._seed_legacy_settlement_page(db)
            identity = {"username": "admin", "role": "admin", "_finance_scope": "firm"}
            for code, status in ((10, "待审批"), (20, "待付款"), (25, "已付款"), (30, "已拒绝")):
                header.source_payload = {**header.source_payload, "SettlementStatus": code}
                await db.commit()
                result = await list_general_settlement_applications(application_status=status, identity=identity, db=db, page=1, page_size=1)
                self.assertEqual(result["total"], 1)
                row = result["items"][0]
                self.assertEqual(row["id"], f"legacy-normal:{header.id}")
                self.assertTrue(row["read_only"])
                self.assertEqual(row["serial_no"], "")
                self.assertEqual(row["source_status"], str(code))
                self.assertEqual(row["amount_basis"], "legacy_snapshot")
                self.assertFalse(row["has_local_allocation_activity"])
                self.assertNotIn("bank_source", row["data"])
                self.assertEqual(row["data"]["payment_method"], "原方式")
                self.assertEqual(result["totals"]["assigned_agency_fee"], 10)
                self.assertIsNone(result["totals"]["actual_settlement_amount"])
                self.assertEqual(row["data"]["allocation_details"][0]["line_id"], line.id)
            response = await export_general_settlements(kind="case", projection_ids=f"legacy-normal:{header.id}",
                identity=identity, db=db, ids="", application_ids="")
            self.assertEqual(response.status_code, 200)
            from app.areas.finance.export_projection import enrich_settlement_exports
            import xlrd
            payment.payment_method = "现行单独修改方式"
            await db.commit()
            await enrich_settlement_exports([row], identity, db, include_invoice_fields=False)
            self.assertEqual(row["data"]["payment_method"], "原方式")
            response = await export_general_settlements(kind="receipt", projection_ids=f"legacy-normal:{header.id}",
                identity=identity, db=db, ids="", application_ids="")
            workbook = xlrd.open_workbook(file_contents=response.body)
            self.assertEqual(workbook.sheet_by_name("来源说明").cell_value(1, 1), "legacy_snapshot")
            values = [str(value) for sheet in workbook.sheets() for index in range(sheet.nrows) for value in sheet.row_values(index)]
            self.assertIn("原方式", values)
            self.assertNotIn("现行单独修改方式", values)
            second_page = await list_general_settlement_applications(application_status="已拒绝", case_no="PROMOTE-CASE",
                identity=identity, db=db, page=2, page_size=1)
            self.assertEqual(second_page["total"], 1)
            self.assertEqual(second_page["items"], [])
            self.assertEqual(second_page["totals"]["assigned_agency_fee"], 10)
            from app.core.incoming_local_amounts import stamp_hz_allocation_summary
            payment.allocations, payment.allocated_amount = [], 0
            await stamp_hz_allocation_summary(payment, db)
            await db.commit()
            current = await list_general_settlement_applications(application_status="已拒绝", identity=identity, db=db, page=1, page_size=10)
            self.assertEqual(current["items"][0]["data"]["assigned_agency_fee"], 10)
            self.assertEqual(current["items"][0]["data"]["amount_basis"], "legacy_snapshot")
            self.assertTrue(current["items"][0]["has_local_allocation_activity"])
            self.assertFalse(current["items"][0]["can_pay"])
            other = await list_general_settlement_applications(application_status="已拒绝", identity={**identity, "_finance_scope": "platform"}, db=db, page=1, page_size=10)
            self.assertEqual(other["total"], 0)
            from app.models import User
            db.add(User(username="outsider", display_name="独立无权用户", password_hash="not-used-in-unit-test", role="user", department="独立部门"))
            await db.commit()
            outsider = await list_general_settlement_applications(application_status="已拒绝", identity={"username": "outsider", "role": "user", "_finance_scope": "firm"}, db=db, page=1, page_size=10)
            self.assertEqual(outsider["total"], 0)
            self.assertEqual(await db.scalar(select(func.count(BusinessRecord.id)).where(BusinessRecord.module == "finance_settlement")), 0)

    async def test_legacy_projection_ids_cannot_enter_modern_review_or_payment_writers(self):
        from pydantic import ValidationError
        from fastapi import HTTPException
        from app.models_shared import FinanceSettlementReviewInput, ArchiveSettlementPaymentReviewInput
        from app.areas.finance.settlements import review_archive_settlement_payments

        async with self.sessions() as db:
            header, line, _, _ = await self._seed_legacy_settlement_page(db)
            with self.assertRaises(ValidationError):
                FinanceSettlementReviewInput(application_ids=[f"legacy-normal:{header.id}"], approved=True)
            with self.assertRaises(HTTPException) as rejected:
                await review_archive_settlement_payments(ArchiveSettlementPaymentReviewInput(
                    settlement_ids=[f"legacy-archive:{line.id}"], approved=True),
                    identity={"username": "admin", "role": "admin", "_finance_scope": "firm"}, db=db)
            self.assertEqual(rejected.exception.status_code, 409)
            self.assertEqual(await db.scalar(select(func.count(BusinessRecord.id)).where(
                BusinessRecord.module.in_(("finance_settlement", "finance_archive_settlement")))), 0)

    async def test_historical_normal_settlement_is_adopted_reviewed_paid_and_rolled_back(self):
        """BUG20261028009：历史只读结算可审核、支付、回滚，办理时按原快照转成现代申请，同一回款只承接一次。"""
        from fastapi import HTTPException
        from app.models import WorkflowEvent
        from app.models_shared import (
            FinanceSettlementPaymentInput, FinanceSettlementReviewInput, FinanceSettlementWithdrawInput,
        )
        from app.areas.finance.settlements import (
            list_general_settlement_applications, pay_or_rollback_general_settlement_applications,
            review_general_settlement_applications, withdraw_general_settlement_applications,
        )

        async with self.sessions() as db:
            header, line, _, payment = await self._seed_legacy_settlement_page(db)
            identity = {"username": "admin", "role": "admin", "_finance_scope": "firm"}
            header.source_payload = {**header.source_payload, "SettlementStatus": 10}
            await db.commit()
            projection_id = f"legacy-normal:{header.id}"
            reviewed = await review_general_settlement_applications(FinanceSettlementReviewInput(
                projection_ids=[projection_id], approved=True, comment="同意"), identity=identity, db=db)
            self.assertEqual(reviewed["status"], "待付款")
            application_id = reviewed["application_ids"][0]
            record = await db.get(BusinessRecord, application_id)
            self.assertEqual(record.data["legacy_projection_id"], projection_id)
            self.assertEqual(record.data["legacy_source_status"], "10")
            self.assertEqual(record.data["receipt_id"], payment.id)
            self.assertEqual(record.data["allocation_details"][0]["line_id"], line.id)
            self.assertEqual((await list_general_settlement_applications(
                application_status="待审批", identity=identity, db=db, page=1, page_size=10))["total"], 0)
            pending_payment = await list_general_settlement_applications(
                application_status="待付款", identity=identity, db=db, page=1, page_size=10)
            self.assertEqual([item["id"] for item in pending_payment["items"]], [application_id])
            with self.assertRaises(HTTPException) as repeated:
                await review_general_settlement_applications(FinanceSettlementReviewInput(
                    projection_ids=[projection_id], approved=True), identity=identity, db=db)
            self.assertEqual(repeated.exception.status_code, 409)
            await db.rollback()
            paid = await pay_or_rollback_general_settlement_applications(FinanceSettlementPaymentInput(
                application_ids=[application_id], action="paid"), identity=identity, db=db)
            self.assertEqual(paid["status"], "已付款")
            record = await db.get(BusinessRecord, application_id)
            details = record.data["allocation_details"]
            if details[0].get("source_status") != "30":
                record.data = {**record.data, "allocation_details": [{**details[0], "source_status": "30"}, *details[1:]]}
                await db.commit()
            with self.assertRaises(HTTPException) as archive_paid:  # 原系统归档费已支付，先回滚归档费
                await withdraw_general_settlement_applications(FinanceSettlementWithdrawInput(
                    application_ids=[application_id], comment="分配有误"), identity=identity, db=db)
            self.assertEqual(archive_paid.exception.status_code, 409)
            await db.rollback()
            record = await db.get(BusinessRecord, application_id)
            record.data = {**record.data, "allocation_details": [
                {**detail, "source_status": "20"} for detail in record.data["allocation_details"]]}
            await db.commit()
            withdrawn = await withdraw_general_settlement_applications(FinanceSettlementWithdrawInput(
                application_ids=[application_id], comment="分配有误"), identity=identity, db=db)
            self.assertEqual(withdrawn["status"], "已撤回")
            for status in ("待审批", "待付款", "已付款", "已拒绝"):
                self.assertEqual((await list_general_settlement_applications(
                    application_status=status, identity=identity, db=db, page=1, page_size=10))["total"], 0)
            actions = (await db.scalars(select(WorkflowEvent.action).where(
                WorkflowEvent.record_id == application_id).order_by(WorkflowEvent.id))).all()
            self.assertEqual(actions, ["承接历史结算", "同意结算", "标记已支付", "回滚结算"])

    async def test_historical_settlement_rollback_requires_comment_and_role(self):
        from pydantic import ValidationError
        from fastapi import HTTPException
        from app.models_shared import FinanceSettlementWithdrawInput
        from app.areas.finance.settlements import withdraw_general_settlement_applications

        with self.assertRaises(ValidationError):
            FinanceSettlementWithdrawInput(projection_ids=["legacy-normal:1"], comment="")
        with self.assertRaises(ValidationError):
            FinanceSettlementWithdrawInput(comment="无目标")
        async with self.sessions() as db:
            with self.assertRaises(HTTPException) as denied:
                await withdraw_general_settlement_applications(FinanceSettlementWithdrawInput(
                    projection_ids=["legacy-normal:1"], comment="回滚"),
                    identity={"username": "u", "role": "user", "_finance_scope": "firm"}, db=db)
            self.assertEqual(denied.exception.status_code, 403)

    async def test_historical_archive_fee_is_rolled_back_reviewed_and_hidden_once_decided(self):
        """BUG20261028010：历史归档费可回滚、审核，办理后由决定记录接管，历史明细不重复显示。"""
        from app.models_shared import ArchiveSettlementPaymentReviewInput, ArchiveSettlementRollbackInput
        from app.areas.finance.settlements import (
            list_archive_settlement_payments, list_paid_archive_settlements,
            review_archive_settlement_payments, rollback_paid_archive_settlements,
        )
        from app.core.imported_settlement_projection import read_imported_settlement_page

        async with self.sessions() as db:
            header, line, _, _ = await self._seed_legacy_settlement_page(db)
            identity = {"username": "admin", "role": "admin", "_finance_scope": "firm"}
            header.source_payload = {**header.source_payload, "SettlementStatus": 25}
            line.source_payload = {**line.source_payload, "ArchiveAmountSettlementStatus": 30}
            await db.commit()
            key = f"legacy-archive:{line.id}"
            paid = await read_imported_settlement_page([], identity, db, mode="paid")
            self.assertEqual([row["id"] for row in paid["items"]], [key])
            rolled = await rollback_paid_archive_settlements(ArchiveSettlementRollbackInput(
                projection_ids=[key], comment="金额有误"), identity=identity, db=db)
            self.assertEqual(rolled["status"], "已回滚")
            self.assertEqual((await read_imported_settlement_page([], identity, db, mode="paid"))["total"], 0)
            payment = await read_imported_settlement_page([], identity, db, mode="payment")
            self.assertEqual([row["id"] for row in payment["items"]], [key])
            reviewed = await review_archive_settlement_payments(ArchiveSettlementPaymentReviewInput(
                settlement_ids=[key], approved=True), identity=identity, db=db)
            self.assertEqual(reviewed["status"], "已支付")
            self.assertEqual((await read_imported_settlement_page([], identity, db, mode="payment"))["total"], 0)
            listed = await list_paid_archive_settlements(identity=identity, db=db, page=1, page_size=10)
            self.assertEqual([row["id"] for row in listed["items"]], reviewed["record_ids"])
            self.assertEqual(listed["items"][0]["data"]["source_row_id"], key)
            self.assertEqual(await db.scalar(select(func.count(BusinessRecord.id)).where(
                BusinessRecord.module == "finance_archive_settlement")), 1)
            with self.assertRaises(Exception):
                await rollback_paid_archive_settlements(ArchiveSettlementRollbackInput(
                    projection_ids=[key], comment="重复"), identity=identity, db=db)
            await db.rollback()
            self.assertEqual((await list_archive_settlement_payments(identity=identity, db=db, page=1, page_size=10))["total"], 0)

    async def test_imported_archive_rules_use_raw_phase_and_keep_unknown_out_of_payment(self):
        from app.core.imported_settlement_projection import read_imported_settlement_page

        async with self.sessions() as db:
            header, line, case, _ = await self._seed_legacy_settlement_page(db)
            identity = {"username": "admin", "role": "admin", "_finance_scope": "firm"}
            line.source_payload = {**line.source_payload, "ArchiveAmountSettlementStatus": 20}
            await db.commit()
            result = await read_imported_settlement_page([], identity, db, mode="payment")
            self.assertEqual(result["total"], 1)
            self.assertEqual(result["totals"]["archive_fee_amount"], 1)
            for state in (50, None):
                line.source_payload = {**line.source_payload, "ArchiveAmountSettlementStatus": state}
                await db.commit()
                self.assertEqual((await read_imported_settlement_page([], identity, db, mode="payment"))["total"], 0)
            case.data = {"legacy_record": {"CasePhaseId": 101011}}
            for state in (30, 40, 50, None):
                line.source_payload = {**line.source_payload, "ArchiveAmountSettlementStatus": state}
                await db.commit()
                result = await read_imported_settlement_page([], identity, db, mode="pending")
                self.assertEqual(result["total"], 0 if state is None else 1)
                self.assertEqual(result["unknown_eligibility_total"], 1 if state is None else 0)
                if state is not None:
                    self.assertEqual(result["items"][0]["source_status"], str(state))
                    self.assertTrue(result["items"][0]["read_only"])
                    self.assertFalse(result["items"][0]["can_pay"])
            line.source_payload = {**line.source_payload, "ArchiveAmountSettlementStatus": 10, "ArchiveAmount": 0}
            await db.commit()
            self.assertEqual((await read_imported_settlement_page([], identity, db, mode="pending"))["total"], 0)
            line.source_payload = {**line.source_payload, "ArchiveAmount": 1}
            for state, mode in ((30, "paid"), (40, "rejected")):
                header.source_payload = {**header.source_payload, "SettlementStatus": 10}
                line.source_payload = {**line.source_payload, "ArchiveAmountSettlementStatus": state}
                case.data = {"case_phase_id": 101011, "legacy_record": {"CasePhaseId": 101011}}
                await db.commit()
                self.assertEqual((await read_imported_settlement_page([], identity, db, mode=mode))["total"], 1)
            header.source_payload = {**header.source_payload, "SettlementStatus": 20}
            line.source_payload = {**line.source_payload, "ArchiveAmountSettlementStatus": 10}
            await db.commit()
            self.assertEqual((await read_imported_settlement_page([], identity, db, mode="pending"))["total"], 1)
            case.data = {}
            await db.commit()
            result = await read_imported_settlement_page([], identity, db, mode="pending")
            self.assertEqual(result["total"], 0)
            self.assertEqual(result["unknown_phase_total"], 1)
            header.source_payload = {**header.source_payload, "SettlementStatus": 25}
            line.source_payload = {**line.source_payload, "ArchiveAmountSettlementStatus": 20}
            case.data = {"case_phase_id": 106012, "legacy_record": {"CasePhaseId": 106012, "AuditedTime": "2026-10-12T09:00:00"},
                         "archived_at": "2000-01-01"}
            await db.commit()
            filters = {"archive_from": date(2026, 10, 1), "archive_to": date(2026, 10, 31)}
            result = await read_imported_settlement_page([], identity, db, mode="payment", filters=filters)
            self.assertEqual(result["total"], 1)
            self.assertEqual(result["items"][0]["data"]["archive_date"], "2026-10-12T09:00:00")
            case.data = {"case_phase_id": 106012, "legacy_record": {"CasePhaseId": 106012}, "archived_at": "2026-10-12"}
            await db.commit()
            result = await read_imported_settlement_page([], identity, db, mode="payment", filters=filters)
            self.assertEqual(result["total"], 0)
            self.assertEqual(result["unknown_date_total"], 1)

    async def test_imported_normal_amount_origins_follow_verified_hz_head_and_detail_contract(self):
        from app.core.imported_settlement_projection import read_imported_settlement_page

        async with self.sessions() as db:
            header, _, _, _ = await self._seed_legacy_settlement_page(db)
            header.source_payload = {**header.source_payload, "AppliedAmount": 12.5, "UnAppliedAmount": 0,
                "CaseOfficeFeeAppliedAmount": 2, "CaseNonOfficeFeeAppliedAmount": 8.5,
                "CaseCommissionFeeAppliedAmount": 2, "CaseNonOfficeFeeSettlementAmount": 6.25,
                "CaseFeeArchiveAmount": 3, "CaseFeeSettlementAmount": 9.25, "SettlementAmount": 999}
            await db.commit()
            result = await read_imported_settlement_page([], {"username": "admin", "role": "admin", "_finance_scope": "firm"},
                db, mode="normal", statuses={"已付款"})
            data = result["items"][0]["data"]
            for key, amount in (("allocated_amount", 12.5), ("remaining_amount", 0), ("assigned_official_fee", 0),
                ("assigned_agency_fee", 10), ("assigned_other_fee", 0), ("agency_settlement_amount", 6.25),
                ("archive_fee", 3), ("actual_settlement_amount", 9.25)):
                self.assertEqual(data[key], amount)
                self.assertEqual(result["totals"][key], amount)
            self.assertEqual(data["allocation_details"][0]["current_amount"], 10)
            self.assertEqual(data["allocation_details"][0]["archive_fee"], 1)
            header.source_payload = {key: value for key, value in header.source_payload.items() if key != "CashedAmount"}
            await db.commit()
            result = await read_imported_settlement_page([], {"username": "admin", "role": "admin", "_finance_scope": "firm"},
                db, mode="normal", statuses={"已付款"})
            self.assertIsNone(result["items"][0]["data"]["remaining_amount"])
            self.assertIsNone(result["totals"]["remaining_amount"])
            self.assertEqual(result["unknown_amount_counts"]["remaining_amount"], 1)

    async def test_imported_archive_exports_and_normal_modern_precedence(self):
        from app.areas.finance.settlements import (
            export_pending_archive_settlements, export_archive_settlement_payments,
            export_paid_archive_settlements, export_rejected_archive_settlements,
            list_general_settlement_applications, export_general_settlements,
        )
        from fastapi import HTTPException
        from starlette.requests import Request
        import xlrd

        async with self.sessions() as db:
            header, line, linked_case, payment = await self._seed_legacy_settlement_page(db)
            identity = {"username": "admin", "role": "admin", "_finance_scope": "firm"}
            for code, phase, exporter in ((10, 101011, export_pending_archive_settlements),
                (20, 106012, export_archive_settlement_payments), (30, None, export_paid_archive_settlements),
                (40, None, export_rejected_archive_settlements)):
                line.source_payload = {**line.source_payload, "ArchiveAmountSettlementStatus": code}
                linked_case.data = {"legacy_record": {"CasePhaseId": phase}} if phase else {}
                await db.commit()
                result = await exporter(projection_ids=f"legacy-archive:{line.id}", identity=identity, db=db, ids="")
                self.assertEqual(result.status_code, 200)
                self.assertGreater(len(result.body), 100)
                if result.body.startswith(b"<?xml"):
                    from xml.etree.ElementTree import fromstring
                    ns = {"s": "urn:schemas-microsoft-com:office:spreadsheet"}
                    source_sheet = fromstring(result.body).find("s:Worksheet[@s:Name='来源说明']", ns)
                    self.assertIn("legacy_snapshot", [item.text for item in source_sheet.findall(".//s:Data", ns)])
                else:
                    source_sheet = xlrd.open_workbook(file_contents=result.body).sheet_by_name("来源说明")
                    self.assertEqual(source_sheet.cell_value(1, 1), "legacy_snapshot")
                with self.assertRaises(HTTPException) as denied:
                    await exporter(projection_ids=f"legacy-archive:{line.id}", identity={**identity, "_finance_scope": "platform"}, db=db, ids="")
                self.assertEqual(denied.exception.status_code, 409)
            request = Request({"type": "http", "query_string": b"status=%E5%B7%B2%E4%BB%98%E6%AC%BE"})
            exported = await export_general_settlements(kind="case", request=request, identity=identity, db=db,
                ids="", application_ids="", projection_ids="")
            workbook = xlrd.open_workbook(file_contents=exported.body)
            self.assertTrue(any("PROMOTE-CASE" in str(value) for sheet in workbook.sheets() for row in range(sheet.nrows) for value in sheet.row_values(row)))
            modern = BusinessRecord(module="finance_settlement", serial_no="MODERN-PRIORITY", title="真实新结算",
                customer="晋升客户", owner="admin", status="已付款", data={"receipt_id": payment.id,
                    "finance_scope": "firm", "receipt_amount": 10, "received_date": "2026-10-16"})
            db.add(modern)
            await db.commit()
            page = await list_general_settlement_applications(application_status="已付款", identity=identity, db=db, page=1, page_size=10)
            self.assertEqual(page["total"], 1)
            self.assertEqual(page["items"][0]["id"], modern.id)
            self.assertNotEqual(page["items"][0].get("source"), "legacy")

    async def _seed_promotable_receipt(self, db, *, group=10):
        from app.models import LegacyFinanceRecord, LegacyFinanceAllocation

        customer = BusinessRecord(module="customer", serial_no="PROMOTE-CUSTOMER", title="晋升客户", owner="admin", data={})
        contract = BusinessRecord(module="contract", serial_no="PROMOTE-CONTRACT", title="晋升合同", customer="晋升客户", owner="admin", data={})
        case = BusinessRecord(module="case", serial_no="PROMOTE-CASE", title="晋升案件", customer="晋升客户", owner="admin", data={})
        db.add_all([customer, contract, case])
        await db.flush()
        raw_fee = LegacyFinanceRecord(source_table="FAM_AR_CaseFee", legacy_id="fixture-hz:901",
            record_kind="case_fee", primary_amount=10, legacy_case_no=case.serial_no,
            legacy_contract_no=contract.serial_no, legacy_customer_no=customer.serial_no,
            case_record_id=case.id, contract_record_id=contract.id, customer_record_id=customer.id,
            source_payload={"_source_database": "fixture-hz", "_legacy_id": "fixture-hz:901", "CaseFeeId": 901,
                "GroupId": group, "CaseFeeTypeId": -200, "IsActived": "T"})
        dictionary = LegacyFinanceRecord(source_table="BAS_Case_FeeType", legacy_id="fixture-hz:-200",
            record_kind="case_fee_type", source_payload={"_source_database": "fixture-hz", "_legacy_id": "fixture-hz:-200",
                "FeeTypeId": -200, "TypeId": 2, "FeeTypeName": "同名费用", "IsActived": "F"}, is_active=False)
        fee = BusinessRecord(module="finance", serial_no="PROMOTE-FEE", title="晋升代理费", customer=customer.title, owner="admin",
            data={"legacy_case_fee_id": 901, "legacy_record": dict(raw_fee.source_payload),
                  "case_id": case.id, "contract_id": contract.id, "amount": 10, "fee_type": "代理费"})
        header = LegacyFinanceRecord(source_table="FAM_AR_Payment", legacy_id="fixture-hz:902",
            record_kind="ar_payment", primary_amount=10, legacy_contract_no=contract.serial_no,
            legacy_customer_no=customer.serial_no, contract_record_id=contract.id, customer_record_id=customer.id,
            source_payload={"_source_database": "fixture-hz", "_legacy_id": "fixture-hz:902", "PaymentId": 902, "GroupId": group,
                "CashedAmount": 10, "AppliedAmount": 10, "CashedDate": "2026-10-16", "PayerName": "晋升付款方",
                "PaymentModeName": "原方式", "SettlementStatus": 25, "IsActived": "T"})
        db.add_all([raw_fee, fee, header, dictionary])
        await db.flush()
        line = LegacyFinanceAllocation(source_table="FAM_AR_Payment_Object", legacy_key="fixture-hz:903",
            allocation_kind="ar_payment", legacy_finance_record_id=header.id,
            parent_source_table="FAM_AR_Payment", parent_legacy_id=header.legacy_id,
            legacy_case_fee_id="901", legacy_case_no=case.serial_no, case_record_id=case.id,
            amount=10, settlement_amount=8, archive_amount=1,
            source_payload={"_source_database": "fixture-hz", "_legacy_id": "fixture-hz:903", "SeqId": 903, "PaymentId": 902,
                "CaseFeeId": 901, "CashedAmount": 10, "SettlementAmount": 8, "ArchiveAmount": 1,
                "ArchiveAmountSettlementStatus": 30, "IsActived": "T"})
        db.add(line)
        await db.commit()
        return header, line, fee

    async def test_promoter_dry_run_create_idempotency_and_original_values(self):
        from app.core.imported_incoming_payments import promote_imported_incoming_payments
        from app.core.finance import _incoming_payment_legacy_summary, _general_settlement_rows
        from app.core.finance_centers import incoming_source_statement, require_source_center
        from sqlalchemy import select, func

        async with self.sessions() as db:
            header, line, fee = await self._seed_promotable_receipt(db)
            report = await promote_imported_incoming_payments(db, source_database="fixture-hz", write=False)
            self.assertEqual(report["created"], 1)
            self.assertEqual(await db.scalar(select(func.count(IncomingPayment.id))), 0)
            report = await promote_imported_incoming_payments(db, source_database="fixture-hz")
            await db.commit()
            self.assertEqual(report["created"], 1)
            payment = await db.scalar(incoming_source_statement().where(IncomingPayment.legacy_finance_record_id == header.id))
            self.assertEqual(payment.finance_scope, "firm")
            self.assertEqual(payment.payment_method, "原方式")
            self.assertEqual(payment.allocations[0]["source_object"]["ArchiveAmountSettlementStatus"], 30)
            self.assertEqual(payment.allocations[0]["source_header"]["SettlementStatus"], 25)
            self.assertNotIn("settlement_items", payment.allocations[0])
            self.assertEqual(_incoming_payment_legacy_summary(payment)["assigned_agency_fee"], 10)
            self.assertEqual(await require_source_center(fee, db), "firm")
            self.assertEqual(await _general_settlement_rows({"username": "admin", "role": "admin", "_finance_scope": "firm"}, db), [])
            payment.remark = "新系统本地备注"
            await db.commit()
            report = await promote_imported_incoming_payments(db, source_database="fixture-hz")
            self.assertEqual(report["unchanged"], 1)
            self.assertEqual(payment.remark, "新系统本地备注")
            self.assertEqual(header.primary_amount, 10)
            self.assertEqual(line.settlement_amount, 8)
            self.assertEqual(line.archive_amount, 1)

    async def test_promoter_source_update_conflict_rolls_back_without_overwriting_local_state(self):
        from app.core.imported_incoming_payments import promote_imported_incoming_payments
        from sqlalchemy import select

        async with self.sessions() as db:
            header, _, _ = await self._seed_promotable_receipt(db)
            await promote_imported_incoming_payments(db, source_database="fixture-hz")
            await db.commit()
            payment = await db.scalar(select(IncomingPayment).where(IncomingPayment.legacy_finance_record_id == header.id))
            header.source_payload = {**header.source_payload, "PaymentModeName": "源更新方式"}
            report = await promote_imported_incoming_payments(db, source_database="fixture-hz")
            self.assertEqual(report["updated"], 1)
            await db.commit()
            self.assertEqual(payment.payment_method, "源更新方式")
            payment.status = "本地已办理"
            await db.commit()
            header.source_payload = {**header.source_payload, "PaymentModeName": "不得覆盖"}
            with self.assertRaisesRegex(ValueError, "冲突"):
                await promote_imported_incoming_payments(db, source_database="fixture-hz")
            await db.rollback()
        async with self.sessions() as db:
            payment = await db.scalar(select(IncomingPayment).where(IncomingPayment.receipt_no == "HZ-RCPT-902"))
            self.assertEqual(payment.status, "本地已办理")
            self.assertEqual(payment.payment_method, "源更新方式")

    async def test_promoter_original_classification_is_atomic_and_never_uses_label(self):
        from app.core.imported_incoming_payments import promote_imported_incoming_payments
        from app.models import LegacyFinanceRecord

        async with self.sessions() as db:
            _, line, _ = await self._seed_promotable_receipt(db)
            dictionary = await db.scalar(select(LegacyFinanceRecord).where(
                LegacyFinanceRecord.source_table == "BAS_Case_FeeType"))
            raw_fee = await db.scalar(select(LegacyFinanceRecord).where(
                LegacyFinanceRecord.source_table == "FAM_AR_CaseFee"))
            for invalid in (None, "", "Y"):
                line.source_payload = {**line.source_payload, "IsActived": invalid}
                with self.assertRaises(ValueError):
                    await promote_imported_incoming_payments(db, source_database="fixture-hz")
                self.assertEqual(await db.scalar(select(func.count(IncomingPayment.id))), 0)
            line.source_payload = {**line.source_payload, "IsActived": "T"}
            raw_fee.source_payload = {**raw_fee.source_payload, "IsActived": "F"}
            raw_fee.is_active = False
            dictionary.source_payload = {**dictionary.source_payload, "TypeId": 5, "IsActived": None}
            await promote_imported_incoming_payments(db, source_database="fixture-hz")
            await db.commit()
            payment = await db.scalar(select(IncomingPayment))
            self.assertEqual(payment.allocations[0]["case_fee_type_id"], -200)
            self.assertEqual(payment.allocations[0]["base_fee_type_id"], 5)
            self.assertFalse(payment.allocations[0]["legacy_fee_is_active"])
            self.assertEqual(payment.allocated_amount, 10)
            payment.status = "本地已办理"
            await db.commit()
            dictionary.source_payload = {**dictionary.source_payload, "TypeId": 1}
            with self.assertRaisesRegex(ValueError, "冲突"):
                await promote_imported_incoming_payments(db, source_database="fixture-hz")
            await db.rollback()
        async with self.sessions() as db:
            payment = await db.scalar(select(IncomingPayment))
            self.assertEqual(payment.status, "本地已办理")
            self.assertEqual(payment.allocations[0]["base_fee_type_id"], 5)

    async def test_promoter_preserves_local_summary_and_rejects_source_update_conflict(self):
        from app.core.imported_incoming_payments import promote_imported_incoming_payments
        from app.core.incoming_allocation_records import allocation_revision

        async with self.sessions() as db:
            header, _, _ = await self._seed_promotable_receipt(db)
            await promote_imported_incoming_payments(db, source_database="fixture-hz")
            await db.commit()
            payment = await db.scalar(select(IncomingPayment))
            self.assertIsNone(payment.local_allocation_summary)
            payment.local_allocation_summary = {"version": 1, "allocation_revision": allocation_revision(payment.allocations),
                "allocated_amount": 10, "assigned_official_fee": 0, "assigned_agency_fee": 10, "assigned_other_fee": 0}
            await db.commit()
            expected = dict(payment.local_allocation_summary)
            result = await promote_imported_incoming_payments(db, source_database="fixture-hz")
            self.assertEqual(result["unchanged"], 1)
            self.assertEqual(payment.local_allocation_summary, expected)
            header.source_payload = {**header.source_payload, "PaymentModeName": "不得覆盖本地摘要"}
            with self.assertRaisesRegex(ValueError, "冲突"):
                await promote_imported_incoming_payments(db, source_database="fixture-hz")
            await db.rollback()
        async with self.sessions() as db:
            payment = await db.scalar(select(IncomingPayment))
            self.assertEqual(payment.local_allocation_summary, expected)
            self.assertEqual(payment.payment_method, "原方式")

    async def test_promoter_rejects_broken_parent_amount_and_existing_unproven_receipt(self):
        from app.core.imported_incoming_payments import promote_imported_incoming_payments
        from sqlalchemy import select, func

        async with self.sessions() as db:
            header, line, _ = await self._seed_promotable_receipt(db)
            line.parent_legacy_id = "other:902"
            with self.assertRaisesRegex(ValueError, "父回款"):
                await promote_imported_incoming_payments(db, source_database="fixture-hz")
            await db.rollback()
        async with self.sessions() as db:
            from app.models import LegacyFinanceAllocation
            line = await db.scalar(select(LegacyFinanceAllocation).where(LegacyFinanceAllocation.legacy_key == "fixture-hz:903"))
            line.amount = 9
            with self.assertRaisesRegex(ValueError, "分配金额"):
                await promote_imported_incoming_payments(db, source_database="fixture-hz")
            await db.rollback()
        async with self.sessions() as db:
            db.add(IncomingPayment(source_kind="hz_crm_20260930", receipt_no="HZ-RCPT-902",
                received_date=date(2026, 10, 16), amount=10, payer_name="旧回款无证据", operator="admin"))
            await db.commit()
            with self.assertRaisesRegex(ValueError, "禁止覆盖"):
                await promote_imported_incoming_payments(db, source_database="fixture-hz")
            self.assertEqual(await db.scalar(select(func.count(IncomingPayment.id))), 1)

    async def test_promoter_unknown_group_and_null_states_never_default_to_firm_or_pending(self):
        from app.core.imported_incoming_payments import promote_imported_incoming_payments
        from app.core.finance_centers import incoming_source_statement
        from app.core.finance import _general_settlement_rows

        async with self.sessions() as db:
            header, line, _ = await self._seed_promotable_receipt(db, group=None)
            header.source_payload = {**header.source_payload, "SettlementStatus": None}
            line.source_payload = {**line.source_payload, "ArchiveAmountSettlementStatus": None}
            report = await promote_imported_incoming_payments(db, source_database="fixture-hz")
            await db.commit()
            self.assertEqual(report["unclassified"], 1)
            payment = await db.scalar(incoming_source_statement().where(IncomingPayment.legacy_finance_record_id == header.id))
            self.assertIsNone(payment.finance_scope)
            self.assertIsNone(payment.resolved_finance_scope)
            self.assertIsNone(payment.legacy_settlement_status)
            self.assertIsNone(payment.allocations[0]["source_object"]["ArchiveAmountSettlementStatus"])
            self.assertEqual(await _general_settlement_rows({"username": "admin", "role": "admin", "_finance_scope": "unclassified"}, db), [])

    async def test_promoter_zero_group_remains_unclassified(self):
        from app.core.imported_incoming_payments import promote_imported_incoming_payments
        from app.core.finance_centers import incoming_source_statement

        async with self.sessions() as db:
            header, _, _ = await self._seed_promotable_receipt(db, group=0)
            report = await promote_imported_incoming_payments(db, source_database="fixture-hz")
            self.assertEqual(report["unclassified"], 1)
            payment = await db.scalar(incoming_source_statement().where(IncomingPayment.legacy_finance_record_id == header.id))
            self.assertIsNone(payment.finance_scope)
            self.assertIsNone(payment.resolved_finance_scope)

    async def test_promoter_accepts_proven_legacy_fee_without_duplicate_migration_source(self):
        from app.core.imported_incoming_payments import promote_imported_incoming_payments

        async with self.sessions() as db:
            _, _, fee = await self._seed_promotable_receipt(db)
            data = dict(fee.data)
            data.pop("legacy_record")
            data.update({"legacy_kind": "ar_case_fee", "source_table": "FAM_AR_CaseFee",
                         "legacy_source": "hz_crm_20260930", "expense_scope": "律所"})
            fee.data = data
            await db.commit()
            report = await promote_imported_incoming_payments(db, source_database="fixture-hz")
            self.assertEqual(report["created"], 1)
            await db.commit()
            self.assertNotIn("migration_source", fee.data)
            fee.data = {**fee.data, "migration_source": "other-source"}
            with self.assertRaisesRegex(ValueError, "同源费用"):
                await promote_imported_incoming_payments(db, source_database="fixture-hz")
            await db.rollback()

    async def test_import_mode_rejects_implicit_business_import_before_opening_database(self):
        from contextlib import ExitStack
        from pathlib import Path
        from unittest.mock import patch
        from scripts import import_legacy_finance as importer

        with ExitStack() as stack:
            stack.enter_context(patch.object(importer, "_load_schema_primary_keys", return_value={}))
            stack.enter_context(patch.object(importer, "load_bundle", return_value={}))
            records = stack.enter_context(patch.object(importer, "_build_records", return_value=[{"source_table": "FAM_AR_Payment"}]))
            for function in ("_build_allocations", "_build_files", "_build_audits"):
                stack.enter_context(patch.object(importer, function, return_value=[]))
            with self.assertRaisesRegex(ValueError, "必须显式选择"):
                await importer.run(Path("unused"), apply=False)
            with self.assertRaisesRegex(ValueError, "不能同时"):
                await importer.run(Path("unused"), apply=False, promote_hz_incoming=True, ledger_only=True)
            records.return_value = []
            with self.assertRaisesRegex(ValueError, "要求输入包含"):
                await importer.run(Path("unused"), apply=False, promote_hz_incoming=True)

    async def test_raw_reimport_preserves_only_database_owned_promotion_baseline(self):
        from app.core.imported_incoming_payments import (
            PROMOTION_KEY, preserve_incoming_promotion_markers, promote_imported_incoming_payments,
        )

        async with self.sessions() as db:
            header, _, _ = await self._seed_promotable_receipt(db)
            await promote_imported_incoming_payments(db, source_database="fixture-hz")
            await db.commit()
            row = {"source_table": header.source_table, "legacy_id": header.legacy_id,
                   "source_payload": dict(header.source_payload)}
            with self.assertRaisesRegex(ValueError, "保留"):
                await preserve_incoming_promotion_markers(db, [row])
            row["source_payload"].pop(PROMOTION_KEY)
            row["source_payload"]["PaymentModeName"] = "新的源方式"
            await preserve_incoming_promotion_markers(db, [row])
            self.assertEqual(row["source_payload"][PROMOTION_KEY], header.source_payload[PROMOTION_KEY])
            self.assertEqual(row["source_payload"]["PaymentModeName"], "新的源方式")

    async def test_reconcile_legacy_identity_requires_snapshots_and_preserves_primary_keys(self):
        from app.core.imported_incoming_payments import reconcile_unnamespaced_incoming, promote_imported_incoming_payments

        async with self.sessions() as db:
            header, line, fee = await self._seed_promotable_receipt(db)
            header_id, line_id = header.id, line.id
            source_header, source_object = dict(header.source_payload), dict(line.source_payload)
            incoming = {"source_table": header.source_table, "legacy_id": header.legacy_id,
                        "source_payload": source_header}
            detail = {"source_table": line.source_table, "legacy_key": line.legacy_key,
                      "source_payload": source_object, "is_active": True,
                      "_parent_key": (header.source_table, header.legacy_id)}
            header.legacy_id = "902"
            header.source_payload = {key: value for key, value in source_header.items() if not key.startswith("_")}
            line.legacy_key, line.parent_legacy_id = "903", "902"
            line.source_payload = {key: value for key, value in source_object.items() if not key.startswith("_")}
            payment = IncomingPayment(source_kind="hz_crm_20260930", receipt_no="HZ-RCPT-902",
                received_date=date(2026, 10, 16), amount=10, allocated_amount=10, payer_name="晋升付款方",
                operator="admin", status="已分配", allocations=[], claimed_customer="晋升客户",
                contract_record_id=header.contract_record_id, contract_no=header.legacy_contract_no,
                bank_source="现行到账行", bank_reference="LOCAL-BANK-REFERENCE")
            db.add(payment)
            await db.commit()
            with self.assertRaisesRegex(ValueError, "快照"):
                await reconcile_unnamespaced_incoming(db, [incoming], [detail])
            self.assertEqual(header.legacy_id, "902")
            self.assertIsNone(payment.legacy_finance_record_id)
            payment.allocations = [{"amount": 10, "fee_id": fee.id,
                "case_id": line.case_record_id, "case_no": line.legacy_case_no,
                "contract_no": header.legacy_contract_no, "local_allocation_note": "现行业务保留",
                "source_header": dict(header.source_payload), "source_object": dict(line.source_payload)}]
            await db.commit()
            await reconcile_unnamespaced_incoming(db, [incoming], [detail])
            self.assertEqual((header.id, line.id), (header_id, line_id))
            self.assertEqual(payment.legacy_finance_record_id, header_id)
            self.assertEqual(header.legacy_id, "fixture-hz:902")
            self.assertEqual(line.parent_legacy_id, header.legacy_id)
            self.assertEqual(line.legacy_key, "fixture-hz:903")
            self.assertEqual(payment.status, "已分配")
            self.assertEqual(payment.amount, 10)
            await promote_imported_incoming_payments(db, source_database="fixture-hz")
            await db.commit()
            self.assertEqual(payment.bank_source, "现行到账行")
            self.assertEqual(payment.bank_reference, "LOCAL-BANK-REFERENCE")
            header.source_payload = {**header.source_payload, "Remark": "源备注更新"}
            await promote_imported_incoming_payments(db, source_database="fixture-hz")
            self.assertEqual(payment.remark, "源备注更新")
            self.assertEqual(payment.bank_source, "现行到账行")
            self.assertEqual(payment.bank_reference, "LOCAL-BANK-REFERENCE")
            self.assertEqual(payment.allocations[0]["local_allocation_note"], "现行业务保留")
            await db.rollback()

    async def test_first_adoption_rejects_existing_local_summary_without_mutating_transaction_targets(self):
        from app.core.imported_incoming_payments import reconcile_unnamespaced_incoming
        from app.models import LegacyFinanceRecord, LegacyFinanceAllocation

        async with self.sessions() as db:
            header, line, fee = await self._seed_promotable_receipt(db)
            header_id, line_id = header.id, line.id
            incoming = {"source_table": header.source_table, "legacy_id": header.legacy_id,
                        "source_payload": dict(header.source_payload)}
            detail = {"source_table": line.source_table, "legacy_key": line.legacy_key,
                "source_payload": dict(line.source_payload), "is_active": True,
                "_parent_key": (header.source_table, header.legacy_id)}
            header.legacy_id, line.legacy_key, line.parent_legacy_id = "902", "903", "902"
            header.source_payload = {key: value for key, value in header.source_payload.items() if not key.startswith("_")}
            line.source_payload = {key: value for key, value in line.source_payload.items() if not key.startswith("_")}
            allocations = [{"amount": 10, "fee_id": fee.id, "case_id": line.case_record_id,
                "case_no": line.legacy_case_no, "contract_no": header.legacy_contract_no,
                "source_header": dict(header.source_payload), "source_object": dict(line.source_payload)}]
            summary = {"version": 1, "allocated_amount": 10, "assigned_agency_fee": 10}
            payment = IncomingPayment(source_kind="hz_crm_20260930", receipt_no="HZ-RCPT-902", finance_scope="firm",
                received_date=date(2026, 10, 16), amount=10, allocated_amount=10, allocations=allocations,
                claimed_customer="晋升客户", contract_record_id=header.contract_record_id, contract_no=header.legacy_contract_no,
                payer_name="晋升付款方", operator="admin", status="已分配", local_allocation_summary=summary)
            db.add(payment)
            await db.commit()
            payment_id = payment.id
            with self.assertRaisesRegex(ValueError, "人工对账"):
                async with db.begin():
                    await reconcile_unnamespaced_incoming(db, [incoming], [detail], adopt_legacy_baseline=True)
        async with self.sessions() as db:
            header = await db.get(LegacyFinanceRecord, header_id)
            line = await db.get(LegacyFinanceAllocation, line_id)
            payment = await db.get(IncomingPayment, payment_id)
            self.assertEqual((header.legacy_id, line.legacy_key, line.parent_legacy_id), ("902", "903", "902"))
            self.assertNotIn("_source_database", header.source_payload)
            self.assertIsNone(payment.legacy_finance_record_id)
            self.assertEqual(payment.allocations, allocations)
            self.assertEqual(payment.local_allocation_summary, summary)
            self.assertEqual((payment.amount, payment.allocated_amount, payment.status), (10, 10, "已分配"))

    async def test_promoter_never_recreates_a_deleted_promoted_receipt(self):
        from app.core.imported_incoming_payments import promote_imported_incoming_payments
        from sqlalchemy import select, func

        async with self.sessions() as db:
            await self._seed_promotable_receipt(db)
            await promote_imported_incoming_payments(db, source_database="fixture-hz")
            await db.commit()
            payment = await db.scalar(select(IncomingPayment).where(IncomingPayment.receipt_no == "HZ-RCPT-902"))
            await db.delete(payment)
            await db.commit()
            with self.assertRaises(ValueError):
                await promote_imported_incoming_payments(db, source_database="fixture-hz")
            self.assertEqual(await db.scalar(select(func.count(IncomingPayment.id))), 0)

    async def test_unallocated_legacy_baseline_requires_explicit_adoption_and_original_snapshot(self):
        from app.core.imported_incoming_payments import reconcile_unnamespaced_incoming, promote_imported_incoming_payments

        async with self.sessions() as db:
            header, line, _ = await self._seed_promotable_receipt(db)
            header.source_payload = {**header.source_payload, "AppliedAmount": 0}
            line.source_payload = {**line.source_payload, "IsActived": "F"}
            source_header, source_object = dict(header.source_payload), dict(line.source_payload)
            incoming = {"source_table": header.source_table, "legacy_id": header.legacy_id, "source_payload": source_header}
            detail = {"source_table": line.source_table, "legacy_key": line.legacy_key,
                "source_payload": source_object, "is_active": False,
                "_parent_key": (header.source_table, header.legacy_id)}
            header.legacy_id = "902"
            header.source_payload = {key: value for key, value in source_header.items() if not key.startswith("_")}
            line.legacy_key, line.parent_legacy_id, line.is_active = "903", "902", False
            line.source_payload = {key: value for key, value in source_object.items() if not key.startswith("_")}
            payment = IncomingPayment(source_kind="hz_crm_20260930", receipt_no="HZ-RCPT-902",
                received_date=date(2026, 10, 16), amount=10, allocated_amount=0, payer_name="晋升付款方",
                operator="admin", status="待分配", allocations=[], claimed_customer="晋升客户",
                contract_record_id=header.contract_record_id, contract_no=header.legacy_contract_no)
            db.add(payment)
            await db.commit()
            changed_input = {**incoming, "source_payload": {**source_header, "PaymentModeName": "新值不能充当旧基线"}}
            with self.assertRaises(ValueError):
                await reconcile_unnamespaced_incoming(db, [changed_input], [detail], adopt_legacy_baseline=True)
            with self.assertRaises(ValueError):
                await reconcile_unnamespaced_incoming(db, [incoming], [detail])
            await reconcile_unnamespaced_incoming(db, [incoming], [detail], adopt_legacy_baseline=True)
            report = await promote_imported_incoming_payments(db, source_database="fixture-hz")
            self.assertEqual(report["unchanged"], 1)
            self.assertEqual(payment.allocations, [])
            self.assertEqual(payment.allocated_amount, 0)
            self.assertEqual(payment.legacy_finance_record_id, header.id)
            await db.rollback()

    async def test_actual_case_fee_candidates_resolve_original_group_without_contract_center(self):
        from app.models import LegacyFinanceRecord
        from app.areas.finance.incoming_payments import incoming_payment_allocation_candidates
        from app.core.finance_centers import require_record_center, require_source_center
        from fastapi import HTTPException

        async with self.sessions() as db:
            customer = BusinessRecord(module="customer", serial_no="SOURCE-CUSTOMER", title="源客户", owner="admin", data={})
            contract = BusinessRecord(module="contract", serial_no="SOURCE-CONTRACT", title="源合同", customer="源客户", owner="admin", data={})
            db.add_all([customer, contract])
            await db.flush()
            case = BusinessRecord(module="case", serial_no="SOURCE-CASE", title="源案件", customer="源客户", owner="admin", data={"contract_id": contract.id})
            db.add(case)
            await db.flush()
            fee_ids = {}
            for number, group in ((81, 10), (82, 20)):
                db.add(LegacyFinanceRecord(source_table="FAM_AR_CaseFee", legacy_id=str(number),
                    record_kind="case_fee", primary_amount=10, source_payload={"CaseFeeId": number, "GroupId": group}))
                fee = BusinessRecord(module="finance", serial_no=f"SOURCE-FEE-{number}", title="历史代理费", customer="源客户", owner="admin", data={
                    "legacy_kind": "ar_case_fee", "legacy_source": "hz_crm_20260930", "source_table": "FAM_AR_CaseFee",
                    "legacy_case_fee_id": number, "case_fee_id": number,
                    "contract_id": contract.id, "case_id": case.id, "amount": 10, "fee_type": "代理费"})
                db.add(fee)
                await db.flush()
                fee_ids[group] = fee.id
            receipt = IncomingPayment(source_kind="manual", receipt_no="SOURCE-CANDIDATE", finance_scope="firm",
                received_date=date(2026, 10, 16), amount=10, payer_name="源客户", claimed_customer="源客户",
                operator="admin", status="待分配")
            db.add(receipt)
            await db.commit()
            identity = {"username": "admin", "role": "admin", "_finance_scope": "firm"}
            result = await incoming_payment_allocation_candidates(receipt.id, case_fees_only=True, identity=identity, db=db)
            self.assertEqual({row["fee_record_id"] for row in result["items"]}, {fee_ids[10]})
            firm_fee = await db.get(BusinessRecord, fee_ids[10])
            platform_fee = await db.get(BusinessRecord, fee_ids[20])
            await require_record_center(firm_fee, identity, db)
            self.assertEqual(await require_source_center(platform_fee, db), "platform")
            with self.assertRaises(HTTPException):
                await require_record_center(platform_fee, identity, db)
            self.assertEqual(contract.data, {})
            self.assertNotIn("finance_scope", firm_fee.data)

    async def test_source_link_keeps_namespaced_same_ids_separate(self):
        from app.models import LegacyFinanceRecord
        from app.core.finance_centers import incoming_source_statement

        async with self.sessions() as db:
            for namespace, group in ((None, 10), ("gd", 20), ("hz-next", 10)):
                payload = {"PaymentId": "71", "GroupId": group,
                           "PaymentModeName": namespace or "旧方式", "SettlementStatus": "25"}
                if namespace:
                    payload["_source_database"] = namespace
                header = LegacyFinanceRecord(source_table="FAM_AR_Payment",
                    legacy_id=f"{namespace}:71" if namespace else "71", record_kind="receipt",
                    primary_amount=10, source_payload=payload)
                db.add(header)
                await db.flush()
                if namespace == "hz-next":
                    linked_id = header.id
            db.add_all([
                IncomingPayment(source_kind="hz_crm_20260930", receipt_no="HZ-RCPT-71",
                    received_date=date(2026, 10, 16), amount=10, payer_name="旧回款", operator="admin"),
                IncomingPayment(source_kind="hz_crm_20260930", receipt_no="HZ-RCPT-LINKED",
                    legacy_finance_record_id=linked_id, received_date=date(2026, 10, 16),
                    amount=10, payer_name="新回款", operator="admin"),
            ])
            await db.commit()
            rows = list((await db.scalars(incoming_source_statement().where(
                IncomingPayment.receipt_no.in_(["HZ-RCPT-71", "HZ-RCPT-LINKED"]),
            ))).all())
            self.assertEqual(len(rows), 2)
            by_no = {row.receipt_no: row for row in rows}
            self.assertEqual(by_no["HZ-RCPT-71"].resolved_finance_scope, "firm")
            self.assertEqual(by_no["HZ-RCPT-71"].legacy_payment_method, "旧方式")
            self.assertEqual(by_no["HZ-RCPT-LINKED"].legacy_payment_method, "hz-next")
            self.assertEqual(by_no["HZ-RCPT-LINKED"].legacy_settlement_status, "25")

    async def test_imported_paid_receipt_cannot_reenter_pending_settlement(self):
        from app.models import LegacyFinanceRecord
        from app.core.finance import _general_settlement_rows
        from app.core.finance_centers import legacy_incoming_status_counts

        async with self.sessions() as db:
            for number, state in ((51, "5"), (52, "25"), (53, None)):
                db.add(LegacyFinanceRecord(source_table="FAM_AR_Payment", legacy_id=str(number),
                    record_kind="ar_payment", primary_amount=10, source_payload={
                        "PaymentId": str(number), "GroupId": 10, "SettlementStatus": state}))
                db.add(IncomingPayment(source_kind="hz_crm_20260930", receipt_no=f"HZ-RCPT-{number}",
                    received_date=date(2026, 10, 16), amount=10, allocated_amount=10,
                    payer_name="独立测试", claimed_customer="独立测试客户", operator="admin",
                    status="已分配", allocations=[{"amount": 10, "settlement_items": [{
                        "fee_type": "代理费", "amount": 10, "settlement_amount": 8, "archive_fee": 1}]}]))
            await db.commit()
            identity = {"username": "admin", "role": "admin", "_finance_scope": "firm"}
            rows = await _general_settlement_rows(identity, db)
            self.assertEqual([row["serial_no"] for row in rows], ["HZ-RCPT-51"])
            self.assertEqual(rows[0]["data"]["source_settlement_status"], "5")
            raw = await _general_settlement_rows(identity, db, include_active_receipts=True, receipt_detail=True)
            self.assertEqual({row["serial_no"] for row in raw}, {"HZ-RCPT-51", "HZ-RCPT-52", "HZ-RCPT-53"})
            counts = await legacy_incoming_status_counts(identity, db)
            self.assertEqual(counts["unmapped_legacy_status_total"], 1)
            self.assertEqual({row["source_status"]: row["count"] for row in counts["legacy_source_statuses"]},
                {"5": 1, "25": 1, None: 1})

    async def test_rolled_back_historical_settlement_returns_to_pending(self):
        """BUG20261028009：历史结算在新系统回滚（承接申请已撤回）后按原系统回到待结算，其他已付款历史仍不进入。"""
        from app.models import LegacyFinanceRecord
        from app.core.finance import _general_settlement_rows

        async with self.sessions() as db:
            for number in (61, 62):
                db.add(LegacyFinanceRecord(source_table="FAM_AR_Payment", legacy_id=str(number),
                    record_kind="ar_payment", primary_amount=10, source_payload={
                        "PaymentId": str(number), "GroupId": 10, "SettlementStatus": "25"}))
                db.add(IncomingPayment(source_kind="hz_crm_20260930", receipt_no=f"HZ-RCPT-{number}",
                    received_date=date(2026, 10, 16), amount=10, allocated_amount=10,
                    payer_name="独立测试", claimed_customer="独立测试客户", operator="admin",
                    status="已分配", allocations=[{"amount": 10, "settlement_items": [{
                        "fee_type": "代理费", "amount": 10, "settlement_amount": 8, "archive_fee": 1}]}]))
            await db.flush()
            rolled_back = await db.scalar(select(IncomingPayment).where(IncomingPayment.receipt_no == "HZ-RCPT-61"))
            db.add(BusinessRecord(module="finance_settlement", serial_no="JS-ADOPTED-61", title="承接", customer="", owner="admin",
                status="已撤回", data={"receipt_id": rolled_back.id, "legacy_projection_id": "legacy-normal:1",
                                     "legacy_source_status": "25", "rollback_comment": "分配有误"}))
            await db.commit()
            identity = {"username": "admin", "role": "admin", "_finance_scope": "firm"}
            rows = await _general_settlement_rows(identity, db)
            self.assertEqual([row["serial_no"] for row in rows], ["HZ-RCPT-61"])
            self.assertEqual(rows[0]["data"]["rejection_comment"], "分配有误")

    async def test_header_method_never_uses_bank_source_or_allocation_method(self):
        from app.core.finance import _incoming_payment_legacy_summary

        payment = IncomingPayment(source_kind="system", bank_source="工行",
            allocations=[{"payment_method": "费用通知到账确认", "amount": 10, "fee_type": "代理费"}])
        self.assertEqual(_incoming_payment_legacy_summary(payment)["payment_method"], "")
        payment.legacy_payment_method = "沪知招行"
        self.assertEqual(_incoming_payment_legacy_summary(payment)["payment_method"], "沪知招行")
        payment.payment_method = "现金"
        self.assertEqual(_incoming_payment_legacy_summary(payment)["payment_method"], "现金")

    async def test_existing_legacy_reader_filters_center_and_preserves_raw_settlement_state(self):
        from app.models import LegacyFinanceRecord, LegacyFinanceAllocation
        from app.areas.finance.router import list_legacy_finance_history, get_legacy_finance_history_record
        from fastapi import HTTPException

        async with self.sessions() as db:
            heads = []
            for number, group, state in ((1, 10, "25"), (2, 20, "30")):
                head = LegacyFinanceRecord(source_table="FAM_AR_Payment", legacy_id=f"HZ:{number}",
                    record_kind="ar_payment", primary_amount=100, status_code="2",
                    source_payload={"_source_database": "HZ", "PaymentId": str(number),
                        "GroupId": group, "PaymentStatus": "2", "SettlementStatus": state})
                db.add(head)
                heads.append(head)
            await db.flush()
            db.add(LegacyFinanceAllocation(legacy_finance_record_id=heads[0].id,
                parent_source_table="FAM_AR_Payment", parent_legacy_id="HZ:1",
                source_table="FAM_AR_Payment_Object", legacy_key="HZ:11", allocation_kind="ar_payment",
                amount=100, settlement_amount=80, archive_amount=8,
                source_payload={"_source_database": "HZ", "SeqId": "11", "PaymentId": "1",
                    "ArchiveAmountSettlementStatus": "30"}))
            await db.commit()
            head_id = heads[0].id
            identity = {"username": "admin", "role": "admin", "_finance_scope": "firm"}
            listing = await list_legacy_finance_history(record_kind="ar_payment", status_code="",
                audit_status_code="", keyword="", include_inactive=False, page=1, page_size=30,
                identity=identity, db=db)
            self.assertEqual(listing["total"], 1)
            self.assertEqual(listing["items"][0]["source_status"]["SettlementStatus"], "25")
            detail = await get_legacy_finance_history_record(head_id, identity=identity, db=db)
            self.assertTrue(detail["read_only"])
            self.assertEqual(detail["allocations"][0]["settlement_amount"], 80)
            self.assertEqual(detail["allocations"][0]["archive_amount"], 8)
            self.assertEqual(detail["allocations"][0]["source_status"]["ArchiveAmountSettlementStatus"], "30")
            self.assertEqual(detail["provenance"]["source_database"], "HZ")
            with self.assertRaises(HTTPException) as denied:
                await get_legacy_finance_history_record(head_id,
                    identity={**identity, "_finance_scope": "platform"}, db=db)
            self.assertEqual(denied.exception.status_code, 404)

    async def test_contract_receipts_use_exact_links_not_contract_center_or_scalar_coincidence(self):
        from sqlalchemy import select
        from app.core.incoming_contracts import contract_incoming_condition

        async with self.sessions() as db:
            contract = BusinessRecord(module="contract", serial_no="CONTRACT-SHARED", title="共享合同",
                owner="admin", data={})
            db.add(contract)
            await db.flush()
            for serial, center, root_id, root_no, allocations in (
                ("ROOT-FIRM", "firm", contract.id, contract.serial_no, []),
                ("ALLOCATION-PLATFORM", "platform", None, "", [{"contract_id": contract.id, "contract_no": contract.serial_no}]),
                ("UNRELATED", "firm", None, "", [{"case_id": contract.id, "amount": contract.id}]),
                ("CONFLICT", "firm", None, "", [{"contract_id": contract.id, "contract_no": "ANOTHER"}]),
            ):
                db.add(IncomingPayment(finance_scope=center, receipt_no=serial, received_date=date(2026, 10, 16),
                    amount=1, payer_name="独立测试", operator="admin", contract_record_id=root_id,
                    contract_no=root_no, allocations=allocations))
            await db.commit()
            rows = list((await db.scalars(select(IncomingPayment.receipt_no).where(
                contract_incoming_condition(contract, db),
            ))).all())
            self.assertEqual(set(rows), {"ROOT-FIRM", "ALLOCATION-PLATFORM"})

    async def test_legacy_settlements_without_receipt_are_classified_or_explicitly_unclassified(self):
        from sqlalchemy import select
        from app.core.finance_centers import settlement_center_conditions

        async with self.sessions() as db:
            payment = IncomingPayment(finance_scope="firm", receipt_no="CENTER-SETTLEMENT-SOURCE",
                received_date=date(2026, 10, 16), amount=100, payer_name="独立测试", operator="admin")
            db.add(payment)
            await db.flush()
            for serial, data in (
                ("LEGACY-FIRM", {"legacy_record": {"GroupId": 10}}),
                ("LEGACY-PLATFORM", {"legacy_record": {"GroupId": 20}}),
                ("LEGACY-UNKNOWN", {}),
                ("MODERN-FIRM", {"receipt_id": payment.id}),
                ("SOURCE-CONFLICT", {"receipt_id": payment.id, "finance_scope": "platform"}),
            ):
                db.add(BusinessRecord(module="finance_settlement", serial_no=serial, title=serial,
                    status="已付款", owner="admin", data={**data, "receipt_amount": 100.25}))
            await db.commit()
            for center, expected in (
                ("firm", {"LEGACY-FIRM", "MODERN-FIRM"}),
                ("platform", {"LEGACY-PLATFORM"}),
                ("unclassified", {"LEGACY-UNKNOWN", "SOURCE-CONFLICT"}),
            ):
                rows = list((await db.scalars(select(BusinessRecord).where(
                    BusinessRecord.module == "finance_settlement",
                    *settlement_center_conditions({"_finance_scope": center}),
                ))).all())
                self.assertEqual({row.serial_no for row in rows}, expected)
                self.assertTrue(all(row.status == "已付款" and row.data["receipt_amount"] == 100.25 for row in rows))

    async def test_finance_cache_parameters_include_request_center(self):
        from unittest.mock import AsyncMock, patch
        from app.areas.finance.query_cache_routes import _wrap_query

        async def endpoint(identity, db):
            return {"items": []}

        wrapped = _wrap_query(endpoint, "/finance/incoming-payments")
        cache = AsyncMock(return_value={"items": []})
        with patch("app.core.query_cache.cached_query", cache):
            for center in ("firm", "platform", "unclassified"):
                await wrapped(identity={"username": "admin", "_finance_scope": center}, db=None)
                self.assertEqual(cache.call_args.args[3], {"finance_scope": center})

    async def test_center_dependency_requires_explicit_scope_and_unknown_is_read_only(self):
        from fastapi import Depends, FastAPI
        from unittest.mock import AsyncMock, patch
        from app.core.finance_centers import finance_center_identity

        local = FastAPI()

        @local.get("/probe")
        @local.post("/probe")
        async def probe(identity=Depends(finance_center_identity)):
            return {"finance_scope": identity["_finance_scope"]}

        local.dependency_overrides[current_identity] = lambda: {"username": "admin", "role": "admin"}
        local.dependency_overrides[get_db] = lambda: None
        with patch("app.core.permissions._permission_payload_for_identity", AsyncMock(return_value={"menu_keys": []})):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=local), base_url="http://unit") as client:
                self.assertEqual((await client.get("/probe")).status_code, 422)
                self.assertEqual((await client.get("/probe", params={"finance_scope": "unassigned"})).status_code, 422)
                for center in ("firm", "platform", "unclassified"):
                    response = await client.get("/probe", params={"finance_scope": center})
                    self.assertEqual(response.json(), {"finance_scope": center})
                self.assertEqual((await client.post("/probe", params={"finance_scope": "unclassified"})).status_code, 409)
        local.dependency_overrides[current_identity] = lambda: {"username": "user", "role": "user"}
        with patch("app.core.permissions._permission_payload_for_identity", AsyncMock(return_value={"menu_keys": ["finance"]})):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=local), base_url="http://unit") as client:
                self.assertEqual((await client.get("/probe", params={"finance_scope": "firm"})).status_code, 200)
                self.assertEqual((await client.get("/probe", params={"finance_scope": "platform"})).status_code, 403)
                self.assertEqual((await client.get("/probe", params={"finance_scope": "unclassified"})).status_code, 403)

    async def test_shared_contract_and_nested_legacy_fee_use_same_sql_and_write_boundary(self):
        from types import SimpleNamespace
        from sqlalchemy import select
        from fastapi import HTTPException
        from app.core.finance_centers import record_center_conditions, require_record_center, require_source_center

        fixtures = [
            ("contract", "SHARED", {}),
            ("contract", "OTHER", {"contract_body": "平台"}),
            ("finance", "LEGACY-FIRM", {"legacy_record": {"GroupId": 10}}),
            ("finance", "CONFLICT", {"expense_scope": "律所", "legacy_record": {"GroupId": 20}}),
            ("finance", "PLATFORM", {"expense_scope": "平台"}),
        ]
        identity = {"_finance_scope": "firm"}
        async with self.sessions() as db:
            for module, serial, data in fixtures:
                db.add(BusinessRecord(module=module, serial_no=serial, title=serial, owner="admin", data=data))
            await db.commit()
            visible = set((await db.scalars(select(BusinessRecord.serial_no).where(*record_center_conditions(identity)))).all())
            self.assertEqual(visible, {"SHARED", "LEGACY-FIRM"})
            strict = set((await db.scalars(select(BusinessRecord.serial_no).where(*record_center_conditions(identity, allow_shared_contract=False)))).all())
            self.assertEqual(strict, {"LEGACY-FIRM"})
        await require_record_center(SimpleNamespace(module="contract", data={}), identity)
        await require_record_center(SimpleNamespace(module="finance", data={"legacy_record": {"GroupId": 10}}), identity)
        self.assertEqual(await require_source_center(SimpleNamespace(data={"expense_scope": "平台"})), "platform")
        for data in ({"expense_scope": "平台"}, {"expense_scope": "律所", "legacy_record": {"GroupId": 20}}, {}):
            with self.assertRaises(HTTPException):
                await require_record_center(SimpleNamespace(module="finance", data=data), identity)
        for data in ({}, {"expense_scope": "律所", "legacy_record": {"GroupId": 20}}):
            with self.assertRaises(HTTPException) as denied:
                await require_source_center(SimpleNamespace(data=data))
            self.assertEqual(denied.exception.status_code, 409)

    async def test_center_projection_keeps_unknown_visible_without_changing_history(self):
        from app.models import LegacyFinanceRecord
        from app.core.finance_centers import require_incoming_center, incoming_source_statement
        from fastapi import HTTPException
        from sqlalchemy import select

        async with self.sessions() as db:
            for number, group in ((1, 10), (2, 20), (3, 99)):
                db.add(LegacyFinanceRecord(
                    source_table="FAM_AR_Payment", legacy_id=str(number), record_kind="receipt",
                    primary_amount=number * 10, source_payload={"PaymentId": str(number),
                        "GroupId": group, "PaymentModeName": "银行转账"},
                ))
                db.add(IncomingPayment(
                    source_kind="hz_crm_20260930", receipt_no=f"HZ-RCPT-{number}",
                    received_date=date(2026, 10, 16), amount=number * 10,
                    payer_name="独立测试付款方", operator="admin", bank_source="工行",
                ))
            db.add(IncomingPayment(source_kind="manual", receipt_no="CENTER-UNKNOWN",
                received_date=date(2026, 10, 16), amount=40, payer_name="未分类", operator="admin"))
            db.add(IncomingPayment(source_kind="manual", receipt_no="CENTER-NEW",
                finance_scope="firm", payment_method="现金", received_date=date(2026, 10, 16),
                amount=50, payer_name="新登记", operator="admin"))
            await db.commit()

        identity = {"username": "admin", "role": "admin"}
        for center, total, amount in (("firm", 2, 60), ("platform", 1, 20), ("unclassified", 2, 70)):
            async with self.sessions() as db:
                result = await list_incoming_payments(
                    identity={**identity, "_finance_scope": center}, db=db,
                    page=1, page_size=1, view="finance-receipts-manage", filters="",
                )
                self.assertEqual(result["total"], total)
                self.assertEqual(result["summary"]["amount"], amount)
                self.assertEqual(result["totals"]["回款金额"], amount)
                self.assertEqual(result["unclassified_total"], 2)
                self.assertEqual(len(result["items"]), 1)
                self.assertEqual(result["items"][0]["finance_scope"], None if center == "unclassified" else center)

        async with self.sessions() as db:
            history = await db.scalar(incoming_source_statement().where(IncomingPayment.receipt_no == "HZ-RCPT-1"))
            self.assertEqual(history.resolved_finance_scope, "firm")
            self.assertEqual(history.legacy_payment_method, "银行转账")
            self.assertIsNone(history.finance_scope)
            self.assertEqual(history.amount, 10)
            self.assertEqual(history.allocated_amount, 0)
            self.assertEqual(history.allocations, [])
            with self.assertRaises(HTTPException) as denied:
                require_incoming_center(history, {**identity, "_finance_scope": "platform"})
            self.assertEqual(denied.exception.status_code, 409)
            self.assertEqual(await db.scalar(select(IncomingPayment.finance_scope).where(IncomingPayment.id == history.id)), None)


class SmokeFinanceRequestContractTest(unittest.TestCase):
    def test_payment_method_matches_legacy_hundred_character_limit(self):
        from app.api_schemas.finance import IncomingPaymentInput
        from pydantic import ValidationError

        body = {"received_date": "2026-10-16", "amount": 1, "payer_name": "独立测试"}
        self.assertEqual(IncomingPayment.__table__.c.payment_method.type.length, 100)
        self.assertEqual(IncomingPaymentInput(**body, payment_method="回" * 100).payment_method, "回" * 100)
        with self.assertRaises(ValidationError):
            IncomingPaymentInput(**body, payment_method="回" * 101)

    @classmethod
    def setUpClass(cls):
        import importlib.util
        from pathlib import Path

        path = Path(__file__).resolve().parents[3] / "scripts" / "smoke-api.py"
        spec = importlib.util.spec_from_file_location("finance_smoke_contract", path)
        cls.smoke = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.smoke)

    def test_fixture_scope_covers_queries_exports_cleanup_and_explicit_other_scopes(self):
        from urllib.parse import parse_qs, urlsplit

        for path in (
            "/finance/incoming-payments", "/finance/incoming-payments/import",
            "/finance/incoming-payments/123?reverse=true",
            "/finance/general-settlements/applications/123",
            "/finance/general-settlements/export?kind=official&ids=123",
            "/finance/archive-settlements/payment/review", "/finance/settlements/pending",
        ):
            with self.subTest(path=path):
                scoped = self.smoke.finance_fixture_path(path)
                self.assertEqual(parse_qs(urlsplit(scoped).query)["finance_scope"], ["firm"])
                self.assertEqual(self.smoke.finance_fixture_path(scoped), scoped)
        for scope in ("platform", "unclassified", ""):
            path = f"/finance/incoming-payments?finance_scope={scope}&page=2"
            self.assertEqual(self.smoke.finance_fixture_path(path), path)
        for path in ("/contracts/123/incoming-payments", "/finance/payment-packages", "/finance/incoming-payments-extra"):
            self.assertEqual(self.smoke.finance_fixture_path(path), path)

    def test_json_cleanup_and_upload_send_scope_without_network(self):
        from unittest.mock import MagicMock, patch
        from urllib.parse import parse_qs, urlsplit

        response = MagicMock()
        response.__enter__.return_value = response
        response.status = 200
        response.read.return_value = b"{}"
        response.headers = {"Content-Type": "application/json"}
        with patch.object(self.smoke.urllib.request, "urlopen", return_value=response) as opened:
            self.smoke.call("DELETE", "/finance/incoming-payments/123", expected=(200,))
            self.assertEqual(parse_qs(urlsplit(opened.call_args.args[0].full_url).query)["finance_scope"], ["firm"])
            self.smoke.multipart_upload("/finance/incoming-payments/import", {}, "bank.csv", b"", expected=(200,))
            self.assertEqual(parse_qs(urlsplit(opened.call_args.args[0].full_url).query)["finance_scope"], ["firm"])


@unittest.skipUnless(POSTGRES_URL, "设置 INCOMING_QUERY_TEST_POSTGRES_URL 运行独立 PostgreSQL 测试")
class PostgresIncomingQueryTest(RawIncomingBundleAssertions, IncomingQueryAssertions, unittest.IsolatedAsyncioTestCase):
    database_url = POSTGRES_URL

    async def test_incoming_source_lock_is_reentrant_and_busy_fails_without_waiting(self):
        import asyncio
        from app.core.imported_incoming_payments import lock_incoming_source
        from app.models import LegacyFinanceRecord

        source = "lock-" + self.schema
        async with self.sessions() as owner, self.sessions() as contender:
            await lock_incoming_source(owner, source)
            await lock_incoming_source(owner, source)
            with self.assertRaises(ValueError):
                await asyncio.wait_for(lock_incoming_source(contender, source), timeout=2)
            await contender.rollback()
            await owner.rollback()
            await asyncio.wait_for(lock_incoming_source(contender, source), timeout=2)
            await contender.rollback()
        async with self.sessions() as db:
            self.assertEqual(await db.scalar(select(func.count(IncomingPayment.id))), 0)
            self.assertEqual(await db.scalar(select(func.count(LegacyFinanceRecord.id))), 0)
