"""知识产权案件页“修改/保存”（BUG20261028001，陶国南 2026-10-28 确认）：迁移案件也能改，写回案件页读取的字段并记系统日志。"""

from datetime import datetime, timezone
import unittest

import httpx
from fastapi import FastAPI
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.areas.ipr import case_files, case_info, reminders
from app.areas.ipr.router import create_ipr_case_log
from app.config import settings
from app.database import Base, get_db
from app.models import BusinessRecord, WorkflowEvent
from app.security import current_identity

API = settings.api_prefix
IDENTITY = {"username": "ipr-info-admin", "role": "admin", "role_ids": ["admin"], "_actual_role_ids": ["admin"],
            "display_name": "IPR Info Admin", "department": "IPR"}
app = FastAPI()
app.include_router(case_info.router)
app.include_router(case_files.router)
app.include_router(reminders.router)
app.add_api_route(f"{settings.api_prefix}/ipr/cases/{{case_id}}/logs", create_ipr_case_log, methods=["POST"], status_code=201)


class IprCaseInfoEditTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with self.sessions() as db:
            now = datetime(2026, 10, 28, tzinfo=timezone.utc)
            case = BusinessRecord(
                module="ipr_case", serial_no="SHPU1810971", title="一种耐火光缆", customer="上海汉欣", status="受理",
                owner=IDENTITY["username"], department="IPR", created_at=now, updated_at=now,
                data={"case_kind": "专利", "legacy_ipr_case_id": 5386, "case_phase": "受理", "case_name": "一种耐火光缆",
                      "cost_slow_rate": "0.85", "has_relief": "T", "case_request_no": "201821235593X"},
            )
            db.add(case)
            await db.commit()
            self.case_id = case.id
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

    async def test_legacy_case_info_can_be_saved(self):
        response = await self.client.patch(f"{API}/ipr/cases/{self.case_id}/info", json={
            "case_phase": "授权", "case_name": "一种新型耐火光缆", "authorization_date": "2019-03-31",
            "first_annual_year": 2, "cost_slow_rate": "0.70", "has_relief": True, "has_priority": True,
        })
        self.assertEqual(response.status_code, 200, response.text)
        async with self.sessions() as db:
            record = await db.get(BusinessRecord, self.case_id)
            self.assertEqual(record.title, "一种新型耐火光缆")
            self.assertEqual(record.data["case_phase"], "授权")
            self.assertEqual(record.data["authorization_date"], "2019-03-31")
            self.assertEqual((record.data["first_annual_year"], record.data["annual_fee_year"]), ("2", "2"))
            self.assertEqual((record.data["cost_slow_rate"], record.data["rate"]), ("0.70", "0.70"))
            self.assertEqual((record.data["has_relief"], record.data["has_priority"]), ("T", "T"))
            events = (await db.scalars(select(WorkflowEvent).where(WorkflowEvent.record_id == self.case_id))).all()
            self.assertEqual(len(events), 1)
            self.assertEqual(events[0].action, "修改案件信息")
            for label in ("案件阶段", "名称", "授权日", "首年年费年度", "费用减缓比例", "优先权"):
                self.assertIn(label, events[0].comment)
            self.assertNotIn("费用减缓、", events[0].comment)
        bad = await self.client.patch(f"{API}/ipr/cases/{self.case_id}/info", json={"cost_slow_rate": "0.5"})
        self.assertEqual(bad.status_code, 422)

    async def test_phase_options_and_files_fall_back_without_legacy_tables(self):
        options = await self.client.get(f"{API}/ipr/cases/{self.case_id}/phase-options")
        self.assertEqual(options.json(), {"items": ["受理"]})
        files = await self.client.get(f"{API}/ipr/cases/{self.case_id}/files")
        self.assertEqual(files.status_code, 200, files.text)


    async def test_side_panel_log_and_reminder_on_legacy_case(self):
        """BUG20261028013：迁移案件（受理等阶段）也能新增案件日志和案件提醒，已结案不行。"""
        log = await self.client.post(f"{API}/ipr/cases/{self.case_id}/logs", json={"content": "已通知客户"})
        self.assertEqual(log.status_code, 201, log.text)
        suppress = await self.client.put(f"{API}/ipr/cases/{self.case_id}/reminder-suppressions", json={"reminder_type_ids": []})
        self.assertNotEqual(suppress.status_code, 409, suppress.text)
        async with self.sessions() as db:
            record = await db.get(BusinessRecord, self.case_id)
            record.status = "已结案"
            await db.commit()
        # 501190：非诉个案已结案也能写日志；诉讼类已结案仍不行。
        open_closed = await self.client.post(f"{API}/ipr/cases/{self.case_id}/logs", json={"content": "x"})
        self.assertEqual(open_closed.status_code, 201, open_closed.text)
        async with self.sessions() as db:
            record = await db.get(BusinessRecord, self.case_id)
            record.data = {**(record.data or {}), "case_category": "litigation"}
            await db.commit()
        closed = await self.client.post(f"{API}/ipr/cases/{self.case_id}/logs", json={"content": "x"})
        self.assertEqual(closed.status_code, 409)

    async def test_trademark_fields_and_image(self):
        """BUG20261030005：商标案件保存商标类别、商品服务、初审公告、商标类型和颜色/声音/三维标志，可上传商标图样。"""
        async with self.sessions() as db:
            record = await db.get(BusinessRecord, self.case_id)
            record.data = {**record.data, "case_kind": "商标"}
            await db.commit()
        response = await self.client.patch(f"{API}/ipr/cases/{self.case_id}/info", json={
            "trademark_ids": "9、35", "trade_product_service": "商业管理咨询", "first_instance_date": "2016-12-13",
            "trade_type_name": "一般商标", "has_trade_color_protected": True, "has_trade3_d_protected": True,
        })
        self.assertEqual(response.status_code, 200, response.text)
        bad = await self.client.patch(f"{API}/ipr/cases/{self.case_id}/info", json={"trade_type_name": "特殊商标"})
        self.assertEqual(bad.status_code, 422)
        missing = await self.client.get(f"{API}/ipr/cases/{self.case_id}/trademark-image")
        self.assertEqual(missing.status_code, 404)
        import tempfile
        from unittest import mock
        from pathlib import Path
        from app.core import storage
        with tempfile.TemporaryDirectory() as folder, mock.patch.object(case_info, "UPLOAD_ROOT", Path(folder)), \
                mock.patch.object(storage, "UPLOAD_ROOT", Path(folder)):
            wrong = await self.client.put(f"{API}/ipr/cases/{self.case_id}/trademark-image", files={"file": ("a.pdf", b"%PDF", "application/pdf")})
            self.assertEqual(wrong.status_code, 422)
            png = b"\x89PNG\r\n\x1a\n" + b"0" * 32
            uploaded = await self.client.put(f"{API}/ipr/cases/{self.case_id}/trademark-image", files={"file": ("logo.png", png, "image/png")})
            self.assertEqual(uploaded.status_code, 200, uploaded.text)
            image = await self.client.get(f"{API}/ipr/cases/{self.case_id}/trademark-image")
            self.assertEqual((image.status_code, image.content), (200, png))
        async with self.sessions() as db:
            record = await db.get(BusinessRecord, self.case_id)
            self.assertEqual((record.data["trademark_ids"], record.data["trade_product_service"]), ("9、35", "商业管理咨询"))
            self.assertEqual((record.data["first_instance_date"], record.data["trade_type_name"]), ("2016-12-13", "一般商标"))
            self.assertEqual((record.data["has_trade_color_protected"], record.data["has_trade3_d_protected"]), ("T", "T"))
            self.assertEqual(record.data["trademark_image_attachment_id"], uploaded.json()["attachment_id"])
            comments = [event.comment for event in (await db.scalars(select(WorkflowEvent).where(WorkflowEvent.record_id == self.case_id))).all()]
            self.assertTrue(any("商标类别" in comment and "颜色保护" in comment for comment in comments))
            self.assertTrue(any("商标图样" in comment for comment in comments))

    async def test_patent_case_cannot_upload_trademark_image(self):
        response = await self.client.put(f"{API}/ipr/cases/{self.case_id}/trademark-image", files={"file": ("logo.png", b"x", "image/png")})
        self.assertEqual(response.status_code, 422)


if __name__ == "__main__":
    unittest.main()
