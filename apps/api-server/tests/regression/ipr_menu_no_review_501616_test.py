"""501616（范文玲 11-05）：知识产权中心按老系统菜单；新建非诉案件不审核，提交即在办（诉讼类仍走立案审核）。"""
import unittest

import httpx
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.core.constants import DEFAULT_HIDDEN_MENU_KEYS, DEFAULT_SYSTEM_MENUS, ROLE_TREE_HIDDEN_MENU_KEYS
from app.database import Base, get_db
from app.main import app
from app.models import BusinessRecord, User
from app.security import current_identity

API = settings.api_prefix
ME = {"username": "fwl616", "role": "admin", "role_ids": ["admin"], "_actual_role_ids": ["admin"], "display_name": "范文玲", "department": "知产部",
      "action_keys": ["*"]}


class IprMenuNoReview501616Test(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with self.sessions() as db:
            db.add(User(username="fwl616", display_name="范文玲", department="知产部", role="admin", password_hash="x", is_active=True))
            self.ids = {}
            for key, category in (("non", "non_litigation"), ("lit", "litigation")):
                record = BusinessRecord(module="ipr_case", serial_no=f"N616-{key}", title=key, customer="客户", status="草稿", owner="fwl616",
                                        department="知产部", data={"case_kind": "专利", "case_category": category, "application_no": "2026100000001"})
                db.add(record)
                await db.flush()
                self.ids[key] = record.id
            await db.commit()
        self.previous = dict(app.dependency_overrides)

        async def session():
            async with self.sessions() as db:
                yield db
        app.dependency_overrides[get_db] = session
        app.dependency_overrides[current_identity] = lambda: dict(ME)
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://ipr616.test")

    async def asyncTearDown(self):
        await self.client.aclose()
        app.dependency_overrides.clear()
        app.dependency_overrides.update(self.previous)
        await self.engine.dispose()

    async def test_non_litigation_submit_goes_straight_to_in_progress(self):
        response = await self.client.post(f"{API}/ipr/cases/{self.ids['non']}/submit")
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["status"], "在办", "非诉新建不审核，提交即立案")
        response = await self.client.post(f"{API}/ipr/cases/{self.ids['lit']}/submit")
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["status"], "待立案审核", "诉讼类仍走立案审核")

    def test_menu_order_and_hidden_pages(self):
        ipr = {key: order for key, parent, _label, _icon, order in DEFAULT_SYSTEM_MENUS if parent == "ipr"}
        self.assertEqual(sorted(("ipr-my-cases", "ipr-case-reboot", "ipr-patent-annual-fee", "ipr-case-files", "ipr-finance"), key=ipr.get),
                         ["ipr-my-cases", "ipr-case-reboot", "ipr-patent-annual-fee", "ipr-case-files", "ipr-finance"])
        for key in ("ipr-patent", "ipr-trademark", "ipr-review", "ipr-business-owner"):
            self.assertIn(key, DEFAULT_HIDDEN_MENU_KEYS)
            self.assertIn(key, ROLE_TREE_HIDDEN_MENU_KEYS)
        self.assertNotIn("ipr-office-files", DEFAULT_HIDDEN_MENU_KEYS, "官文等专利/商标转文上线后再收")


if __name__ == "__main__":
    unittest.main()
