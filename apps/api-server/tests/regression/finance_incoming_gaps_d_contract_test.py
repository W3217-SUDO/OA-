"""Backend contract tests for finance gap D: incoming edit, refund claim, revoke, AR ledger."""

import unittest
from datetime import date
from inspect import signature
from unittest.mock import AsyncMock, Mock, patch

import httpx
from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.routing import APIRoute
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database import Base, get_db
from app.main import app
from app.models import (
    BusinessRecord,
    FileAttachment,
    FinanceTransaction,
    IncomingPayment,
    ReceivablePlan,
    RolePermission,
    User,
    WorkflowEvent,
)
from app.security import current_identity
from app.areas.finance import query_cache_routes as cache_routes


API = settings.api_prefix
ADMIN = {"username": "finance-d-admin", "role": "admin", "display_name": "财务D管理员", "department": "上海分所"}
USER = {"username": "finance-d-user", "role": "user", "display_name": "财务D员工", "department": "上海分所"}


class FinanceIncomingGapsDContractTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with self.sessions() as db:
            db.add_all([
                User(username="finance-d-admin", display_name="财务D管理员", department="上海分所", role="admin", password_hash="test", is_active=True),
                User(username="finance-d-user", display_name="财务D员工", department="上海分所", role="user", password_hash="test", is_active=True),
                RolePermission(role="admin", display_name="财务D管理员", data_scope="全所数据", menu_keys=["finance"], field_keys=["finance.amount"]),
                RolePermission(role="user", display_name="财务D员工", data_scope="全所数据", menu_keys=["finance"], field_keys=[]),
            ])
            customer = BusinessRecord(module="customer", serial_no="CODEX-FINANCE-D-CUST", title="CODEX D 客户", customer="CODEX D 客户", status="正常", owner="finance-d-admin", department="上海分所")
            contract = BusinessRecord(module="contract", serial_no="CODEX-FINANCE-D-HT", title="CODEX D 合同", customer="CODEX D 客户", status="审批通过", owner="finance-d-admin", department="上海分所", data={"amount": 1000})
            other_contract = BusinessRecord(module="contract", serial_no="CODEX-FINANCE-D-HT2", title="CODEX D 合同二", customer="CODEX D 客户", status="审批通过", owner="finance-d-admin", department="上海分所", data={"amount": 600})
            db.add_all([customer, contract, other_contract])
            await db.flush()
            self.customer_id = customer.id
            self.contract_id = contract.id
            self.other_contract_id = other_contract.id
            self.plan = ReceivablePlan(contract_record_id=contract.id, phase="首付款", due_date=date(2026, 8, 20), amount=500, received_amount=0, status="待收款", payer="CODEX D 客户")
            self.partial_plan = ReceivablePlan(contract_record_id=other_contract.id, phase="进度款", due_date=date(2026, 9, 1), amount=600, received_amount=0, status="待收款", payer="CODEX D 客户")
            db.add_all([self.plan, self.partial_plan])
            await db.flush()
            self.plan_id = self.plan.id
            self.partial_plan_id = self.partial_plan.id
            await db.commit()
        app.dependency_overrides[get_db] = self.override_db
        app.dependency_overrides[current_identity] = lambda: ADMIN
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://finance-d.test")

    async def override_db(self):
        async with self.sessions() as db:
            yield db

    async def asyncTearDown(self):
        await self.client.aclose()
        app.dependency_overrides.clear()

    async def _create_payment(self, payer="CODEX D 付款方", status_value="待认领", reference="CODEX-FINANCE-D-BANK-1", amount=200.0, claimed_customer="", allocated_amount=0.0, allocations=None):
        async with self.sessions() as db:
            item = IncomingPayment(
                receipt_no=f"HK-CODEX-D-{reference}",
                received_date=date(2026, 8, 1),
                amount=amount,
                payer_name=payer,
                bank_reference=reference,
                status=status_value,
                source_kind="manual",
                claimed_customer=claimed_customer,
                contract_no="CODEX-FINANCE-D-HT" if claimed_customer else "",
                claimant="finance-d-admin" if claimed_customer else "",
                allocated_amount=allocated_amount,
                allocations=allocations or [],
                operator="finance-d-admin",
            )
            db.add(item)
            await db.commit()
            await db.refresh(item)
            return item.id

    async def test_incoming_payment_edit_role_and_state_guards(self):
        payment_id = await self._create_payment()
        other_payment_id = await self._create_payment(reference="CODEX-FINANCE-D-BANK-2", amount=150)
        app.dependency_overrides[current_identity] = lambda: USER
        forbidden = await self.client.put(f"{API}/finance/incoming-payments/{payment_id}", json={
            "received_date": "2026-08-02", "amount": 210, "payer_name": "CODEX D 新付款方",
            "bank_reference": "CODEX-FINANCE-D-BANK-2", "customer": "", "contract_no": "", "remark": "编辑",
        })
        self.assertEqual(forbidden.status_code, status.HTTP_403_FORBIDDEN)
        app.dependency_overrides[current_identity] = lambda: ADMIN
        duplicate = await self.client.put(f"{API}/finance/incoming-payments/{payment_id}", json={
            "received_date": "2026-08-02", "amount": 210, "payer_name": "CODEX D 新付款方",
            "bank_reference": "CODEX-FINANCE-D-BANK-2", "customer": "", "contract_no": "", "remark": "编辑",
        })
        self.assertIsNotNone(other_payment_id)
        self.assertEqual(duplicate.status_code, status.HTTP_409_CONFLICT)
        ok = await self.client.put(f"{API}/finance/incoming-payments/{payment_id}", json={
            "received_date": "2026-08-02", "amount": 210, "payer_name": "CODEX D 新付款方",
            "bank_reference": "CODEX-FINANCE-D-BANK-3", "customer": "CODEX D 客户", "contract_no": "CODEX-FINANCE-D-HT", "remark": "编辑",
        })
        self.assertEqual(ok.status_code, status.HTTP_200_OK)
        body = ok.json()
        self.assertEqual(body["amount"], 210)
        self.assertEqual(body["payer_name"], "CODEX D 新付款方")
        self.assertEqual(body["claimed_customer"], "CODEX D 客户")
        self.assertEqual(body["contract_no"], "CODEX-FINANCE-D-HT")
        async with self.sessions() as db:
            item = await db.get(IncomingPayment, payment_id)
            item.status = "待分配"
            item.claimed_customer = "CODEX D 客户"
            item.allocated_amount = 50
            item.allocations = [{"receivable_plan_id": self.plan_id, "contract_id": self.contract_id, "amount": 50, "transaction_id": 999}]
            await db.commit()
        locked = await self.client.put(f"{API}/finance/incoming-payments/{payment_id}", json={
            "received_date": "2026-08-03", "amount": 200, "payer_name": "CODEX D 新付款方",
            "bank_reference": "CODEX-FINANCE-D-BANK-4", "customer": "", "contract_no": "", "remark": "编辑",
        })
        self.assertEqual(locked.status_code, status.HTTP_409_CONFLICT)

    async def test_refund_candidates_and_refund_claim_flow(self):
        fee = BusinessRecord(module="finance", serial_no="CODEX-FINANCE-D-FEE", title="CODEX D 法院诉讼费", customer="CODEX D 客户", status="已付款", owner="finance-d-admin", department="上海分所", data={"amount": 300, "fee_type": "官方费用", "case_no": "CODEX-FINANCE-D-CASE", "court": "上海市宝山区人民法院"})
        not_paid = BusinessRecord(module="finance", serial_no="CODEX-FINANCE-D-FEE2", title="CODEX D 未付款官费", customer="CODEX D 客户", status="待审批", owner="finance-d-admin", department="上海分所", data={"amount": 200, "fee_type": "官方费用", "case_no": "CODEX-FINANCE-D-CASE2", "court": "上海市浦东新区人民法院"})
        other_type = BusinessRecord(module="finance", serial_no="CODEX-FINANCE-D-FEE3", title="CODEX D 代理费", customer="CODEX D 客户", status="已付款", owner="finance-d-admin", department="上海分所", data={"amount": 500, "fee_type": "代理费", "case_no": "CODEX-FINANCE-D-CASE3", "court": "上海市宝山区人民法院"})
        async with self.sessions() as db:
            db.add_all([fee, not_paid, other_type])
            await db.commit()
            await db.refresh(fee)
            self.fee_id = fee.id
        payment_id = await self._create_payment(payer="上海市宝山区人民法院退诉讼费", reference="CODEX-FINANCE-D-BANK-COURT", amount=300)
        candidates = await self.client.get(f"{API}/finance/incoming-payments/{payment_id}/refund-candidates")
        self.assertEqual(candidates.status_code, status.HTTP_200_OK)
        data = candidates.json()
        self.assertEqual(data["remaining_amount"], 300)
        self.assertEqual([item["fee_record_id"] for item in data["items"]], [self.fee_id])
        self.assertEqual(data["items"][0]["match_amount"], 300)
        claim = await self.client.post(f"{API}/finance/incoming-payments/{payment_id}/refund-claim", json={"customer": "CODEX D 客户", "fee_record_id": self.fee_id, "comment": "法院退费认领"})
        self.assertEqual(claim.status_code, status.HTTP_200_OK)
        self.assertEqual(claim.json()["status"], "待分配")
        self.assertEqual(claim.json()["claimed_customer"], "CODEX D 客户")
        async with self.sessions() as db:
            events = list((await db.scalars(select(WorkflowEvent).where(WorkflowEvent.record_id.in_([self.customer_id, self.fee_id])))).all())
        self.assertEqual({event.action for event in events}, {"认领退费到账", "匹配退费到账"})
        async with self.sessions() as db:
            item = await db.get(IncomingPayment, payment_id)
            item.status = "待分配"
            item.claimed_customer = "CODEX D 客户"
            item.allocated_amount = 300
            item.allocations = [{"receivable_plan_id": self.plan_id, "contract_id": self.contract_id, "amount": 300, "transaction_id": 999}]
            await db.commit()
        bad_fee = await self.client.post(f"{API}/finance/incoming-payments/{payment_id}/refund-claim", json={"customer": "CODEX D 客户", "fee_record_id": fee.id, "comment": "重复"})
        self.assertEqual(bad_fee.status_code, status.HTTP_409_CONFLICT)

    async def test_batch_revoke_allocations_restores_plans_and_transactions(self):
        payment_id = await self._create_payment(payer="CODEX D 客户", status_value="待分配", claimed_customer="CODEX D 客户", reference="CODEX-FINANCE-D-BANK-ALLOC", amount=300)
        async with self.sessions() as db:
            tx = FinanceTransaction(finance_record_id=self.contract_id, transaction_type="回款", amount=300, transaction_date=date(2026, 8, 1), voucher_no="CODEX-FINANCE-D-BANK-ALLOC", counterparty="CODEX D 客户", operator="finance-d-admin", remark="分配")
            db.add(tx)
            await db.flush()
            item = await db.get(IncomingPayment, payment_id)
            item.allocated_amount = 300
            item.status = "已分配"
            item.allocations = [{"receivable_plan_id": self.plan_id, "contract_id": self.contract_id, "contract_no": "CODEX-FINANCE-D-HT", "phase": "首付款", "amount": 300, "transaction_id": tx.id, "allocated_by": "finance-d-admin", "allocated_at": "2026-08-01T10:00:00"}]
            plan = await db.get(ReceivablePlan, self.plan_id)
            plan.received_amount = 300
            plan.status = "已收款"
            await db.commit()
            self.tx_id = tx.id
        app.dependency_overrides[current_identity] = lambda: USER
        forbidden = await self.client.post(f"{API}/finance/incoming-payments/revoke-allocations", json={"payment_ids": [payment_id], "comment": "越权"})
        self.assertEqual(forbidden.status_code, status.HTTP_403_FORBIDDEN)
        app.dependency_overrides[current_identity] = lambda: ADMIN
        revoked = await self.client.post(f"{API}/finance/incoming-payments/revoke-allocations", json={"payment_ids": [payment_id], "comment": "撤销"})
        self.assertEqual(revoked.status_code, status.HTTP_200_OK)
        self.assertEqual(revoked.json()["revoked"], 1)
        self.assertEqual(revoked.json()["items"][0]["status"], "待分配")
        self.assertEqual(revoked.json()["items"][0]["allocated_amount"], 0)
        async with self.sessions() as db:
            plan = await db.get(ReceivablePlan, self.plan_id)
            tx = await db.get(FinanceTransaction, self.tx_id)
            event = await db.scalar(select(WorkflowEvent).where(WorkflowEvent.record_id == self.contract_id, WorkflowEvent.action == "撤销银行回款分配"))
            self.assertEqual(plan.received_amount, 0)
            self.assertEqual(plan.status, "待收款")
            self.assertIsNone(tx)
            self.assertIsNotNone(event)

    async def test_ar_summary_contract_file_and_contract_ledger(self):
        async with self.sessions() as db:
            attachment = FileAttachment(record_id=self.contract_id, category="合同附件", original_name="CODEX-D-contract.pdf", stored_name="codex-d-contract.pdf", content_type="application/pdf", size=10, path="/tmp/codex-d-contract.pdf", uploader="finance-d-admin", remark="合同附件")
            fee = BusinessRecord(module="finance", serial_no="CODEX-FINANCE-D-AP", title="CODEX D 应付官费", customer="CODEX D 客户", status="已付款", owner="finance-d-admin", department="上海分所", data={"amount": 120, "fee_type": "官方费用", "case_no": "CODEX-FINANCE-D-CASE", "contract_id": self.contract_id, "contract_no": "CODEX-FINANCE-D-HT", "court": "上海市宝山区人民法院"})
            db.add_all([attachment, fee])
            await db.flush()
            tx = FinanceTransaction(finance_record_id=fee.id, transaction_type="付款", amount=120, transaction_date=date(2026, 8, 1), voucher_no="CODEX-FINANCE-D-V", counterparty="上海市宝山区人民法院", operator="finance-d-admin", remark="付款")
            db.add(tx)
            await db.commit()
            await db.refresh(attachment)
            self.attachment_id = attachment.id
            self.fee_id = fee.id
            self.tx_id = tx.id
        summary = await self.client.get(f"{API}/finance/ar-summary")
        self.assertEqual(summary.status_code, status.HTTP_200_OK)
        rows = summary.json()["items"]
        self.assertEqual(len(rows), 2)
        first = next(row for row in rows if row["contract_record_id"] == self.contract_id)
        self.assertIsNotNone(first["contract_file"])
        self.assertEqual(first["contract_file"]["id"], self.attachment_id)
        self.assertEqual(first["contract_file"]["download_url"], f"{API}/attachments/{self.attachment_id}/download")
        self.assertEqual(first["ledger_url"], f"{API}/finance/contract-ledger/{self.contract_id}")
        second = next(row for row in rows if row["contract_record_id"] == self.other_contract_id)
        self.assertIsNone(second["contract_file"])
        ledger = await self.client.get(f"{API}/finance/contract-ledger/{self.contract_id}")
        self.assertEqual(ledger.status_code, status.HTTP_200_OK)
        data = ledger.json()
        self.assertEqual(data["contract"]["id"], self.contract_id)
        self.assertEqual(len(data["ar_rows"]), 1)
        self.assertEqual(data["ar_rows"][0]["remaining_amount"], 500)
        self.assertEqual(len(data["ap_rows"]), 1)
        self.assertEqual(data["ap_rows"][0]["serial_no"], "CODEX-FINANCE-D-AP")
        self.assertEqual(data["ap_rows"][0]["paid_amount"], 120)
        self.assertEqual(data["ap_rows"][0]["unpaid_amount"], 0)
        self.assertEqual(len(data["transactions"]), 1)
        self.assertEqual(data["transactions"][0]["transaction_type"], "付款")
        self.assertEqual(data["summary"]["ap_paid"], 120)
        hidden = await self.client.get(f"{API}/finance/contract-ledger/999999")
        self.assertEqual(hidden.status_code, status.HTTP_404_NOT_FOUND)


