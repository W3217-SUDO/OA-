import os
import re
import unittest
from datetime import date
from types import SimpleNamespace
from unittest.mock import patch

from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool, StaticPool

from app.database import Base
from app.main import dashboard, list_receivable_details
from app.models import (
    BusinessRecord, ContractObject, FinanceTransaction, IncomingPayment,
    ReceivablePlan, User,
)


IDENTITY = {"username": "admin", "role": "admin"}


def _receipt_pool(fees):
    from app.core.fee_receipt_pool import FeeReceiptPool

    fields = ("case_id", "case_record_id", "case_no", "contract_id", "contract_record_id",
              "contract_no", "legacy_case_fee_id", "legacy_fee_id")
    # 只验证轻量池的 Python 消费契约，SQL 投影与触发器由读模型回归验证。
    return FeeReceiptPool.from_rows(SimpleNamespace(
        id=fee.id, status=fee.status, links=[(fee.data or {}).get(key) for key in fields],
        is_candidate=True,
    ) for fee in fees)


async def _read_binding_pool(db, fees):
    if db.get_bind().dialect.name == "postgresql":
        from app.core.dashboard_finance_read_model import read_dashboard_finance_fee_pool
        from app.core.fee_receipt_pool import FeeReceiptPool

        rows, _ = await read_dashboard_finance_fee_pool(db, [
            BusinessRecord.module == "finance", BusinessRecord.id.in_([fee.id for fee in fees]),
        ])
        return FeeReceiptPool.from_rows(rows)
    return _receipt_pool(fees)


