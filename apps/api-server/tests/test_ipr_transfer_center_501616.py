"""280146 / 501616：知识产权中心“专利转文”“商标转文”——次级菜单计数、列表、标记已转、上传转文、生成转达函。"""
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import httpx
from docx import Document
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.areas.ipr import transfer_center as tc
from app.config import settings
from app.database import Base, get_db
from app.main import app
from app.models import BusinessRecord, FileAttachment, SystemParameter, User
from app.security import current_identity

API = settings.api_prefix
ADMIN = {"username": "admin", "role": "admin", "role_ids": ["admin"], "display_name": "管理者", "department": "知产"}


def case(serial, kind, customer, source="ipr_hd_20261030", **data):
    return BusinessRecord(module="ipr_case", serial_no=serial, title=serial, customer=customer, status="在办", owner="admin", department="知产",
                          data={"case_kind": kind, "migration_source": source, "customer_record_id": customer, "application_no": f"{serial}-NO",
                                "application_date": "2020-01-02T00:00:00", "case_name": f"{serial}名称", **data})


class IprTransferCenterTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.upload = patch.object(tc, "UPLOAD_ROOT", Path(self.temp.name)); self.upload.start()
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with self.sessions() as db:
            db.add(User(username="admin", display_name="管理者", department="知产", password_hash="x", role="admin", is_active=True))
            db.add_all([SystemParameter(category="ipr_case_file_type", code="200999", name="其他官文", extra={"is_official": True}, is_active=True),
                        SystemParameter(category="ipr_case_file_type", code="3310001", name="委托资料", extra={}, is_active=True)])
            p1, p2 = case("HDPI2000001", "专利", "甲公司", case_type_name="国内发明专利"), case("HDPU2000002", "专利", "乙公司", case_type_name="国内实用新型专利")
            old = case("SHPI1800001", "专利", "甲公司", source="hz_crm_20260930")
            t1 = case("HDTM2000003", "商标", "甲公司", trademark_ids="35")
            db.add_all([p1, p2, old, t1]); await db.flush()
            self.ids = {}
            for name, record, code, category, sent in (
                ("p1", p1, "200101", "专利申请受理通知书", False), ("p2", p2, "200101", "专利申请受理通知书", False),
                ("p1_done", p1, "200101", "专利申请受理通知书", True), ("p1_oa", p1, "210401", "第一次审查意见通知书", False),
                ("p1_other", p1, "200999", "其他官文", False), ("p1_client", p1, "3310001", "委托资料", False),
                ("old", old, "200101", "专利申请受理通知书", False),
                ("t1", t1, "420001", "商标注册申请受理通知书", False),
            ):
                attachment = FileAttachment(record_id=record.id, category=category, file_type_code=code, original_name=f"{name}.pdf",
                                            stored_name=f"{name}.pdf", content_type="application/pdf", size=1, path="x", uploader="admin", is_transmitted=sent)
                db.add(attachment); await db.flush(); self.ids[name] = attachment.id
            await db.commit()
        app.dependency_overrides[get_db] = self._db
        app.dependency_overrides[current_identity] = lambda: ADMIN
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://transfer.test")

    async def _db(self):
        async with self.sessions() as db:
            yield db

    async def asyncTearDown(self):
        await self.client.aclose(); app.dependency_overrides.clear(); await self.engine.dispose()
        self.upload.stop(); self.temp.cleanup()

    async def test_summary_items_and_mark(self):
        summary = (await self.client.get(f"{API}/ipr/transfer-center/patent/summary")).json()
        counts = {item["label"]: item["count"] for item in summary["items"]}
        self.assertEqual(len(summary["items"]), 26)
        self.assertEqual(counts["转专利申请受理通知书"], 2, "已转的、沪知老系统的不算")
        self.assertEqual((counts["转第一次审查意见通知书"], counts["转其他官文"]), (1, 1))
        trademark = {item["label"]: item["count"] for item in (await self.client.get(f"{API}/ipr/transfer-center/trademark/summary")).json()["items"]}
        self.assertEqual(trademark["转商标注册申请受理通知书"], 1)

        items = (await self.client.get(f"{API}/ipr/transfer-center/patent/items", params={"item": "200101"})).json()["items"]
        self.assertEqual({row["serial_no"] for row in items}, {"HDPI2000001", "HDPU2000002"})
        filtered = (await self.client.get(f"{API}/ipr/transfer-center/patent/items", params={"item": "200101", "customer": "甲 公司"})).json()["items"]
        self.assertEqual([row["serial_no"] for row in filtered], ["HDPI2000001"])
        done = (await self.client.get(f"{API}/ipr/transfer-center/patent/items", params={"item": "200101", "status": "已转"})).json()["items"]
        self.assertEqual([row["attachment_id"] for row in done], [self.ids["p1_done"]])

        response = await self.client.post(f"{API}/ipr/transfer-center/mark-transmitted", json={"attachment_ids": [self.ids["p2"]]})
        self.assertEqual(response.json(), {"updated": 1})
        counts = {item["label"]: item["count"] for item in (await self.client.get(f"{API}/ipr/transfer-center/patent/summary")).json()["items"]}
        self.assertEqual(counts["转专利申请受理通知书"], 1)

    async def test_upload_marks_and_attaches(self):
        response = await self.client.post(f"{API}/ipr/transfer-center/upload", files={"file": ("转达函.pdf", b"%PDF", "application/pdf")},
                                          data={"attachment_ids": f"[{self.ids['p1']}, {self.ids['p1_oa']}]", "document_date": "2026-11-05"})
        self.assertEqual(response.status_code, 201, response.text)
        self.assertEqual(response.json(), {"cases": 1, "transmitted": 2})
        async with self.sessions() as db:
            letters = (await db.scalars(select(FileAttachment).where(FileAttachment.original_name == "转达函.pdf"))).all()
            self.assertEqual(len(letters), 1)
            self.assertTrue((await db.get(FileAttachment, self.ids["p1"])).is_transmitted)

    async def test_generate_letter_same_customer_only(self):
        bad = await self.client.get(f"{API}/ipr/transfer-center/patent/generate", params={"item": "200101", "attachment_ids": f"{self.ids['p1']},{self.ids['p2']}"})
        self.assertEqual(bad.status_code, 422)
        self.assertIn("客户不一致", bad.json()["detail"])
        response = await self.client.get(f"{API}/ipr/transfer-center/patent/generate", params={"item": "200101", "attachment_ids": str(self.ids["p1"])})
        self.assertEqual(response.status_code, 200, response.text)
        document = Document(io.BytesIO(response.content))
        text = "\n".join(p.text for p in document.paragraphs) + "\n".join(c.text for t in document.tables for r in t.rows for c in r.cells)
        self.assertIn("HDPI2000001", text)
        self.assertIn("8110201012400029679", text, "收款账户换成中信银行古北支行")
        self.assertNotIn("452075880439", text)
        self.assertNotIn("$", text, "占位符都替换了")
        trademark = await self.client.get(f"{API}/ipr/transfer-center/trademark/generate", params={"item": "420001", "attachment_ids": str(self.ids["t1"])})
        self.assertEqual(trademark.status_code, 200, trademark.text)
        rows = [[c.text for c in r.cells] for r in Document(io.BytesIO(trademark.content)).tables[-1].rows]
        self.assertEqual(rows[-1][:5], ["1", "HDTM2000003", "HDTM2000003名称", "35", "HDTM2000003-NO"])

    def test_every_item_has_a_template(self):
        from app.areas.ipr.transfer_templates import TEMPLATES
        for kind, (_, items, other) in tc.KINDS.items():
            for item in items + ([other] if other else []):
                self.assertIn(item[3], TEMPLATES, item[1])
        self.assertIn("转第一次审查意见通知书(实用新型,外观)", TEMPLATES)


if __name__ == "__main__":
    unittest.main()
