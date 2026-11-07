"""公证书号仓库信息导入收 Excel 和 CSV（范文玲 11-06，501692/501694）：按线索号或公证书号更新已有公证记录，规则和原 CSV 一样。"""
import io
import unittest
from datetime import datetime

import httpx
from openpyxl import Workbook
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.core.data_scope_gate import reset_gate_cache
from app.database import Base, get_db
from app.main import app
from app.models import BusinessRecord, User
from app.security import create_token, hash_password

API = settings.api_prefix
HEADER = ["线索号", "调查员", "调查时间", "侵权方式", "店铺名称", "调查地址", "公证书号", "仓库", "发票号", "案号"]


class NotaryStorageExcelImportTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        reset_gate_cache()
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with self.sessions() as db:
            db.add(User(username="boss", display_name="管理员", department="调查部", role="admin", role_ids=["admin"], is_active=True,
                        password_hash=hash_password("FakeRev#12345678"), profile={}))
            db.add_all([
                BusinessRecord(module="notary", serial_no="GZ1", title="公证一", status="等待材料", owner="boss", department="调查部",
                               customer="", description="", data={"clue_no": "XS1001"}),
                BusinessRecord(module="notary", serial_no="GZ2", title="公证二", status="等待材料", owner="boss", department="调查部",
                               customer="", description="", data={"certificate_no": "(2026)沪证字9号"}),
            ])
            await db.commit()

        async def override_db():
            async with self.sessions() as db:
                yield db
        self.previous = dict(app.dependency_overrides)
        app.dependency_overrides[get_db] = override_db
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t")
        self.headers = {"Authorization": "Bearer " + create_token("boss", "admin", 30)}

    async def asyncTearDown(self):
        await self.client.aclose()
        app.dependency_overrides.clear()
        app.dependency_overrides.update(self.previous)
        await self.engine.dispose()
        reset_gate_cache()

    async def upload(self, name, content, mime):
        return await self.client.post(f"{API}/investigations/notaries/storage/import", headers=self.headers,
                                      files={"file": (name, content, mime)})

    async def notary(self, serial):
        async with self.sessions() as db:
            return await db.scalar(select(BusinessRecord).where(BusinessRecord.serial_no == serial))

    async def test_xlsx_updates_by_clue_and_certificate(self):
        book = Workbook(); sheet = book.active
        sheet.append(["", ""])  # 表头前的空行跳过
        sheet.append(HEADER)
        sheet.append(["XS1001", "张三", datetime(2026, 11, 6), "线上", "某店", "上海", "(2026)沪证字1号", "A-01", 12345678, ""])
        sheet.append([None] * 10)  # 中间空行跳过
        sheet.append(["", "李四", "", "", "", "", "(2026)沪证字9号", "B-02", "", ""])
        sheet.append(["XS9999", "", "", "", "", "", "", "C", "", ""])
        buffer = io.BytesIO(); book.save(buffer)
        response = await self.upload("取证信息.xlsx", buffer.getvalue(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        self.assertEqual(response.status_code, 201, response.text)
        body = response.json()
        self.assertEqual(body["updated"], 2)
        self.assertEqual(body["failed"], 1)
        self.assertEqual(body["errors"][0]["row"], 6)  # Excel 行号
        first = await self.notary("GZ1")
        self.assertEqual(first.data["certificate_no"], "(2026)沪证字1号")
        self.assertEqual(first.data["warehouse"], "A-01")
        self.assertEqual(first.data["invoice_no"], "12345678")  # 数字不带 .0
        self.assertEqual(first.data["investigated_at"], "2026-11-06")  # 日期不带时间
        second = await self.notary("GZ2")
        self.assertEqual(second.data["warehouse"], "B-02")

    async def test_csv_still_works(self):
        content = ("﻿" + ",".join(HEADER) + "\r\nXS1001,,,,,,,D-09,,\r\n").encode("utf-8")
        response = await self.upload("取证信息.csv", content, "text/csv")
        self.assertEqual(response.status_code, 201, response.text)
        self.assertEqual(response.json()["updated"], 1)
        self.assertEqual((await self.notary("GZ1")).data["warehouse"], "D-09")

    async def test_other_files_rejected(self):
        response = await self.upload("取证信息.txt", b"x", "text/plain")
        self.assertEqual(response.status_code, 422)
        broken = await self.upload("取证信息.xlsx", b"not a workbook", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        self.assertEqual(broken.status_code, 422, broken.text)


if __name__ == "__main__":
    unittest.main()