class Row7ReceivableDetailTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        postgres_url = os.environ.get("OA_TEST_POSTGRES_URL")
        postgres_schema = os.environ.get("OA_TEST_POSTGRES_SCHEMA")
        if postgres_url is not None or postgres_schema is not None:
            if not postgres_url or not postgres_schema or not re.fullmatch(r"oa_test_[a-z0-9_]+", postgres_schema):
                raise ValueError("PostgreSQL 回归必须同时指定独立测试库连接和 oa_test_ schema")
            database_name = make_url(postgres_url).database or ""
            if not database_name.startswith("CODEX-"):
                raise ValueError("财务回归只能使用任务专属 CODEX- 测试库")
            self.engine = create_async_engine(postgres_url, poolclass=NullPool,
                connect_args={"server_settings": {"search_path": postgres_schema}})
            self.addAsyncCleanup(self.engine.dispose)
            connection = await self.engine.connect()
            self.addAsyncCleanup(connection.close)
            transaction = await connection.begin()
            self.addAsyncCleanup(transaction.rollback)
            target = (await connection.execute(text("SELECT current_database(), current_schema()"))).one()
            self.assertEqual(tuple(target), (database_name, postgres_schema))
            # 所有测试会话绑定同一个外层事务；用例中的 commit 只释放保存点。
            self.sessions = async_sessionmaker(connection, expire_on_commit=False, class_=AsyncSession,
                                               join_transaction_mode="create_savepoint")
            return
        self.engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.addAsyncCleanup(self.engine.dispose)
        self.sessions = async_sessionmaker(
            self.engine, expire_on_commit=False, class_=AsyncSession,
        )
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

    async def test_compact_receipts_preserve_binding_pool_and_zero_nested_receipts(self):
        from app.core.fee_cash_query import read_fee_receipts
        from app.core.finance_summary_query import receivable_payment_projection
        from app.core.formatters import _case_fee_display_type

        async with self.sessions() as db:
            case = BusinessRecord(module="case", serial_no="CODEX-COMPACT-CASE", title="案件",
                                  status="一审", owner="admin", department="测试部", data={})
            db.add(case)
            await db.flush()
            definitions = [("官费", "草稿", 912345), ("代理费", "草稿", 0),
                           ("官费", "草稿", 0), ("官费", "已删除", 0),
                           ("官费", "草稿", 0), ("代理费", "草稿", 0)]
            fees = [BusinessRecord(module="finance", serial_no=f"CODEX-COMPACT-FEE-{index}",
                        title=fee_type, status=status, owner="admin", department="测试部",
                        data={"fee_type": fee_type, "case_id": case.id, "case_no": case.serial_no,
                              "legacy_case_fee_id": legacy_id, "amount": 100})
                    for index, (fee_type, status, legacy_id) in enumerate(definitions)]
            db.add_all(fees)
            await db.flush()
            fees[1].data = {**fees[1].data, "legacy_fee_id": " 912345 ", "case_id": str(case.id)}
            fees[5].data = {**fees[5].data, "legacy_case_fee_id": fees[0].id,
                            "legacy_fee_id": str(fees[0].id)}
            db.add(IncomingPayment(receipt_no="CODEX-COMPACT-RECEIPT", received_date=date(2026, 10, 12),
                amount=500, payer_name="测试客户", status="已认领", operator="admin", allocations=[
                    {"fee_id": fees[0].id, "amount": 99,
                     "settlement_items": [{"fee_id": fees[2].id, "amount": 0}]},
                    {"legacy_case_fee_id": 912345, "amount": 50},
                    {"case_no": case.serial_no, "amount": 88},
                    {"fee_id": fees[0].id, "amount": 0.015},
                    {"fee_id": fees[0].id, "amount": 0.005},
                    {"fee_id": fees[1].id, "amount": 1.234},
                    {"fee_id": fees[3].id, "amount": 99},
                    {"fee_id": fees[0].id, "amount": 77,
                     "settlement_items": [{"fee_id": fees[1].id, "amount": 0}]},
                    {"fee_record_id": fees[0].id, "fee_id": fees[1].id, "amount": 3},
                    {"fee_record_id": 912345, "fee_id": fees[0].id, "amount": 4},
                    {"legacy_fee_id": fees[0].id, "amount": 2},
                ]))
            await db.commit()
            original = await receivable_payment_projection(fees, IDENTITY, db, record_scope=[], receipts_only=True)
            with patch("app.core.formatters._case_fee_display_type", wraps=_case_fee_display_type) as display:
                compact = await receivable_payment_projection(
                    fees, IDENTITY, db, record_scope=[], receipts_only=True, compact_receipts=True,
                )
                display.assert_not_called()
            self.assertEqual(compact, {
                fees[0].id: {"cashed_amount": 7.02},
                fees[1].id: {"cashed_amount": 1.23},
                fees[2].id: {"cashed_amount": 0.0},
                fees[5].id: {"cashed_amount": 2.0},
            })
            pool = await _read_binding_pool(db, fees)
            indexed = await receivable_payment_projection(
                [fee for fee in fees if fee.title == "官费"], IDENTITY, db,
                record_scope=[], receipts_only=True, compact_receipts=True, receipt_pool=pool,
            )
            self.assertEqual(indexed, compact)
            active_fees = [fee for fee in fees if fee.status != "已删除"]
            binding = pool.receipt_binding()
            original_receipts = await read_fee_receipts(
                active_fees, {case.serial_no: active_fees}, set(), db, filter_related=True,
            )
            indexed_receipts = await read_fee_receipts(
                [], binding.group_by_case({case.id: case}, {case.serial_no: case}), set(), db,
                filter_related=True, binding=binding,
            )
            self.assertEqual(indexed_receipts, original_receipts)
            self.assertNotIn(fees[3].id, original)
            self.assertEqual(original[fees[4].id]["cashed_amount"], 0)
            for fee_id, values in compact.items():
                self.assertEqual(values["cashed_amount"], original[fee_id]["cashed_amount"])
            self.assertTrue(all(set(values) == {"fee_type", "cashed_amount"} for values in original.values()))
            with self.assertRaises(ValueError):
                await receivable_payment_projection(fees, IDENTITY, db, compact_receipts=True)
            with self.assertRaises(ValueError):
                await receivable_payment_projection(fees, IDENTITY, db, receipts_only=True,
                                                    receipt_pool=_receipt_pool(fees))

    def test_receipt_pool_preserves_raw_keys_and_non_deleted_scope(self):
        from app.core.fee_receipt_pool import FeeReceiptPool

        def row(fee_id, status, case_id, case_no, legacy_id, alias):
            return SimpleNamespace(id=fee_id, status=status,
                links=[case_id, None, case_no, None, None, None, legacy_id, alias], is_candidate=False)

        rows = [row(11, None, " +21 ", " CASE ", " +100 ", 100),
                row(12, "草稿", 21.9, 23, True, 1.9),
                row(13, "草稿", False, "", "bad", {}),
                row(14, "已删除", "bad", "CASE", 100, 1)]
        pool = FeeReceiptPool.from_rows(rows)
        binding = pool.receipt_binding()
        self.assertEqual(pool.all_record_ids, {11, 12, 13, 14})
        self.assertEqual(binding.fee_ids, {11, 12, 13})
        self.assertEqual(binding.legacy_fee_ids, {100: 11, 1: 12})
        self.assertEqual(binding.case_ids, {21})
        self.assertEqual(binding.case_nos, {" CASE ", "23"})
        self.assertEqual(binding.case_ids_by_fee, {11: 21, 12: 21, 13: 0})
        merged = pool.with_rows([row(15, "草稿", 0, "", 100, 10**30)])
        self.assertEqual([item.id for item in merged.rows], [11, 12, 13, 14, 15])
        self.assertEqual(merged.receipt_binding().legacy_fee_ids, {1: 12, 10**30: 15})
        self.assertEqual(pool.receipt_binding().legacy_fee_ids, {100: 11, 1: 12})
        with self.assertRaises(ValueError):
            FeeReceiptPool.from_rows([row(16, "草稿", "bad", None, None, None)]).receipt_binding()

    async def test_receipt_pool_keeps_local_legacy_and_global_case_ambiguity(self):
        from app.core.finance_summary_query import receivable_payment_projection
        from app.core.finance_read_scope import finance_read_scope

        async with self.sessions() as db:
            cases = [BusinessRecord(module="case", serial_no=f"CODEX-POOL-CASE-{index}", title="案件",
                        status="一审", owner="admin", department="测试部", data={}) for index in range(3)]
            db.add_all(cases)
            await db.flush()
            fees = [BusinessRecord(module="finance", serial_no=f"CODEX-POOL-FEE-{index}", title="官费",
                        status="草稿", owner="admin", department="测试部",
                        data={"case_id": case.id, "case_no": case.serial_no if index < 2 else "",
                              "legacy_fee_id": 777 if index == 0 else 0, "amount": 100})
                    for index, case in enumerate(cases)]
            hidden = BusinessRecord(module="finance", serial_no="CODEX-POOL-HIDDEN", title="代理费",
                status="已删除", owner="other", department="其他部",
                data={"case_no": cases[0].serial_no, "legacy_case_fee_id": 777})
            db.add_all([*fees, hidden])
            await db.flush()
            db.add(IncomingPayment(receipt_no="CODEX-POOL-RECEIPT", received_date=date(2026, 10, 12),
                amount=100, payer_name="测试客户", status="已认领", operator="admin", allocations=[
                    {"legacy_fee_id": 777, "amount": 5},
                    {"case_no": cases[0].serial_no, "amount": 80},
                    {"case_no": cases[1].serial_no, "amount": 2.345},
                    {"case_no": cases[2].serial_no, "amount": 11},
                    {"fee_id": fees[2].id, "amount": 0},
                ]))
            await db.commit()
            with finance_read_scope(db):
                expected = await receivable_payment_projection(
                    fees, IDENTITY, db, record_scope=[], receipts_only=True, compact_receipts=True,
                )
                actual = await receivable_payment_projection(
                    [], IDENTITY, db, record_scope=[], receipts_only=True, compact_receipts=True,
                    receipt_pool=await _read_binding_pool(db, fees),
                )
                self.assertEqual(actual, expected)
                self.assertEqual(actual, {fees[0].id: {"cashed_amount": 5.0},
                    fees[1].id: {"cashed_amount": round(2.345, 2)}, fees[2].id: {"cashed_amount": 0.0}})
                case_only = await receivable_payment_projection(
                    [], IDENTITY, db, record_scope=[], receipts_only=True, compact_receipts=True,
                    receipt_pool=await _read_binding_pool(db, [fees[2]]),
                )
                original_case_only = await receivable_payment_projection(
                    [fees[2]], IDENTITY, db, record_scope=[], receipts_only=True, compact_receipts=True,
                )
                self.assertEqual(case_only, original_case_only)
                # 即使案件编号能解析，收款上非空案号仍必须等于费用原始案号。
                self.assertEqual(case_only, {fees[2].id: {"cashed_amount": 0.0}})

    async def test_compact_summary_preserves_deleted_type_and_object_claims(self):
        from app.core.finance import _receivable_fee_category
        from app.core.finance_summary_query import read_fee_summaries
        from app.core.projections import _receivable_detail_projection

        async with self.sessions() as db:
            contract = BusinessRecord(module="contract", serial_no="CODEX-COMPACT-CONTRACT", title="合同",
                                      status="审批通过", owner="admin", department="测试部", data={})
            db.add(contract)
            await db.flush()
            cases = [BusinessRecord(module="case", serial_no=f"CODEX-COMPACT-TYPE-CASE-{index}", title="案件",
                        status="一审", owner="admin", department="测试部", data={"contract_id": contract.id})
                     for index in range(3)]
            db.add_all(cases)
            await db.flush()
            agency = ContractObject(contract_record_id=contract.id, case_record_id=cases[0].id,
                                    fee_type="代理费", amount=100, created_by="admin", updated_by="admin")
            empty_type = ContractObject(contract_record_id=contract.id, case_record_id=cases[0].id,
                                        fee_type="", amount=100, created_by="admin", updated_by="admin")
            official = ContractObject(contract_record_id=contract.id, case_record_id=cases[2].id,
                                      fee_type="官方费用", amount=100, created_by="admin", updated_by="admin")
            db.add_all([agency, empty_type, official])
            await db.flush()
            definitions = [
                ("草稿", {"fee_type": "官费", "contract_object_id": agency.id}),
                ("草稿", {"fee_type": "代理费", "fee_type_name": "官费", "amount": 100.125,
                          "received_amount": 10.125}),
                ("已删除", {"fee_type": "官费", "fee_type_name": "代理费", "amount": 30, "received_amount": 5}),
                ("草稿", {"fee_type": "官费", "fee_type_name": "代理费"}),
                ("已删除", {"fee_type": "代理费", "fee_type_name": "官费"}),
                ("草稿", {"fee_type": "", "amount": 40}),
                ("草稿", {"fee_type": "代理费", "expense_scope": "内部费用",
                          "commission_lifecycle": "待结算", "source_fee_id": 1}),
                ("草稿", {"fee_type": "代理费", "contract_object_id": official.id,
                          "received_amount": 10.125}),
                ("草稿", {"fee_type": "代理费", "fee_type_name": {"label": "官费"},
                          "amount": 50, "received_amount": 5}),
                ("草稿", {"fee_type": "官费", "amount": 0}),
                ("草稿", {"fee_type": "代理费", "case_fee_type_name": "官费",
                          "amount": 60, "received_amount": 7}),
                ("草稿", {"fee_type": "代理费", "expense_subtype": "官费",
                          "amount": 70, "received_amount": 8}),
                ("草稿", {"fee_type": "代理费", "fee_type_name": "代理费", "case_fee_type_name": "官费"}),
                ("草稿", {"fee_type": " ", "amount": 90}),
                ("草稿", {"fee_type": "代理费", "fee_type_name": False}),
            ]
            fees = []
            for index, (status, data) in enumerate(definitions):
                case = cases[0] if index == 0 else cases[2] if index == 7 else cases[1]
                fees.append(BusinessRecord(module="finance", serial_no=f"CODEX-COMPACT-TYPE-FEE-{index}",
                    title="服务费" if index in (6, 7, 8, 14) else "官费", status=status, owner="admin", department="测试部",
                    data={"contract_id": contract.id, "case_id": case.id, "case_no": case.serial_no,
                          "amount": 100, **data}))
            db.add_all(fees)
            await db.flush()
            db.add(IncomingPayment(receipt_no="CODEX-POOL-OBJECT-RECEIPT", received_date=date(2026, 10, 12),
                amount=20, payer_name="测试客户", status="已认领", operator="admin",
                allocations=[{"fee_id": fees[7].id, "case_no": cases[2].serial_no, "amount": 20}]))
            await db.commit()
            records = [contract, *cases, *fees]
            identity = {**IDENTITY, "_dashboard_case_ids": {case.id for case in cases}}
            original = await _receivable_detail_projection(
                identity, db, records, summary_only=True, official_only=True,
            )
            with patch("app.core.finance._receivable_fee_category", wraps=_receivable_fee_category) as classify:
                compact = await _receivable_detail_projection(
                    identity, db, records, summary_only=True, official_only=True, dashboard_finance_only=True,
                )
                self.assertEqual(classify.call_count, 6)
            self.assertEqual(compact, original)
            self.assertEqual({row["id"]: row["remaining_amount"] for row in compact}, {
                f"fee:{fees[1].id}": 90.0, f"fee:{fees[2].id}": 25.0, f"fee:{fees[5].id}": 40.0,
                f"object:{official.id}": 80.0, f"fee:{fees[8].id}": 45.0,
                f"fee:{fees[10].id}": 53.0, f"fee:{fees[11].id}": 62.0, f"fee:{fees[13].id}": 90.0,
            })
            active_fees = [fee for fee in fees if fee.status != "已删除"]
            rich_fees = [fee for fee in active_fees if fee.id != fees[6].id]
            pool = _receipt_pool(active_fees)
            supplemented_ids = []
            from app.core.dashboard_finance_read_model import LINK_FIELDS, read_dashboard_finance_fee_pool
            from app.core.fee_receipt_pool import FeeReceiptPool

            if db.get_bind().dialect.name == "postgresql":
                bindings, projected = await read_dashboard_finance_fee_pool(db, [
                    BusinessRecord.module == "finance", BusinessRecord.id.in_([fee.id for fee in fees]),
                ])
                self.assertEqual({row.id: row.is_candidate for row in bindings},
                                 {fee.id: index != 6 for index, fee in enumerate(fees)})
                self.assertEqual({row.id: row.links for row in bindings},
                                 {fee.id: [fee.data.get(key) for key in LINK_FIELDS] for fee in fees})
                self.assertEqual({fee.id for fee in projected}, {fee.id for fee in fees if fee.id != fees[6].id})
                self.assertIs(next(fee for fee in projected if fee.id == fees[14].id).data["fee_type_name"], False)
                pool = FeeReceiptPool.from_rows(row for row in bindings if row.status != "已删除")
                rich_fees = [fee for fee in projected if fee.status != "已删除"]
                self.assertEqual(pool.all_record_ids, {fee.id for fee in active_fees})

            async def read_related_pool(db, conditions, *, where_data):
                if db.get_bind().dialect.name == "postgresql":
                    # 仅记录真实查询返回的编号，不替换 SQL、候选判断或结果。
                    rows, related = await read_dashboard_finance_fee_pool(db, conditions, where_data=where_data)
                    supplemented_ids.extend(row.id for row in rows)
                    return rows, related
                # SQLite 只模拟新读模型返回形态，不宣称覆盖 PostgreSQL 候选谓词。
                related = await read_fee_summaries(db, conditions, where_data=where_data)
                supplemented_ids.extend(fee.id for fee in related)
                return _receipt_pool(related).rows, related

            with patch("app.core.dashboard_finance_read_model.read_dashboard_finance_fee_pool",
                       side_effect=read_related_pool):
                indexed = await _receivable_detail_projection(
                    identity, db, [contract, *cases, *rich_fees], summary_only=True, official_only=True,
                    dashboard_finance_only=True, receipt_pool=pool,
                )
            self.assertEqual(indexed, compact)
            self.assertEqual(set(supplemented_ids), {fees[2].id, fees[4].id})
            with self.assertRaises(ValueError):
                await _receivable_detail_projection(identity, db, records,
                                                    receipt_pool=_receipt_pool(active_fees))

    async def test_dashboard_and_detail_share_receivable_projection(self):
        async with self.sessions() as db:
            db.add(User(
                username="case-owner", display_name="案件负责人", department="上海分所",
                password_hash="test-only", role="user", role_ids=["user"],
            ))
            contract = BusinessRecord(
                module="contract", serial_no="CODEX-8.27-7-CONTRACT",
                title="第7行应收合同", customer="第7行客户", status="审批通过",
                owner="case-owner", department="上海分所",
                data={"contract_body": "律所", "source_person": "case-owner"},
            )
            db.add(contract)
            await db.flush()
            case = BusinessRecord(
                module="case", serial_no="CODEX-8.27-7-CASE",
                title="第7行应收案件", customer="第7行客户", status="一审",
                owner="case-owner", department="上海分所",
                data={
                    "contract_id": contract.id, "contract_no": contract.serial_no,
                    "case_stage": "一审", "case_type": "民事案件",
                },
            )
            db.add(case)
            await db.flush()
            contract_object = ContractObject(
                contract_record_id=contract.id, case_record_id=case.id,
                fee_type="一审诉讼费", amount=100, remark="第7行官费标的",
                created_by="admin", updated_by="admin",
            )
            db.add(contract_object)
            await db.flush()
            fee = BusinessRecord(
                module="finance", serial_no="CODEX-8.27-7-FEE",
                title="一审诉讼费", customer="第7行客户", status="已付款",
                owner="cashier", department="财务部",
                data={
                    "fee_type": "官方费用", "expense_subtype": "一审诉讼费",
                    "amount": 100, "case_id": case.id, "case_no": case.serial_no,
                    "contract_id": contract.id,
                    "contract_object_id": contract_object.id,
                },
            )
            db.add(fee)
            await db.flush()

            other_contract = BusinessRecord(
                module="contract", serial_no="CODEX-8.27-7-OTHER-CONTRACT",
                title="其他人员应收合同", customer="第7行其他客户", status="审批通过",
                owner="other-user", department="上海分所", data={"contract_body": "律所"},
            )
            db.add(other_contract)
            await db.flush()
            other_case = BusinessRecord(
                module="case", serial_no="CODEX-8.27-7-OTHER-CASE",
                title="其他人员应收案件", customer="第7行其他客户", status="一审",
                owner="other-user", department="上海分所",
                data={"contract_id": other_contract.id, "case_stage": "一审", "case_type": "民事案件"},
            )
            db.add(other_case)
            await db.flush()
            other_contract_object = ContractObject(
                contract_record_id=other_contract.id, case_record_id=other_case.id,
                fee_type="公证费", amount=50, remark="其他人员官费标的",
                created_by="other-user", updated_by="other-user",
            )
            db.add(other_contract_object)
            await db.flush()
            other_fee = BusinessRecord(
                module="finance", serial_no="CODEX-8.27-7-OTHER-FEE",
                title="公证费", customer="第7行其他客户", status="已付款",
                owner="cashier", department="财务部",
                data={
                    "fee_type": "官方费用", "expense_subtype": "公证费",
                    "amount": 50, "case_id": other_case.id,
                    "case_no": other_case.serial_no,
                    "contract_id": other_contract.id,
                    "contract_object_id": other_contract_object.id,
                },
            )
            db.add(other_fee)
            await db.flush()
            db.add_all([
                FinanceTransaction(
                    finance_record_id=fee.id, transaction_type="付款", amount=70,
                    transaction_date=date(2026, 8, 27), voucher_no="CODEX-8.27-7-PAY",
                    counterparty="法院", operator="admin",
                ),
                IncomingPayment(
                    receipt_no="CODEX-8.27-7-RECEIPT", received_date=date(2026, 8, 27),
                    amount=20, payer_name="第7行客户", bank_reference="CODEX-8.27-7-BANK",
                    status="已认领", claimed_customer="第7行客户",
                    contract_record_id=contract.id, contract_no=contract.serial_no,
                    case_no=case.serial_no, allocated_amount=20,
                    allocations=[{"fee_id": fee.id, "amount": 20}], operator="admin",
                ),
                ReceivablePlan(
                    contract_record_id=contract.id, phase="官费首付款",
                    due_date=date(2026, 9, 1), amount=999, received_amount=0,
                    status="待收款", payer="第7行客户",
                ),
                FinanceTransaction(
                    finance_record_id=other_fee.id, transaction_type="付款", amount=50,
                    transaction_date=date(2026, 8, 27), voucher_no="CODEX-8.27-7-OTHER-PAY",
                    counterparty="公证处", operator="cashier",
                ),
            ])
            await db.commit()

            owner_identity = {"username": "case-owner", "role": "user", "role_ids": ["user"]}
            dashboard_result = await dashboard(owner_identity, db, section="metrics")
            detail_result = await list_receivable_details("official-fee-unreceived", owner_identity, db)

        metric = next(
            item for item in dashboard_result["metrics"]
            if item["key"] == "official-fee-unreceived"
        )
        self.assertEqual(metric["value"], "80.00元")
        self.assertEqual(metric["route"], "dashboard-queue-official-fee-unreceived")

        self.assertEqual(detail_result["official_unreceived"], 80.0)
        row = next(item for item in detail_result["items"] if item["owner"] == "case-owner")
        self.assertEqual(row["contract_no"], "CODEX-8.27-7-CONTRACT")
        self.assertEqual(row["case_no"], "CODEX-8.27-7-CASE")
        self.assertEqual(row["case_stage"], "一审")
        self.assertEqual(row["case_type"], "民事案件")
        self.assertEqual(row["source_type"], "contract_object")
        self.assertEqual(row["fee_type"], "一审诉讼费")
        self.assertEqual(row["paid_amount"], 70.0)
        self.assertEqual(row["received_amount"], 20.0)
        self.assertEqual(row["remaining_amount"], 80.0)
        self.assertEqual(row["owner"], "case-owner")
        self.assertFalse(any(
            item["contract_no"] == "CODEX-8.27-7-OTHER-CONTRACT"
            for item in detail_result["items"]
        ))
        self.assertFalse(any(item["source_type"] == "receivable_plan" for item in detail_result["items"]))


if __name__ == "__main__":
    unittest.main()
