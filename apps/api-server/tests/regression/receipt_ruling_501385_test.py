"""501385（范文玲 11-04）：公司收文、我的收文按文件名识别案件里的法院收文，补上“裁定书”和旧系统一致；调解书等不计入。"""
import unittest
from unittest.mock import patch

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.areas.aws import receipt_sources
from app.database import Base
from app.models import BusinessRecord, FileAttachment

ADMIN = {"username": "fwl", "role": "admin", "role_ids": ["admin"], "_actual_role_ids": ["admin"]}


class ReceiptRulingTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        async with self.sessions() as db:
            case = BusinessRecord(module="case", serial_no="HZMS2600001", title="测试案件", status="在办", owner="fwl", data={})
            db.add(case)
            await db.flush()
            for name in ("（2026）沪0110民初1号民事裁定书.pdf", "（2026）沪0110民初1号民事判决书.pdf", "（2026）沪0110民初1号民事调解书.pdf", "起诉状.pdf"):
                db.add(FileAttachment(record_id=case.id, category="案件文档", original_name=name, stored_name=name, size=1, path=name, uploader="fwl"))
            await db.commit()

    async def asyncTearDown(self):
        await self.engine.dispose()

    async def names(self, scope):
        async def allow(*args):
            return None
        async with self.sessions() as db:
            with patch.object(receipt_sources, "_require_receipt_menu", allow):
                result = await receipt_sources.list_receipts(scope=scope, identity=ADMIN, db=db)
        return {row["title"] for row in result["items"]}

    async def test_ruling_counts_as_receipt(self):
        names = await self.names("company")
        self.assertIn("（2026）沪0110民初1号民事裁定书.pdf", names)
        self.assertIn("（2026）沪0110民初1号民事判决书.pdf", names)
        self.assertNotIn("（2026）沪0110民初1号民事调解书.pdf", names, "调解书不计入（范文玲 15:22）")
        self.assertNotIn("起诉状.pdf", names)
        self.assertIn("（2026）沪0110民初1号民事裁定书.pdf", await self.names("mine"), "我的收文同一规则")


if __name__ == "__main__":
    unittest.main()
