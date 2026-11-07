"""收文台按上传日期在后端筛（陶威 11-07：公司收文默认当天，却整包取回全所 1 万多份收文，一直“正在加载”）。

后端筛出来的必须和原来“全量取回再按上传日期字符串筛”完全一样；起止要一起给，起不能晚于止。
"""
import unittest
from datetime import datetime, timedelta, timezone

import httpx
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database import Base, get_db
from app.main import app
from app.models import BusinessRecord, FileAttachment, User
from app.security import current_identity

API = settings.api_prefix
CHINA = timezone(timedelta(hours=8))
IDENTITY = {"username": "CODEX-1107-receipts", "role": "admin", "role_ids": ["admin"], "department": "测试部"}


class ReceiptUploadRangeTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with self.sessions() as db:
            db.add(User(username=IDENTITY["username"], display_name="收文测试", role="admin", role_ids=["admin"],
                        department="测试部", password_hash="unused", is_active=True))
            case = BusinessRecord(module="case", serial_no="HZMS-1107", title="案件", status="提交立案", owner=IDENTITY["username"],
                                  department="测试部", customer="甲公司", description="", data={"plaintiff": "甲公司", "opponent": "乙公司"})
            db.add(case)
            await db.flush()
            # 案件附件：前一天深夜、当天零点后、当天深夜、次日零点（北京时间）
            for name, when in (("前一天_传票.pdf", datetime(2026, 11, 6, 23, 30, tzinfo=CHINA)),
                               ("当天凌晨_传票.pdf", datetime(2026, 11, 7, 0, 10, tzinfo=CHINA)),
                               ("当天深夜_判决书.pdf", datetime(2026, 11, 7, 23, 59, tzinfo=CHINA)),
                               ("次日零点_裁定书.pdf", datetime(2026, 11, 8, 0, 0, tzinfo=CHINA)),
                               ("不是收文_合同.pdf", datetime(2026, 11, 7, 10, 0, tzinfo=CHINA))):
                db.add(FileAttachment(record_id=case.id, category="案件文档", original_name=name, stored_name=name, path=name, content_type="application/pdf",
                                      size=10, uploader=IDENTITY["username"], created_at=when))
            # 官方收文：上传日期写在收文记录上
            for name, uploaded in (("官文当天_通知书.pdf", "2026-11-07"), ("官文前天_通知书.pdf", "2026-11-05")):
                attachment = FileAttachment(record_id=case.id, category="官方收文", original_name=name, stored_name=name, path=name,
                                            content_type="application/pdf", size=10, uploader=IDENTITY["username"],
                                            created_at=datetime(2026, 11, 7, 9, 0, tzinfo=CHINA))
                db.add(attachment)
                await db.flush()
                db.add(BusinessRecord(module="document", serial_no=f"SW-{attachment.id}", title=name, status="已签收", owner=IDENTITY["username"],
                                      department="测试部", customer="", description="",
                                      data={"direction": "收文", "attachment_id": attachment.id, "uploaded_at": uploaded}))
            await db.commit()
        self.old_overrides = dict(app.dependency_overrides)
        app.dependency_overrides[get_db] = self.override_db
        app.dependency_overrides[current_identity] = lambda: IDENTITY
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://receipts.test")

    async def asyncTearDown(self):
        await self.client.aclose()
        app.dependency_overrides.clear()
        app.dependency_overrides.update(self.old_overrides)
        await self.engine.dispose()

    async def override_db(self):
        async with self.sessions() as db:
            yield db

    async def listing(self, scope, **params):
        response = await self.client.get(f"{API}/documents/receipts", params={"scope": scope, **params})
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    async def test_range_matches_full_listing_filtered_by_upload_day(self):
        for scope in ("company", "mine", "official"):
            full = await self.listing(scope)
            for start, end in (("2026-11-07", "2026-11-07"), ("2026-11-06", "2026-11-07"), ("2026-11-08", "2026-11-08"), ("2020-01-01", "2026-12-31")):
                ranged = await self.listing(scope, uploaded_from=start, uploaded_to=end)
                expected = [row for row in full["items"] if start <= str(row["data"].get("uploaded_at") or "") <= end]
                self.assertEqual(ranged["items"], expected, f"{scope} {start}~{end}")
                self.assertEqual(ranged["total"], len(expected))
                kept = {row["data"].get("attachment_id") for row in expected}
                self.assertEqual(sorted(item["id"] for item in ranged["attachments"]), sorted(kept))

    async def test_today_only_returns_that_day(self):
        names = sorted(row["title"] for row in (await self.listing("company", uploaded_from="2026-11-07", uploaded_to="2026-11-07"))["items"])
        self.assertEqual(names, ["官文当天_通知书.pdf", "当天凌晨_传票.pdf", "当天深夜_判决书.pdf"])

    async def test_range_needs_both_ends_in_order(self):
        for params in ({"uploaded_from": "2026-11-07"}, {"uploaded_to": "2026-11-07"}, {"uploaded_from": "2026-11-08", "uploaded_to": "2026-11-07"}):
            response = await self.client.get(f"{API}/documents/receipts", params={"scope": "company", **params})
            self.assertEqual(response.status_code, 422, params)


if __name__ == "__main__":
    unittest.main()