class FinanceQueryCacheRouteContractTest(unittest.IsolatedAsyncioTestCase):
    def test_actual_registration_preserves_routes_and_excludes_writes_files_auth(self):
        expected = {**cache_routes.FINANCE_JSON_QUERIES, **cache_routes.FINANCE_CONDITIONAL_QUERIES}
        mounted = {route.path.removeprefix(API): route for route in app.routes if isinstance(route, APIRoute) and route.methods == {"GET"}}
        self.assertEqual(len(expected), 60)
        self.assertEqual(len(cache_routes.FINANCE_FILE_QUERIES), 17)
        for path, name in expected.items():
            route = mounted[path]
            self.assertEqual(route.endpoint.__name__, name)
            self.assertIs(route.dependant.call.__wrapped__, route.endpoint)
            self.assertEqual(signature(route.dependant.call), signature(route.endpoint))
            self.assertEqual({dep.name for dep in route.dependant.dependencies}, {"db", "identity"})
        for path in cache_routes.FINANCE_FILE_QUERIES | {"/auth/me"}:
            self.assertIs(mounted[path].dependant.call, mounted[path].endpoint)
        for route in app.routes:
            if isinstance(route, APIRoute) and "GET" not in route.methods:
                self.assertIs(route.dependant.call, route.endpoint)

    async def test_associated_lists_and_parameter_categories_are_precise(self):
        db = Mock()
        for module in cache_routes.FINANCE_RECORD_LIST_MODULES:
            self.assertTrue(await cache_routes._financial_query_branch("/records", {"module": module, "db": db}))
        for module in ("hr", "task", "clue", "investigation", "warehouse", "unknown"):
            self.assertFalse(await cache_routes._financial_query_branch("/records", {"module": module, "db": db}))
        for category in ("fee_type", "case_file_type"):
            self.assertTrue(await cache_routes._financial_query_branch("/system/parameters/options", {"category": category}))
        self.assertFalse(await cache_routes._financial_query_branch("/system/parameters/options", {"category": "notary_office"}))
        db.scalar.assert_not_called()

    async def test_detail_cache_does_not_expand_to_linked_modules_or_audit_scope(self):
        db = Mock(scalar=AsyncMock())
        for module in cache_routes.FINANCIAL_RECORD_MODULES:
            db.scalar.return_value = module
            self.assertTrue(await cache_routes._financial_query_branch("/records/{record_id}", {"record_id": 1, "scope": "", "db": db}))
        for module in ("case", "customer", "contract", "clue", None):
            db.scalar.return_value = module
            self.assertFalse(await cache_routes._financial_query_branch("/records/{record_id}/history", {"record_id": 1, "db": db}))
        db.scalar.reset_mock()
        self.assertFalse(await cache_routes._financial_query_branch("/records/{record_id}", {"record_id": 1, "scope": "audit", "db": db}))
        db.scalar.assert_not_awaited()

    def _install_isolated_route(self, endpoint, path, **route_options):
        local = FastAPI()
        local.add_api_route(API + path, endpoint, methods=["GET"], **route_options)
        with patch.object(cache_routes, "FINANCE_JSON_QUERIES", {path: endpoint.__name__}), \
             patch.object(cache_routes, "FINANCE_CONDITIONAL_QUERIES", {}), \
             patch.object(cache_routes, "FINANCE_FILE_QUERIES", set()):
            cache_routes.install_finance_query_cache(local)
        return local

    async def test_asgi_cache_hit_still_authenticates_and_preserves_alias_defaults_filters(self):
        auth_calls = 0
        computed = 0
        identity_value = {"username": "CODEX-CACHE-A", "menu_keys": ["finance"], "data_scope": "self"}
        authenticated = True
        db_value = object()

        async def identity_dependency():
            nonlocal auth_calls
            auth_calls += 1
            if not authenticated:
                raise HTTPException(401, "认证失效")
            return dict(identity_value)

        async def db_dependency():
            yield db_value

        async def list_incoming_payments(payment_id: int, kind: str = Query("all", alias="type"),
                                         page: int = Query(1, ge=1), received_date: date | None = None,
                                         identity: dict = Depends(identity_dependency), db=Depends(db_dependency)):
            nonlocal computed
            computed += 1
            return {"id": payment_id, "kind": kind, "page": page, "date": received_date, "user": identity["username"]}

        path = "/finance/incoming-payments/{payment_id}"
        local = self._install_isolated_route(list_incoming_payments, path)
        keys = {}

        async def cache_stub(db, identity, namespace, parameters, compute):
            self.assertIs(db, db_value)
            self.assertEqual(namespace, "finance.list_incoming_payments")
            key = (str(sorted(identity.items())), tuple(sorted(parameters.items())))
            if key not in keys:
                keys[key] = await compute()
            return keys[key]

        cache = AsyncMock(side_effect=cache_stub)
        with patch("app.core.query_cache.cached_query", cache):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=local), base_url="http://cache-route.test") as client:
                url = API + "/finance/incoming-payments/7"
                first = await client.get(url)
                second = await client.get(url)
                self.assertEqual(first.json(), second.json())
                self.assertEqual(first.status_code, 200)
                self.assertEqual(computed, 1)
                self.assertEqual(auth_calls, 2)
                self.assertEqual(cache.call_args.args[3], {"payment_id": 7, "kind": "all", "page": 1, "received_date": None})
                filtered = await client.get(url, params={"type": "bank", "page": 2, "received_date": "2026-10-11"})
                self.assertEqual(filtered.json()["kind"], "bank")
                self.assertEqual(filtered.json()["date"], "2026-10-11")
                self.assertEqual(cache.call_args.args[3]["received_date"], date(2026, 10, 11))
                identity_value["data_scope"] = "department"
                await client.get(url)
                self.assertEqual(computed, 3)
                calls = cache.await_count
                authenticated = False
                self.assertEqual((await client.get(url)).status_code, 401)
                self.assertEqual(cache.await_count, calls)
                self.assertEqual((await client.get(url, params={"page": 0})).status_code, 401)

    async def test_response_status_and_headers_stay_owned_by_original_route(self):
        async def identity_dependency():
            return ADMIN

        async def db_dependency():
            yield object()

        async def query(identity: dict = Depends(identity_dependency), db=Depends(db_dependency)):
            return JSONResponse({"ok": True}, status_code=202, headers={"X-Query-Contract": "unchanged"})

        local = self._install_isolated_route(query, "/finance/summary")

        async def call_original(db, identity, namespace, parameters, compute):
            return await compute()

        with patch("app.core.query_cache.cached_query", AsyncMock(side_effect=call_original)):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=local), base_url="http://cache-route.test") as client:
                response = await client.get(API + "/finance/summary")
        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.headers["X-Query-Contract"], "unchanged")
        self.assertEqual(response.json(), {"ok": True})

    async def test_conditional_bypass_calls_original_without_cache(self):
        endpoint = AsyncMock(return_value={"items": []})
        endpoint.__name__ = "list_records"
        endpoint.__signature__ = signature(lambda module, identity, db: None)
        wrapped = cache_routes._wrap_query(endpoint, "/records")
        with patch("app.core.query_cache.cached_query", AsyncMock()) as cache:
            result = await wrapped(module="hr", identity=ADMIN, db=object())
        self.assertEqual(result, {"items": []})
        endpoint.assert_awaited_once()
        cache.assert_not_awaited()

    def test_unregistered_finance_get_and_special_request_parameter_fail_registration(self):
        async def identity_dependency():
            return ADMIN

        async def db_dependency():
            yield object()

        async def query(identity: dict = Depends(identity_dependency), db=Depends(db_dependency)):
            return {}

        local = FastAPI()
        local.add_api_route(API + "/finance/unreviewed", query, methods=["GET"])
        with self.assertRaisesRegex(RuntimeError, "未审计"):
            cache_routes.install_finance_query_cache(local)

        from starlette.requests import Request

        async def special(request: Request, identity: dict = Depends(identity_dependency), db=Depends(db_dependency)):
            return {}

        with self.assertRaisesRegex(RuntimeError, "非查询参数"):
            self._install_isolated_route(special, "/finance/summary")


if __name__ == "__main__":
    unittest.main()
