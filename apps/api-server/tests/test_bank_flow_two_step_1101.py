"""陶国南 11-01 定：银行流水和旧系统一样两步——上传只写流水，勾选后再生成到账单。"""
import unittest

import httpx
from fastapi import FastAPI
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.areas.finance import bank_flows, incoming_payments
from app.core import soft_delete
from app.core.dependencies import get_db
from app.database import Base
from app.models import BankStatementLine, IncomingPayment, User
from app.security import current_identity

ADMIN = {"username": "fadmin", "role": "admin", "role_ids": ["admin"], "_actual_role_ids": ["admin"],
         "display_name": "管理员", "department": "财务部", "action_keys": ["*"]}
API = "/api/v1"
CSV = "对方户名,银行流水号,到账日期,到账金额\n甲公司,BF-1,2026-10-30,100\n乙公司,BF-2,2026-10-31,250.5\n".encode("utf-8-sig")


class BankFlowTwoStepTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        soft_delete.set_actor(ADMIN["username"])
        async with self.sessions() as db:
            db.add(User(username="fadmin", display_name="管理员", password_hash="x", department="财务部", role="admin"))
            await db.commit()
        app = FastAPI()
        app.include_router(incoming_payments.router)
        app.include_router(bank_flows.router)

        async def session():
            async with self.sessions() as db:
                yield db
        app.dependency_overrides[get_db] = session
        app.dependency_overrides[current_identity] = lambda: dict(ADMIN)
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://isolated")

    async def asyncTearDown(self):
        await self.client.aclose()
        await self.engine.dispose()

    async def _upload(self, scope="firm"):
        params = {"finance_scope": scope}
        preview = await self.client.post(f"{API}/finance/incoming-payments/import", params=params,
                                         files={"file": ("bank.csv", CSV, "text/csv")}, data={"bank_source": "icbc"})
        self.assertEqual(preview.status_code, 200, preview.text)
        self.assertTrue(preview.json()["requires_confirmation"])
        return await self.client.post(f"{API}/finance/incoming-payments/import", params=params,
                                      files={"file": ("bank.csv", CSV, "text/csv")},
                                      data={"bank_source": "icbc", "confirmation_token": preview.json()["confirmation_token"]})

    async def _lines(self, scope="firm", **params):
        response = await self.client.get(f"{API}/finance/bank-flows/lines", params={"finance_scope": scope, **params})
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    async def test_upload_writes_flows_not_receipts(self):
        confirmed = await self._upload()
        self.assertEqual(confirmed.status_code, 200, confirmed.text)
        self.assertEqual((confirmed.json()["created"], confirmed.json()["target"]), (2, "bank_flows"))
        async with self.sessions() as db:
            self.assertEqual((await db.scalars(select(IncomingPayment))).all(), [])
        listed = await self._lines()
        self.assertEqual((listed["total"], listed["amount"]), (2, 350.5))
        row = next(item for item in listed["items"] if item["bank_reference"] == "BF-1")
        self.assertEqual((row["status"], row["group"], row["bank_label"], row["file_name"]), ("未导入", "律所", "工行", "bank.csv"))
        # 同一文件再传：两条都已在流水里，不重复写
        again = await self._upload()
        self.assertEqual(again.json()["created"], 0)
        self.assertEqual(len(again.json()["errors"]), 2)
        # 平台中心看不到律所上传的流水
        self.assertEqual((await self._lines("platform"))["total"], 0)

    async def test_generate_receipts_then_lines_are_imported(self):
        await self._upload()
        ids = [item["id"] for item in (await self._lines())["items"]]
        generated = await self.client.post(f"{API}/finance/bank-flows/generate", params={"finance_scope": "firm"}, json={"ids": ids})
        self.assertEqual(generated.status_code, 200, generated.text)
        self.assertEqual(generated.json()["created"], 2)
        async with self.sessions() as db:
            payments = (await db.scalars(select(IncomingPayment).order_by(IncomingPayment.bank_reference))).all()
            self.assertEqual([(p.bank_reference, p.amount, p.status, p.finance_scope, p.source_kind, p.bank_source) for p in payments],
                             [("BF-1", 100.0, "待认领", "firm", "bank_import", "工行"), ("BF-2", 250.5, "待认领", "firm", "bank_import", "工行")])
            lines = (await db.scalars(select(BankStatementLine))).all()
            self.assertTrue(all(line.status == "已导入" and line.incoming_payment_id and line.receipt_no for line in lines))
        self.assertEqual((await self._lines())["total"], 0)
        self.assertEqual((await self._lines(status="已导入"))["total"], 2)
        # 已导入的不能再生成，也不能删
        again = await self.client.post(f"{API}/finance/bank-flows/generate", params={"finance_scope": "firm"}, json={"ids": ids[:1]})
        self.assertEqual(again.status_code, 409)
        deleted = await self.client.post(f"{API}/finance/bank-flows/delete", params={"finance_scope": "firm"}, json={"ids": ids[:1]})
        self.assertEqual(deleted.status_code, 409)

    async def test_generate_is_all_or_nothing_and_scope_checked(self):
        await self._upload()
        ids = [item["id"] for item in (await self._lines())["items"]]
        async with self.sessions() as db:
            db.add(IncomingPayment(source_kind="manual", receipt_no="HK-X", received_date=__import__("datetime").date(2026, 10, 31),
                                   amount=250.5, payer_name="乙公司", bank_reference="BF-2", status="待认领", operator="x"))
            await db.commit()
        failed = await self.client.post(f"{API}/finance/bank-flows/generate", params={"finance_scope": "firm"}, json={"ids": ids})
        self.assertEqual(failed.status_code, 409)
        self.assertIn("BF-2", failed.json()["detail"])
        async with self.sessions() as db:
            self.assertEqual(len((await db.scalars(select(IncomingPayment))).all()), 1)
            self.assertTrue(all(line.status == "未导入" for line in (await db.scalars(select(BankStatementLine))).all()))
        other_center = await self.client.post(f"{API}/finance/bank-flows/generate", params={"finance_scope": "platform"}, json={"ids": ids})
        self.assertEqual(other_center.status_code, 409)

    async def test_delete_is_logical(self):
        await self._upload()
        first = (await self._lines())["items"][0]
        deleted = await self.client.post(f"{API}/finance/bank-flows/delete", params={"finance_scope": "firm"}, json={"ids": [first["id"]]})
        self.assertEqual(deleted.status_code, 200, deleted.text)
        self.assertEqual((await self._lines())["total"], 1)
        trash = await self._lines(status="已删除")
        self.assertEqual([(item["id"], item["status"]) for item in trash["items"]], [(first["id"], "已删除")])
        async with self.sessions() as db:
            row = await db.scalar(select(BankStatementLine).where(BankStatementLine.id == first["id"]).execution_options(include_deleted=True))
            self.assertIsNotNone(row.deleted_at)

    async def test_payer_account_is_parsed_and_filterable(self):
        csv = "对方户名,对方账号,银行流水号,到账日期,到账金额\n丙公司,6222 0000 1111,BF-9,2026-10-30,66\n".encode("utf-8-sig")
        params = {"finance_scope": "firm"}
        files = {"file": ("acc.csv", csv, "text/csv")}
        preview = await self.client.post(f"{API}/finance/incoming-payments/import", params=params, files=files, data={"bank_source": "boc"})
        self.assertEqual(preview.json()["items"][0]["payer_account"], "6222 0000 1111")
        await self.client.post(f"{API}/finance/incoming-payments/import", params=params, files=files,
                               data={"bank_source": "boc", "confirmation_token": preview.json()["confirmation_token"]})
        found = await self._lines(payer_account="0000 1111")
        self.assertEqual([(item["payer_name"], item["payer_account"]) for item in found["items"]], [("丙公司", "6222 0000 1111")])
        generated = await self.client.post(f"{API}/finance/bank-flows/generate", params=params, json={"ids": [found["items"][0]["id"]]})
        self.assertEqual(generated.status_code, 200, generated.text)
        async with self.sessions() as db:
            payment = await db.scalar(select(IncomingPayment).where(IncomingPayment.bank_reference == "BF-9"))
            self.assertIn("对方账号 6222 0000 1111", payment.remark)

    def test_export_template_reads_account_by_header_name(self):
        import io
        from openpyxl import Workbook
        from app.core.bank_statement_import import read_statement
        book = Workbook()
        sheet = book.active
        header = [""] * 21
        for index, label in {0: "账号", 3: "交易日", 7: "借方金额", 8: "贷方金额", 11: "流水号", 18: "收(付)方账号", 19: "收(付)方名称"}.items():
            header[index] = label
        sheet.append(["招商银行交易查询"])
        sheet.append(header)
        row = [""] * 21
        row[0], row[3], row[7], row[8], row[11], row[18], row[19] = "本方1", "2026-10-30", "", "500", "CMB-1", "6214 8888", "丁公司"
        sheet.append(row)
        buffer = io.BytesIO()
        book.save(buffer)
        rows = read_statement(buffer.getvalue(), "cmb.xlsx", "cmb")
        self.assertEqual([(item[2]["payer_name"], item[2]["payer_account"]) for item in rows], [("丁公司", "6214 8888")])


if __name__ == "__main__":
    unittest.main()
