"""9.29 第10行返工：独立数据库、真实 JWT 和实际案件/合同/财务入口回归。"""
import asyncio
import os
from pathlib import Path
import unittest
from datetime import date

import httpx
from sqlalchemy import delete, event, func, select, text

test_db = Path(os.environ["OA_RW10_TEST_DB"]).resolve()
upload_dir = Path(os.environ["UPLOAD_ROOT"]).resolve()
if test_db.name != "row10-test.db" or test_db.parent.name != "runtime" or "apps" in test_db.parts:
    raise RuntimeError("只能使用第10行外部隔离 runtime/row10-test.db")
if upload_dir.parent != test_db.parent or upload_dir.name != "uploads":
    raise RuntimeError("附件必须使用同一隔离 runtime/uploads")
test_db.parent.mkdir(parents=True, exist_ok=True)
upload_dir.mkdir(exist_ok=True)
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///" + test_db.as_posix()
os.environ["SEED_DEMO_DATA"] = "false"

from app.database import Base, SessionLocal, engine
from app.main import app
from app.models import BusinessRecord, FinanceTransaction, JobRole, SystemParameter, User, WorkflowEvent
from app.security import create_token
from app.core.constants import FIELD_KEYS

PREFIX = "CODEX-929-RW10-"


class Rework10(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://rw10.test")
        self.serial = 0
        async with SessionLocal() as db:
            for name, role, fields in [("admin", "admin", list(FIELD_KEYS)), ("applicant", "user", list(FIELD_KEYS)),
                                       ("hidden", "user", [key for key in FIELD_KEYS if key != "finance.amount"])]:
                code = PREFIX + name
                db.add(User(username=code, display_name="测试" + name, role=role, password_hash="not-for-login",
                    department=PREFIX + "部门", profile={"permission_role_code": code} if role != "admin" else {}, is_active=True))
                if role != "admin":
                    db.add(JobRole(code=code, name=code, permissions=["contract-mine", "finance-payment-mine", "finance-payment-audit", "case-mine", "合同付款申请", "case.fee.payment"],
                        field_keys=fields, field_keys_configured=True,
                        data_scope="本人及共享数据"))
            parameter = SystemParameter(category="payment_type", code=PREFIX + "PAY", name="测试付款单位", is_active=True,
                extra={"nature": "对公", "payee": "测试收款单位", "account_bank": "测试银行", "account": "TEST-ACCOUNT"})
            db.add(parameter)
            await db.commit()
            self.payment_type_id = parameter.id
        self.actor("admin")

    async def asyncTearDown(self):
        await self.client.aclose()
        async with engine.begin() as connection:
            await connection.execute(text("PRAGMA foreign_keys=OFF"))
            for table in reversed(Base.metadata.sorted_tables):
                await connection.execute(delete(table))
            self.assertEqual(await connection.scalar(select(func.count()).select_from(BusinessRecord)), 0)
        for path in upload_dir.rglob("*"):
            if path.is_file():
                path.unlink()
        await engine.dispose()

    def actor(self, name):
        self.client.headers["Authorization"] = "Bearer " + create_token(PREFIX + name, "user")

    async def api(self, method, path, code=200, **kwargs):
        response = await self.client.request(method, "/api/v1" + path, **kwargs)
        self.assertEqual(response.status_code, code, response.text)
        return response.json() if response.content else None

    async def record(self, module, data=None, status="草稿", owner="admin", customer=None):
        self.serial += 1
        async with SessionLocal() as db:
            row = BusinessRecord(module=module, serial_no=f"{PREFIX}{module}-{self.serial}", title=PREFIX + module,
                customer=customer or PREFIX + "客户", owner=PREFIX + owner, department=PREFIX + "部门", status=status, data=data or {})
            db.add(row)
            await db.commit()
            return row

    async def change(self, row, *, status=None, **data):
        async with SessionLocal() as db:
            current = await db.get(BusinessRecord, row.id)
            current.data = {**current.data, **data}
            if status:
                current.status = status
            await db.commit()
            row.data, row.status = dict(current.data), current.status

    async def setup_sources(self, owner="admin", merged=True):
        head = await self.record("contract", {"contract_body": "律所"}, status="审批中", owner=owner)
        original = await self.record("contract", {"contract_body": "律所"}, status="审批中", owner=owner)
        source = await self.record("case", {"contract_id": original.id, "contract_no": original.serial_no}, owner=owner)
        master = await self.record("case", {"contract_id": head.id, "contract_no": head.serial_no,
            "case_creation_step": "completed", "case_type": "民事", "case_team_usernames": [PREFIX + owner],
            "merged_sources": [{"id": source.id, "serial_no": source.serial_no}] if merged else []}, status="一审阶段", owner=owner)
        if merged:
            await self.change(source, status="已合并", merged_into_case_id=master.id, merged_into_case_no=master.serial_no)
        common = {"case_id": master.id, "case_record_id": master.id, "case_no": master.serial_no,
                  "fee_type": "官方费用", "expense_scope": "律所", "amount": 100, "paid_amount": 0,
                  "handler": PREFIX + owner, "expense_subtype": "一审诉讼费"}
        own = await self.record("finance", {**common, "contract_id": head.id, "contract_no": head.serial_no}, owner=owner)
        moved = await self.record("finance", {**common, "contract_id": original.id, "contract_no": original.serial_no,
            **({"merged_from_case_id": source.id, "merged_from_case_no": source.serial_no} if merged else {})}, owner=owner)
        return head, original, master, source, own, moved

    def body(self, fee, amount=60):
        return {"payment_type_id": self.payment_type_id, "application_date": str(date.today()),
                "lines": [{"case_fee_id": fee.id, "amount": amount}]}

    async def create_payment(self, contract, fee, amount=60):
        return await self.api("POST", f"/contracts/{contract.id}/payment-applications", code=201, json=self.body(fee, amount))

    async def candidates(self, contract):
        result = await self.api("GET", f"/contracts/{contract.id}/payment-candidates")
        return {item["case_fee_id"]: item for item in result["items"] if item.get("case_fee_id")}

    async def totals(self, fee):
        return (await self.api("GET", f"/records/{fee.id}"))["data"]

    async def test_merged_sources_and_normal_multicontract_and_internal_boundaries(self):
        head, original, master, source, own, moved = await self.setup_sources()
        internal = await self.record("finance", {**moved.data, "expense_scope": "内部", "fee_type": "内部费用"})
        platform = await self.record("finance", {**moved.data, "expense_scope": "平台"})
        invalid = await self.record("finance", {**moved.data, "merged_from_case_no": "wrong"})
        outsider = await self.record("finance", moved.data, customer=PREFIX + "其他客户")
        rows = await self.candidates(head)
        self.assertEqual(set(rows), {own.id, moved.id, platform.id})
        self.assertEqual(rows[moved.id]["remaining_amount"], 100)
        for rejected in (internal, invalid, outsider):
            await self.api("POST", f"/contracts/{head.id}/payment-applications", code=404, json=self.body(rejected))
        normal, _, _, _, normal_own, other = await self.setup_sources(merged=False)
        self.assertEqual(set(await self.candidates(normal)), {normal_own.id})
        await self.api("POST", f"/contracts/{normal.id}/payment-applications", code=404, json=self.body(other))

    async def test_historical_cp_zero_raw_projection_all_read_paths_and_amount_permission(self):
        head, _, master, _, own, _ = await self.setup_sources(owner="hidden")
        historical = await self.record("contract_payment", {"contract_id": head.id, "contract_no": head.serial_no,
            "applicant": PREFIX + "hidden", "amount": 60, "lines": [{"case_fee_id": own.id, "amount": 60}]},
            status="待审批", owner="hidden")
        data = await self.totals(own)
        self.assertEqual((data["payment_requested_amount"], data["direct_payment_requested_amount"], data["payment_remaining_amount"]), (60, 0, 40))
        listing = await self.api("GET", "/records", params={"module": "finance", "page_size": 100})
        self.assertEqual(next(row for row in listing["items"] if row["id"] == own.id)["data"]["payment_requested_amount"], 60)
        context = await self.api("GET", f"/case-spaces/{master.id}/context")
        self.assertEqual(next(row for row in context["finances"]["fees"] if row["id"] == own.id)["data"]["payment_requested_amount"], 60)
        async with SessionLocal() as db:
            self.assertNotIn("payment_requested_amount", (await db.get(BusinessRecord, own.id)).data)
        self.actor("hidden")
        hidden = await self.totals(own)
        # 既有可见页面 capability 同时授予原金额字段；新字段与原金额保持相同口径。
        self.assertEqual("amount" in hidden, "payment_requested_amount" in hidden)
        from app.core.contracts import _contract_customer_record_dicts
        async with SessionLocal() as db:
            restricted = await _contract_customer_record_dicts([await db.get(BusinessRecord, own.id)], set(), db)
        self.assertFalse({"amount", "payment_requested_amount", "contract_payment_requested_amount", "direct_payment_requested_amount", "payment_remaining_amount"} & set(restricted[0]["data"]))

    async def test_cross_contract_and_case_submission_share_one_global_balance(self):
        head, original, _, _, _, moved = await self.setup_sources()
        payment = await self.create_payment(head, moved, 60)
        await self.api("POST", f"/finance/fees/{moved.id}/submit", json={"amount": 30, "payment_type_id": self.payment_type_id})
        data = await self.totals(moved)
        self.assertEqual((data["direct_payment_requested_amount"], data["contract_payment_requested_amount"], data["payment_requested_amount"]), (30, 60, 90))
        self.assertEqual((await self.candidates(original))[moved.id]["remaining_amount"], 10)
        self.assertEqual((await self.candidates(head))[moved.id]["remaining_amount"], 10)
        await self.api("POST", f"/contracts/{original.id}/payment-applications", code=422, json=self.body(moved, 11))
        async with SessionLocal() as db:
            raw = await db.get(BusinessRecord, moved.id)
            self.assertEqual((raw.data["payment_requested_amount"], raw.data["contract_id"]), (30, original.id))
            self.assertEqual(await db.scalar(select(func.count()).select_from(BusinessRecord).where(BusinessRecord.module == "contract_payment")), 1)
        self.assertEqual((await self.totals(moved))["payment_requested_amount"], 90)

    async def test_contract_cancel_reject_reapply_pay_and_failed_reapply_are_atomic(self):
        head, original, _, _, _, moved = await self.setup_sources()
        first = await self.create_payment(head, moved, 60)
        key = f"/contract-payment-applications/{first['id']}"
        await self.api("POST", key + "/cancel", json={"reason": "撤回核对"})
        self.assertEqual((await self.totals(moved))["payment_requested_amount"], 0)
        first = await self.create_payment(head, moved, 60)
        key = f"/contract-payment-applications/{first['id']}"
        await self.api("POST", key + "/review", json={"approved": False, "comment": "驳回"})
        await self.api("POST", key + "/submit", json={"comment": "修改后重提"})
        self.assertEqual((await self.totals(moved))["payment_requested_amount"], 60)
        await self.api("POST", key + "/review", json={"approved": False, "comment": "再次驳回"})
        second = await self.create_payment(original, moved, 70)
        await self.api("POST", key + "/submit", code=422, json={"comment": "余额不足"})
        self.assertEqual((await self.api("GET", f"/records/{first['id']}"))["status"], "已驳回")
        await self.api("POST", f"/contract-payment-applications/{second['id']}/review", json={"approved": True})
        await self.api("POST", f"/contract-payment-applications/{second['id']}/pay", json={"paid_date": str(date.today()), "voucher_no": "RW10-VOUCHER"})
        self.assertEqual((await self.totals(moved))["payment_requested_amount"], 70)
        await self.api("POST", f"/contract-payment-applications/{second['id']}/cancel", code=409, json={"reason": "已付不可撤"})
        async with SessionLocal() as db:
            txs = list((await db.scalars(select(FinanceTransaction))).all())
            self.assertEqual([(row.finance_record_id, row.amount) for row in txs], [(second["id"], 70)])
            self.assertNotIn("payment_requested_amount", (await db.get(BusinessRecord, moved.id)).data)

    async def test_real_mine_and_audit_record_sources_show_one_cp_and_applicant(self):
        head, _, _, _, own, _ = await self.setup_sources(owner="applicant")
        self.actor("applicant")
        payment = await self.create_payment(head, own, 60)
        for page, actor in [("finance-payment-mine", "applicant"), ("finance-payment-audit", "admin")]:
            self.actor(actor)
            fees = await self.api("GET", "/records", params={"module": "finance", "page_size": 100}, headers={"X-Page-Key": page})
            cps = await self.api("GET", "/records", params={"module": "contract_payment", "page_size": 100}, headers={"X-Page-Key": page})
            rows = [*fees["items"], *cps["items"]]
            rows = [r for r in rows if (r["data"].get("applicant") or r["owner"]) == PREFIX + "applicant"] if actor == "applicant" else [r for r in rows if r["status"] == "待审批"]
            found = [row for row in rows if row["id"] == payment["id"]]
            self.assertEqual(len(found), 1)
            self.assertEqual((found[0]["data"]["amount"], found[0]["data"]["applicant"]), (60, PREFIX + "applicant"))
        async with SessionLocal() as db:
            self.assertEqual(await db.scalar(select(func.count()).select_from(BusinessRecord).where(BusinessRecord.module == "finance")), 2)

    async def test_read_projection_echo_is_not_written_and_batch_has_constant_queries(self):
        head, _, _, _, own, _ = await self.setup_sources()
        await self.create_payment(head, own, 60)
        dto = await self.totals(own)
        body = {**dto, "title": own.title, "customer": own.customer, "handler": own.owner,
                "case_record_id": own.data["case_id"], "contract_record_id": head.id}
        await self.api("PUT", f"/finance/fees/{own.id}", json=body)
        denied = await self.api("PATCH", f"/records/{own.id}", json={"data": dto})
        self.assertFalse(denied["IsSuccess"])
        for _ in range(20):
            await self.record("finance", own.data)
        from app.core.case_fee_payments import fee_payment_totals
        async with SessionLocal() as db:
            rows = list((await db.scalars(select(BusinessRecord).where(BusinessRecord.module == "finance"))).all())
            statements = []
            def counted(conn, cursor, statement, params, context, executemany):
                statements.append(statement)
            event.listen(engine.sync_engine, "before_cursor_execute", counted)
            try:
                totals = await fee_payment_totals(rows, db)
            finally:
                event.remove(engine.sync_engine, "before_cursor_execute", counted)
            self.assertEqual(len(totals), 22)
            self.assertEqual(len(statements), 2)
            raw = await db.get(BusinessRecord, own.id)
            self.assertFalse({"payment_requested_amount", "direct_payment_requested_amount", "contract_payment_requested_amount", "payment_remaining_amount"} & set(raw.data))

    async def test_concurrent_original_and_merged_contract_cannot_overreserve(self):
        head, original, _, _, _, moved = await self.setup_sources()
        responses = await asyncio.gather(*[self.client.post(f"/api/v1/contracts/{contract.id}/payment-applications", json=self.body(moved, 70)) for contract in (head, original)])
        self.assertEqual(sum(response.status_code == 201 for response in responses), 1, [r.text for r in responses])
        self.assertTrue(all(r.status_code in {201, 409, 422} for r in responses))
        self.assertEqual((await self.totals(moved))["payment_requested_amount"], 70)

    async def test_two_direct_payment_packages_preserve_cp_and_historical_document(self):
        head, _, _, _, own, _ = await self.setup_sources()
        cp = await self.create_payment(head, own, 60)
        package_ids = []
        for index, amount in enumerate((30, 10), 1):
            await self.api("POST", f"/finance/fees/{own.id}/submit", json={"amount": amount, "payment_type_id": self.payment_type_id})
            await self.api("POST", f"/finance/fees/{own.id}/review", json={"approved": True})
            fee_document = await self.api("GET", f"/finance/payment-workflow/{own.id}/document")
            self.assertEqual(fee_document["data"]["amount"], amount)
            package = await self.api("POST", f"/finance/payment-workflow/{own.id}/submit")
            package_ids.append(package["id"])
            self.assertEqual(package["data"]["amount"], amount)
            self.assertEqual(package["data"]["items"][0]["amount"], amount)
            document = await self.api("GET", f"/finance/payment-workflow/{package['id']}/document")
            self.assertEqual((document["data"]["items"][0]["current_payment"], document["data"]["items"][0]["fee_amount"]), (amount, 100))
            await self.api("POST", f"/finance/payment-workflow/{package['id']}/writeoff", code=409,
                data={"paid_date": str(date.today()), "amount": amount + 1, "payment_method": "银行卡", "invoice_no": f"RW10-{index}"},
                files={"files": ("voucher.pdf", b"%PDF-RW10", "application/pdf")})
            await self.api("POST", f"/finance/payment-workflow/{package['id']}/writeoff",
                data={"paid_date": str(date.today()), "amount": amount, "payment_method": "银行卡", "invoice_no": f"RW10-{index}"},
                files={"files": ("voucher.pdf", b"%PDF-RW10", "application/pdf")})
            data = await self.totals(own)
            self.assertEqual(data["payment_requested_amount"], 90 if index == 1 else 100)
            self.assertEqual(data["payment_remaining_amount"], 10 if index == 1 else 0)
        self.assertEqual(len(set(package_ids)), 2)
        old_document = await self.api("GET", f"/finance/payment-workflow/{package_ids[0]}/document")
        self.assertEqual(old_document["data"]["items"][0]["current_payment"], 30)
        async with SessionLocal() as db:
            txs = list((await db.scalars(select(FinanceTransaction).where(FinanceTransaction.finance_record_id == own.id))).all())
            self.assertEqual([row.amount for row in txs], [30, 10])
            self.assertEqual((await db.get(BusinessRecord, own.id)).data["payment_requested_amount"], 40)
            self.assertEqual((await db.get(BusinessRecord, cp["id"])).status, "待审批")

    async def test_direct_transaction_cannot_pay_cp_share_and_paid_is_not_counted_twice(self):
        head, _, _, _, own, _ = await self.setup_sources()
        await self.create_payment(head, own, 60)
        await self.api("POST", f"/finance/fees/{own.id}/submit", json={"amount": 30, "payment_type_id": self.payment_type_id})
        await self.api("POST", f"/finance/fees/{own.id}/review", json={"approved": True})
        body = {"finance_record_id": own.id, "transaction_type": "付款", "amount": 31, "transaction_date": str(date.today())}
        await self.api("POST", "/finance/transactions", code=409, json=body)
        await self.api("POST", "/finance/transactions", code=201, json={**body, "amount": 30})
        self.assertEqual((await self.totals(own))["payment_remaining_amount"], 10)
        await self.api("POST", f"/finance/fees/{own.id}/submit", json={"amount": 10, "payment_type_id": self.payment_type_id})
        self.assertEqual((await self.totals(own))["payment_requested_amount"], 100)

    async def test_legacy_ap_keeps_independent_full_payment_amount(self):
        legacy = await self.record("finance", {"legacy_kind": "ap_payment", "amount": 80, "expense_scope": "律所", "fee_type": "官方费用"}, status="已审批")
        package = await self.api("POST", f"/finance/payment-workflow/{legacy.id}/submit")
        self.assertEqual(package["data"]["amount"], 80)

    async def test_reject_cancel_and_rollback_release_current_direct_request_keep_paid(self):
        head, _, _, _, own, _ = await self.setup_sources()
        await self.create_payment(head, own, 60)
        await self.api("POST", f"/finance/fees/{own.id}/submit", json={"amount": 30, "payment_type_id": self.payment_type_id})
        await self.api("POST", f"/finance/fees/{own.id}/review", json={"approved": True})
        await self.api("POST", "/finance/transactions", code=201, json={"finance_record_id": own.id, "transaction_type": "付款", "amount": 30, "transaction_date": str(date.today())})
        for operation, payload in [("review", {"approved": False, "comment": "本轮退回"}),
                                   ("cancel", {"reason": "撤回本轮"}), ("rollback", {"comment": "回滚本轮"})]:
            await self.api("POST", f"/finance/fees/{own.id}/submit", json={"amount": 10, "payment_type_id": self.payment_type_id})
            await self.api("POST", f"/finance/fees/{own.id}/{operation}", json=payload)
            data = await self.totals(own)
            self.assertEqual((data["payment_requested_amount"], data["direct_payment_requested_amount"], data["payment_remaining_amount"]), (90, 30, 10))
        other = await self.create_payment(head, own, 10)
        self.assertEqual(other["data"]["amount"], 10)
        self.assertEqual((await self.totals(own))["payment_remaining_amount"], 0)

    async def test_transaction_then_package_uses_actual_paid_sum_and_hides_new_amount_fields(self):
        head, _, _, _, own, _ = await self.setup_sources()
        await self.create_payment(head, own, 60)
        await self.api("POST", f"/finance/fees/{own.id}/submit", json={"amount": 30, "payment_type_id": self.payment_type_id})
        await self.api("POST", f"/finance/fees/{own.id}/review", json={"approved": True})
        await self.api("POST", "/finance/transactions", code=201, json={"finance_record_id": own.id, "transaction_type": "付款", "amount": 20, "transaction_date": str(date.today())})
        # 既有单笔登记后状态是部分付款；本轮剩余10仍可从普通付款入口提交。
        package = await self.api("POST", f"/finance/payment-workflow/{own.id}/submit")
        self.assertEqual(package["data"]["amount"], 10)
        await self.api("POST", f"/finance/payment-workflow/{package['id']}/writeoff",
            data={"paid_date": str(date.today()), "amount": 10, "payment_method": "银行卡", "invoice_no": "RW10-MIX"},
            files={"files": ("voucher.pdf", b"%PDF-RW10", "application/pdf")})
        self.assertEqual((await self.totals(own))["paid_amount"], 30)
        from app.core.contracts import _contract_customer_record_dicts
        async with SessionLocal() as db:
            dto = (await _contract_customer_record_dicts([await db.get(BusinessRecord, own.id)], set(), db))[0]
            self.assertNotIn("payment_request_amount", dto["data"])
            self.assertNotIn("payment_package_amount", dto["data"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
