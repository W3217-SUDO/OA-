"""BUG20261028008（范明明 2026-10-29）：银行流水（表格）上传后先预览，点“确认导入”才写入回款。"""
import io
import unittest

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool
from starlette.datastructures import UploadFile

from app.areas.finance.incoming_payments import import_incoming_payments
from app.data_models.finance import IncomingPayment
from app.database import Base
from app.models import User

IDENTITY = {"username": "CODEX008", "display_name": "财务", "role": "admin", "role_ids": ["admin"], "department": "", "_finance_scope": "firm"}
CSV = "对方户名,银行流水号,到账日期,到账金额,摘要\n甲公司,CODEX008-A,2026-10-20,825.00,核定成本\n乙公司,CODEX008-B,2026-10-21,1021.50,代理费\n"


def upload(text):
    return UploadFile(file=io.BytesIO(text.encode("utf-8")), filename="流水.csv")


class BankImportConfirmTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.sessions() as db:
            db.add(User(username=IDENTITY["username"], display_name="财务", password_hash="isolated-only", role="admin"))
            await db.commit()

    async def asyncTearDown(self):
        await self.engine.dispose()

    async def count(self):
        async with self.sessions() as db:
            return await db.scalar(select(func.count()).select_from(IncomingPayment))

    async def call(self, **kwargs):
        async with self.sessions() as db:
            return await import_incoming_payments(bank_source="boc", identity=IDENTITY, db=db,
                                                  **{"file": None, "confirmed_rows": "", "confirmation_token": "", **kwargs})

    async def test_spreadsheet_previews_then_imports_on_confirm(self):
        preview = await self.call(file=upload(CSV))
        self.assertTrue(preview["requires_confirmation"])
        self.assertTrue(preview["confirm_with_file"])
        self.assertEqual((preview["valid_count"], len(preview["items"])), (2, 2))
        self.assertIsNone(preview["rows"])
        self.assertEqual(await self.count(), 0, "预览时不写入回款")
        result = await self.call(file=upload(CSV), confirmation_token=preview["confirmation_token"])
        self.assertEqual(result["created"], 2)
        self.assertEqual(await self.count(), 2)

    async def test_changed_file_is_rejected_on_confirm(self):
        preview = await self.call(file=upload(CSV))
        changed = CSV.replace("1021.50", "9021.50")
        with self.assertRaises(HTTPException) as caught:
            await self.call(file=upload(changed), confirmation_token=preview["confirmation_token"])
        self.assertEqual(caught.exception.status_code, 422)
        self.assertEqual(await self.count(), 0)


if __name__ == "__main__":
    unittest.main()
