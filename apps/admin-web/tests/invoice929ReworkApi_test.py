"""第9行返工：外部隔离数据库、真实合同维护与开票入口。"""
import unittest

import finance929Regression_test as fixture
from sqlalchemy import func, select
from app.database import SessionLocal
from app.models import BusinessRecord, JobRole, User, WorkflowEvent

fixture.PREFIX = "CODEX-929-RW09-"
PREFIX = fixture.PREFIX


class Invoice929Rework(fixture.Finance929Regression):
    async def new_sources(self):
        customer = await self.record("customer")
        async with SessionLocal() as db:
            source = await db.get(BusinessRecord, customer.id)
            source.title = customer.customer
            await db.commit()
        customer.title = customer.customer
        contract = (await self.api("POST", "/contracts", code=201, json={
            "title": PREFIX + "可选外部号合同", "customer": customer.title,
            "owner": PREFIX + "admin", "department": "回归测试部",
            "data": {"contract_body": "律所", "external_contract_numbers": [], "customer_id": customer.id},
        })).json()
        case = await self.record("case", status="一审阶段", data={"case_creation_step": "completed",
            "contract_id": contract["id"], "contract_no": contract["serial_no"], "case_type": "民事",
            "external_contract_no": "OLD-CASE", "case_team_usernames": [PREFIX + "admin"]})
        fee = await self.record("finance", data={"case_id": case.id, "case_no": case.serial_no, "case_type": "民事",
            "contract_id": contract["id"], "contract_no": contract["serial_no"], "expense_scope": "律所",
            "fee_type": "官方费用", "amount": 100, "invoice_amount": 0})
        async with SessionLocal() as db:
            return await db.get(BusinessRecord, contract["id"]), case, fee

    async def change_number(self, contract, number):
        return (await self.api("POST", f"/contracts/{contract.id}/changes", code=201, json={
            "change_type": "合同补充/修订", "reason": PREFIX + "补充外部合同号",
            "external_contract_numbers": [number] if number else [],
        })).json()

    async def context(self, contract, selected, **params):
        return (await self.api("GET", "/finance/invoice-context", params={
            "customer": contract.customer, "selected_fee_ids": ",".join(str(fee.id) for fee in selected), **params,
        })).json()

    async def test_rw09_optional_contract_change_and_two_applications(self):
        contract, case, fee = await self.new_sources()
        self.assertTrue(contract.serial_no.startswith("SH"))
        self.assertEqual(contract.data["external_contract_numbers"], [])
        second = await self.record("finance", data=dict(fee.data))
        blocked = self.invoice_body(contract, case, [fee])
        blocked["external_contract_no"] = "FORGED"
        await self.api("POST", "/finance/invoices", code=409, json=blocked)
        async with SessionLocal() as db:
            self.assertEqual(await db.scalar(select(func.count()).select_from(BusinessRecord).where(BusinessRecord.module == "invoice")), 0)
        await self.change_number(contract, "CURRENT-13156")
        fresh = (await self.api("GET", f"/records/{contract.id}")).json()
        self.assertEqual(fresh["data"]["external_contract_no"], "CURRENT-13156")
        context = await self.context(contract, [fee, second], page_size=1)
        self.assertEqual(len(context["items"]), 1)
        self.assertEqual({row["id"] for row in context["selected_items"]}, {fee.id, second.id})
        self.assertTrue(all(row["data"]["external_contract_no"] == "CURRENT-13156" for row in context["selected_items"]))
        for source in (fee, second):
            created = (await self.api("POST", "/finance/invoices", code=201, json=self.invoice_body(contract, case, [source]))).json()
            self.assertEqual(created["data"]["external_contract_no"], "CURRENT-13156")
            loaded = (await self.api("GET", f"/finance/invoices/{created['id']}")).json()
            self.assertEqual(loaded["data"]["invoice_objects"][0]["external_contract_no"], "CURRENT-13156")
        async with SessionLocal() as db:
            self.assertGreater(await db.scalar(select(func.count()).select_from(WorkflowEvent).where(WorkflowEvent.record_id == contract.id)), 1)

    async def test_rw09_old_draft_patch_submit_and_history_unchanged(self):
        contract, case, fee = await self.new_sources()
        await self.change_number(contract, "FIRST")
        body = self.invoice_body(contract, case, [fee])
        created = (await self.api("POST", "/finance/invoices", code=201, json=body)).json()
        history = await self.record("invoice", status="已开票", data={"external_contract_no": "HISTORICAL"})
        await self.change_number(contract, "SECOND")
        detail = (await self.api("GET", f"/finance/invoices/{created['id']}")).json()
        self.assertEqual(detail["data"]["external_contract_no"], "FIRST")
        context = await self.context(contract, [fee], invoice_id=created["id"])
        self.assertEqual(context["selected_items"][0]["data"]["external_contract_no"], "SECOND")
        updated = (await self.api("PATCH", f"/finance/invoices/{created['id']}", json={**body, "external_contract_no": "FORGED"})).json()
        self.assertEqual(updated["data"]["external_contract_no"], "SECOND")
        await self.change_number(contract, "THIRD")
        submitted = (await self.api("POST", f"/finance/invoices/{created['id']}/submit", json={"comment": "重读合同"})).json()
        self.assertEqual(submitted["data"]["external_contract_no"], "THIRD")
        async with SessionLocal() as db:
            self.assertEqual((await db.get(BusinessRecord, created["id"])).data["external_contract_no"], "THIRD")
            self.assertEqual((await db.get(BusinessRecord, history.id)).data["external_contract_no"], "HISTORICAL")

    async def test_rw09_clear_failure_non_sh_and_permissions(self):
        contract, case, fee = await self.new_sources()
        await self.change_number(contract, "FIRST")
        body = self.invoice_body(contract, case, [fee])
        created = (await self.api("POST", "/finance/invoices", code=201, json=body)).json()
        await self.change_number(contract, "")
        await self.api("PATCH", f"/finance/invoices/{created['id']}", code=409, json={**body, "external_contract_no": "FORGED"})
        await self.api("POST", f"/finance/invoices/{created['id']}/submit", code=409, json={"comment": "空号应阻断"})
        async with SessionLocal() as db:
            self.assertEqual((await db.get(BusinessRecord, created["id"])).status, "草稿")
        self.actor("viewer")
        await self.api("POST", f"/contracts/{contract.id}/changes", code=404, json={"change_type": "合同补充/修订", "reason": "无权变更", "external_contract_numbers": ["BAD"]})
        async with SessionLocal() as db:
            db.add(JobRole(code=PREFIX + "no-invoice", name=PREFIX + "仅案件", permissions=["case-mine"],
                field_keys=list(fixture.FIELD_KEYS), field_keys_configured=True, data_scope="本人及共享数据"))
            db.add(User(username=PREFIX + "no-invoice", display_name="无开票权限", role="user",
                profile={"permission_role_code": PREFIX + "no-invoice"}, department="独立部门", password_hash="not-a-login-password", is_active=True))
            await db.commit()
        self.actor("no-invoice")
        await self.api("GET", "/finance/invoice-context", code=403, params={"customer": contract.customer, "selected_fee_ids": fee.id})
        self.actor("admin")
        await self.api("GET", "/finance/invoice-context", code=403, params={"customer": "OTHER-CUSTOMER", "selected_fee_ids": fee.id})
        await self.api("GET", "/finance/invoice-context", code=422, params={"customer": contract.customer, "selected_fee_ids": "-1"})
        async with SessionLocal() as db:
            current = await db.get(BusinessRecord, contract.id)
            current.serial_no = "OTHER-" + PREFIX
            fee_row = await db.get(BusinessRecord, fee.id)
            fee_row.data = {**fee_row.data, "contract_no": current.serial_no}
            await db.commit()
        submitted = (await self.api("POST", f"/finance/invoices/{created['id']}/submit", json={"comment": "非SH例外"})).json()
        self.assertEqual(submitted["status"], "待审批")
        self.assertEqual(submitted["data"]["external_contract_no"], "")


if __name__ == "__main__":
    suite = unittest.TestSuite(Invoice929Rework(name) for name in dir(Invoice929Rework) if name.startswith("test_rw09_"))
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    raise SystemExit(not result.wasSuccessful())
