"""501692/501694（fwl 11-06）：公证书号仓库信息导入收 Excel/CSV，按线索号找到证物更新公证书号、仓库、发票号并关联案件。"""

import io
import unittest

import httpx
from openpyxl import Workbook
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database import Base, get_db
from app.main import app
from app.models import BusinessRecord, User
from app.security import current_identity

API = settings.api_prefix
IDENTITY = {"username": "CODEX-501692", "role": "admin", "role_ids": ["admin"], "department": "测试部"}
HEADER = ["线索号", "调查员", "调查时间", "侵权方式", "店铺名称", "调查地址", "公证书号", "仓库", "发票号", "案号"]


def workbook(rows, title_row=False) -> bytes:
    book = Workbook()
    sheet = book.active
    if title_row:
        sheet.append(["补充取证信息(公证书号,仓库位置,发票号)文件导入"])
    sheet.append(HEADER)
    for row in rows:
        sheet.append(row)
    buffer = io.BytesIO()
    book.save(buffer)
    return buffer.getvalue()


class NotaryStorageImportTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with self.sessions() as db:
            db.add(User(username=IDENTITY["username"], display_name="导入测试", role="admin", role_ids=["admin"],
                        department="测试部", password_hash="unused", is_active=True))
            base = dict(customer="", status="已取证", owner=IDENTITY["username"], department="测试部")
            clue = BusinessRecord(module="clue", serial_no="M26043645", title="线索一", **base)
            many = BusinessRecord(module="clue", serial_no="M26000002", title="线索二", **base)
            case = BusinessRecord(module="case", serial_no="HZMS2600001", title="案件", **base)
            db.add_all([clue, many, case])
            await db.flush()
            self.single = BusinessRecord(module="evidence", serial_no="EV-1", title="证物一", data={"clue_record_id": clue.id, "warehouse": "旧仓"}, **base)
            self.first = BusinessRecord(module="evidence", serial_no="EV-2", title="证物二", data={"clue_no": "M26000002", "certificate_no": "(2026)赣证内字第1号"}, **base)
            self.second = BusinessRecord(module="evidence", serial_no="EV-3", title="证物三", data={"clue_no": "M26000002", "certificate_no": "(2026)赣证内字第2号"}, **base)
            db.add_all([self.single, self.first, self.second])
            await db.commit()
        self.old = dict(app.dependency_overrides)
        app.dependency_overrides[get_db] = self.override_db
        app.dependency_overrides[current_identity] = lambda: IDENTITY
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://notary.test")

    async def override_db(self):
        async with self.sessions() as db:
            yield db

    async def asyncTearDown(self):
        await self.client.aclose()
        app.dependency_overrides.clear()
        app.dependency_overrides.update(self.old)
        await self.engine.dispose()

    async def upload(self, name, content):
        return await self.client.post(f"{API}/investigations/notaries/storage/import", files={"file": (name, content)})

    async def data(self, record):
        async with self.sessions() as db:
            return (await db.get(BusinessRecord, record.id)).data

    async def test_excel_updates_evidence_by_clue_and_certificate(self):
        content = workbook([
            ["M26043645", "苏贵龙", "", "", "", "", "(2026)赣洪江证内字第1009号", "上海一仓", "FP001", "HZMS2600001"],
            ["M26000002", "", "", "", "", "", "(2026)赣证内字第2号", "", "FP002", ""],
            ["M26000002", "", "", "", "", "", "", "上海二仓", "", ""],
            ["M99999999", "", "", "", "", "", "", "上海三仓", "", ""],
        ], title_row=True)
        response = await self.upload("仓库信息.xlsx", content)
        self.assertEqual(response.status_code, 201, response.text)
        body = response.json()
        self.assertEqual((body["updated"], body["failed"]), (2, 2))
        self.assertEqual([item["row"] for item in body["errors"]], [5, 6])
        self.assertIn("有 2 个证物", body["errors"][0]["error"])
        single = await self.data(self.single)
        self.assertEqual((single["certificate_no"], single["warehouse"], single["invoice_no"], single["case_no"]),
                         ("(2026)赣洪江证内字第1009号", "上海一仓", "FP001", "HZMS2600001"))
        self.assertNotIn("investigator", single)  # 调查员等线索信息不写到证物上
        self.assertEqual(single["notarization_no"], "(2026)赣洪江证内字第1009号")  # 页面先读这个键
        self.assertEqual(single["notary_import_fields"], ["certificate_no", "invoice_no", "warehouse"])  # 同步按它保留
        second = await self.data(self.second)
        self.assertEqual((second["invoice_no"], second.get("warehouse")), ("FP002", None))  # 空格子不覆盖
        self.assertNotIn("invoice_no", await self.data(self.first))
        self.assertEqual(second["notary_import_fields"], ["certificate_no", "invoice_no"])  # 空格子不算导入过

    async def test_csv_still_works_and_other_formats_are_refused(self):
        csv_text = ",".join(HEADER) + "\nM26043645,,,,,,,上海四仓,,\n"
        response = await self.upload("仓库信息.csv", csv_text.encode("utf-8-sig"))
        self.assertEqual((response.status_code, response.json()["updated"]), (201, 1), response.text)
        self.assertEqual((await self.data(self.single))["warehouse"], "上海四仓")
        refused = await self.upload("仓库信息.pdf", b"%PDF")
        self.assertEqual(refused.status_code, 422)
        self.assertIn("Excel", refused.json()["detail"])


if __name__ == "__main__":
    unittest.main()
