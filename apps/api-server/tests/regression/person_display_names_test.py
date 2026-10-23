"""人员姓名统一补齐：附件上传人、记录负责人、收文列表；找不到账号的显示原用户名，不再显示“姓名待维护”。"""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import httpx
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.core import person_names
from app.core.formatters import _person_reference_display
from app.core.storage import _attachment_dict
from app.core.system import _record_dict
from app.database import Base, get_db
from app.main import app
from app.models import BusinessRecord, FileAttachment, User
from app.security import current_identity

API = settings.api_prefix
IDENTITY = {"username": "tgn", "role": "admin", "role_ids": ["admin"], "department": "测试部"}


class PersonNamesTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with self.sessions() as db:
            db.add_all([User(username="tgn", display_name="思法汇成", role="admin", role_ids=["admin"], department="测试部",
                             password_hash="unused", is_active=True),
                        User(username="caozg", display_name="曹志刚", role="user", role_ids=["user"], department="测试部",
                             password_hash="unused", is_active=True)])
            await db.commit()
            await person_names.refresh_person_names(db, force=True)
        self.old_overrides = dict(app.dependency_overrides)
        app.dependency_overrides[get_db] = self.override_db
        app.dependency_overrides[current_identity] = lambda: IDENTITY
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://names.test")
        self.temporary = tempfile.TemporaryDirectory(prefix="CODEX-names-")

    async def asyncTearDown(self):
        await self.client.aclose()
        app.dependency_overrides.clear()
        app.dependency_overrides.update(self.old_overrides)
        await self.engine.dispose()
        self.temporary.cleanup()

    async def override_db(self):
        async with self.sessions() as db:
            yield db

    def test_lookup_falls_back_to_username_for_unknown_accounts(self):
        self.assertEqual(person_names.person_name("TGN"), "思法汇成")
        self.assertEqual(person_names.person_name("legacy_wang"), "legacy_wang")
        self.assertEqual((person_names.person_name(""), person_names.person_name("system")), ("", "系统"))
        self.assertEqual(_person_reference_display("legacy_wang", {}), ("legacy_wang", True))

    def test_attachment_and_record_carry_display_names_without_caller_maps(self):
        known = FileAttachment(id=1, category="官方收文", original_name="a.pdf", stored_name="a", size=1, path="a", uploader="tgn")
        unknown = FileAttachment(id=2, category="官方收文", original_name="b.pdf", stored_name="b", size=1, path="b", uploader="legacy_wang")
        self.assertEqual(_attachment_dict(known)["uploader_display_name"], "思法汇成")
        self.assertEqual(_attachment_dict(unknown)["uploader_display_name"], "legacy_wang")
        self.assertEqual(_attachment_dict(known, None, {"tgn": "映射优先"})["uploader_display_name"], "映射优先")
        record = BusinessRecord(id=9, module="document", serial_no="SW1", title="t", customer="", status="待签收", owner="caozg",
                                department="测试部", data={})
        self.assertEqual(_record_dict(record)["owner_display_name"], "曹志刚")

    async def test_receipt_list_shows_uploader_names(self):
        root = Path(self.temporary.name)
        local = root / "notice.pdf"
        local.write_bytes(b"pdf")
        async with self.sessions() as db:
            case = BusinessRecord(module="case", serial_no="GDMS1", title="案件", customer="客户", owner="tgn", department="测试部",
                                  status="提交立案", data={})
            db.add(case)
            await db.flush()
            official = FileAttachment(record_id=case.id, category="官方收文", original_name="GDMS1_传票.pdf", stored_name="o1",
                                      size=3, path=str(local), uploader="tgn")
            legacy = FileAttachment(record_id=case.id, category="案件文档", original_name="旧系统_通知书.pdf", stored_name="o2",
                                    size=3, path=str(local), uploader="legacy_wang")
            db.add_all([official, legacy])
            await db.flush()
            db.add(BusinessRecord(module="document", serial_no="SW1", title="GDMS1_传票.pdf", customer="", owner="tgn",
                                  department="测试部", status="待签收",
                                  data={"direction": "收文", "attachment_id": official.id, "case_id": case.id}))
            await db.commit()
        with patch("app.core.storage.UPLOAD_ROOT", root):
            response = await self.client.get(f"{API}/documents/receipts", params={"scope": "company"})
        self.assertEqual(response.status_code, 200, response.text)
        rows = {row["title"]: row for row in response.json()["items"]}
        self.assertEqual(rows["GDMS1_传票.pdf"]["data"]["uploader_display_name"], "思法汇成")
        self.assertEqual(rows["旧系统_通知书.pdf"]["data"]["uploader_display_name"], "legacy_wang")
        uploaders = {item["original_name"]: item["uploader_display_name"] for item in response.json()["attachments"]}
        self.assertEqual(uploaders, {"GDMS1_传票.pdf": "思法汇成", "旧系统_通知书.pdf": "legacy_wang"})
        self.assertNotIn("姓名待维护", response.text)


if __name__ == "__main__":
    unittest.main()
