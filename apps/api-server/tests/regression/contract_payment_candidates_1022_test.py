"""10.22 第2行：合同付款候选不再列出已申请满（待付为 0）的费用。

只用一次性内存 SQLite，测试数据前缀 CODEX-1022-2-。
"""
import os
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"

import unittest
from datetime import date

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.areas.contract import router as routes
from app.core.dependencies import current_identity
from app.database import Base, get_db
from app.models import BusinessRecord, SystemParameter, User
from app.models_shared import ContractPaymentApplicationInput, ContractPaymentReviewInput

ADMIN = {"username": "admin", "role": "admin", "department": "CODEX-1022-2"}


class ContractPaymentCandidatesRow2Test(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.db = async_sessionmaker(self.engine, expire_on_commit=False)()
        self.db.add(User(username="admin", password_hash="isolated-not-a-login", department="CODEX-1022-2"))
        self.contract = self.record("contract", "CONTRACT", data={"contract_body": "律所"})
        self.case = self.record("case", "CASE", status="在办", data={"stage": "一审"})
        self.payment_type = SystemParameter(category="payment_type", code="CODEX-1022-2-TYPE", name="CODEX-1022-2-PAYEE",
            extra={"nature": "案件付款", "payee": "CODEX-1022-2-PAYEE", "account_bank": "CODEX-BANK", "account": "CODEX-ACCOUNT"},
            is_active=True, created_by="admin", updated_by="admin")
        self.db.add(self.payment_type)
        await self.db.flush()
        source = {"case_id": self.case.id, "case_no": self.case.serial_no,
                  "contract_id": self.contract.id, "contract_no": self.contract.serial_no}
        self.court = self.record("finance", "COURT", data={**source, "fee_type": "官方费用", "expense_subtype": "一审诉讼费", "amount": 100})
        self.search = self.record("finance", "SEARCH", data={**source, "fee_type": "其他费用", "expense_subtype": "检索费", "amount": 1})
        self.agency = self.record("finance", "AGENCY", data={**source, "fee_type": "代理费", "fee_type_name": "律师代理费", "amount": 1000})
        await self.db.commit()
        app = FastAPI()
        app.include_router(routes.router)
        app.dependency_overrides[current_identity] = lambda: ADMIN

        async def isolated_db():
            try:
                yield self.db
            except Exception:
                await self.db.rollback()
                raise
        app.dependency_overrides[get_db] = isolated_db
        self.client = AsyncClient(transport=ASGITransport(app=app), base_url="http://isolated")

    async def asyncTearDown(self):
        await self.client.aclose()
        await self.db.close()
        await self.engine.dispose()

    def record(self, module, suffix, status="草稿", data=None):
        record = BusinessRecord(module=module, serial_no=f"CODEX-1022-2-{suffix}", title=f"CODEX-1022-2-{suffix}",
            customer="CODEX-1022-2-CUSTOMER", status=status, owner="admin", department="CODEX-1022-2", data=data or {})
        self.db.add(record)
        return record

    def body(self, *lines):
        return ContractPaymentApplicationInput(payment_type_id=self.payment_type.id, application_date=date(2026, 10, 22),
            remark="CODEX-1022-2", lines=[{"case_fee_id": fee.id, "amount": amount, "remark": ""} for fee, amount in lines])

    async def create(self, *lines):
        response = await self.client.post(f"/api/v1/contracts/{self.contract.id}/payment-applications",
            json=self.body(*lines).model_dump(mode="json"))
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()

    async def candidates(self):
        response = await self.client.get(f"/api/v1/contracts/{self.contract.id}/payment-candidates")
        self.assertEqual(response.status_code, 200, response.text)
        return {row["case_fee_id"]: row for row in response.json()["items"]}

    async def test_fully_applied_fees_hidden_partial_kept_and_rejection_restores(self):
        self.assertEqual(set(await self.candidates()), {self.court.id, self.search.id, self.agency.id})
        payment = await self.create((self.court, 100), (self.search, 1), (self.agency, 400))
        rows = await self.candidates()
        # 全额申请的一审诉讼费、检索费不再出现；部分申请的律师代理费显示剩余待付。
        self.assertEqual(set(rows), {self.agency.id})
        self.assertEqual(rows[self.agency.id]["remaining_amount"], 600)
        self.assertTrue(all(row["remaining_amount"] > 0 for row in rows.values()))
        # 已占满的费用直接提交仍被拒绝，不产生新请款单。
        blocked = await self.client.post(f"/api/v1/contracts/{self.contract.id}/payment-applications",
            json=self.body((self.court, 1)).model_dump(mode="json"))
        self.assertEqual(blocked.status_code, 422, blocked.text)
        # 驳回释放占额后重新出现。
        await routes.review_contract_payment_application(payment["id"], ContractPaymentReviewInput(approved=False, comment="CODEX-1022-2 驳回"), ADMIN, self.db)
        rows = await self.candidates()
        self.assertEqual(set(rows), {self.court.id, self.search.id, self.agency.id})
        self.assertEqual(rows[self.court.id]["remaining_amount"], 100)

    async def test_edit_context_keeps_own_lines_even_when_balance_is_zero(self):
        original = await self.create((self.court, 100), (self.search, 1))
        await routes.review_contract_payment_application(original["id"], ContractPaymentReviewInput(approved=False, comment="CODEX-1022-2 驳回"), ADMIN, self.db)
        # 另一张单占满一审诉讼费。
        await self.create((self.court, 100))
        context = await self.client.get(f"/api/v1/contract-payment-applications/{original['id']}/edit-context")
        self.assertEqual(context.status_code, 200, context.text)
        items = {row["case_fee_id"]: row for row in context.json()["items"]}
        # 本单明细里的费用都保留（即使被他单占满，余额为 0）。
        self.assertIn(self.court.id, items)
        self.assertEqual(items[self.court.id]["remaining_amount"], 0)
        self.assertIn(self.search.id, items)
        self.assertIn(self.agency.id, items)
        # 新建入口仍隐藏被占满的费用。
        self.assertNotIn(self.court.id, await self.candidates())
        # 只改未被占满的检索费可以保存。
        saved = await self.client.put(f"/api/v1/contract-payment-applications/{original['id']}",
            json=self.body((self.search, 1)).model_dump(mode="json"))
        self.assertEqual(saved.status_code, 200, saved.text)

    async def test_active_own_payment_edit_context_keeps_fully_reserved_line(self):
        # 本单为有效状态时扣回本单占额，本单费用不因自身占满而消失。
        payment = await self.create((self.court, 100))
        record = await self.db.get(BusinessRecord, payment["id"])
        from app.core.contract_payment_lifecycle import visible_payment_candidates
        rows = {row["case_fee_id"]: row for row in await visible_payment_candidates(self.contract, ADMIN, self.db, record)}
        self.assertEqual(rows[self.court.id]["remaining_amount"], 100)
        self.assertNotIn(self.court.id, await self.candidates())


if __name__ == "__main__":
    unittest.main()
