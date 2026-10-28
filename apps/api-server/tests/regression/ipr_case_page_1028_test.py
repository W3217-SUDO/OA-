"""知识产权案件页（BUG20261028001）：发票文件页签按文档类型关键词筛选；原系统费用明细镜像表不在时返回空。"""

from datetime import date, datetime, timezone
import unittest

import httpx
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database import Base, get_db
from app.areas.ipr import case_files, fees
from app.models import BusinessRecord, FileAttachment
from app.security import current_identity


API = settings.api_prefix
app = FastAPI()
app.include_router(case_files.router)
app.include_router(fees.router)
IDENTITY = {"username": "ipr-case-page-admin", "role": "admin", "display_name": "IPR Case Page Admin", "department": "IPR"}


class IprCasePage1028Test(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with self.sessions() as db:
            now = datetime(2026, 10, 28, 9, 0, tzinfo=timezone.utc)
            case = BusinessRecord(
                module="ipr_case", serial_no="SHPU1810971", title="一种耐火光缆", customer="上海汉欣电线电缆有限公司",
                status="在办", owner=IDENTITY["username"], department="IPR",
                data={"case_kind": "专利", "legacy_ipr_case_id": 5386}, created_at=now, updated_at=now,
            )
            db.add(case)
            await db.flush()
            self.case_id = case.id
            for index, category in enumerate(["转年费收据、手续费发票通知", "受理通知书", "转专利代理费发票通知", "缴费收据"]):
                db.add(FileAttachment(
                    record_id=case.id, category=category, original_name=f"f{index}.pdf", stored_name=f"f{index}.pdf",
                    content_type="application/pdf", size=10, path=f"/tmp/f{index}.pdf", uploader=IDENTITY["username"],
                    document_date=date(2026, 10, 1 + index), created_at=now,
                ))
            await db.commit()
        app.dependency_overrides[get_db] = self.override_db
        app.dependency_overrides[current_identity] = lambda: IDENTITY
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver")

    async def override_db(self):
        async with self.sessions() as db:
            yield db

    async def asyncTearDown(self):
        await self.client.aclose()
        app.dependency_overrides.clear()
        await self.engine.dispose()

    async def test_invoice_tab_filters_files_by_category_keywords(self):
        response = await self.client.get(f"{API}/ipr/cases/{self.case_id}/files", params={"category_keywords": "发票,收据"})
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertEqual(body["total"], 3)
        self.assertNotIn("受理通知书", [item["category"] for item in body["items"]])
        everything = (await self.client.get(f"{API}/ipr/cases/{self.case_id}/files")).json()
        self.assertEqual(everything["total"], 4)

    async def test_legacy_fee_items_are_empty_without_legacy_mirror(self):
        response = await self.client.get(f"{API}/ipr/cases/{self.case_id}/legacy-fee-items")
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json(), {"items": []})
        # 镜像表查询失败只回滚到保存点，同一请求里后续查询照常可用。
        files = await self.client.get(f"{API}/ipr/cases/{self.case_id}/files")
        self.assertEqual(files.status_code, 200)


if __name__ == "__main__":
    unittest.main()
