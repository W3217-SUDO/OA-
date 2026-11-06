"""501635（tgn 11-06）：发任务选常见主题自动带负责人——案件选项里带上本案律师助理、开庭律师的在职账号。"""
import unittest

import httpx
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database import Base, get_db
from app.main import app
from app.models import BusinessRecord, User
from app.security import current_identity

API = settings.api_prefix
ADMIN = {"username": "admin", "role": "admin", "role_ids": ["admin"], "display_name": "管理者", "department": "上海分所"}


class TaskSubjectPresetsTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with self.sessions() as db:
            for username, name, active in (("admin", "管理者", True), ("zhul", "助理甲", True), ("gone", "离职乙", False), ("kting", "开庭丙", True)):
                db.add(User(username=username, display_name=name, department="上海分所", password_hash="x", role="admin" if username == "admin" else "user", is_active=active))
            db.add(BusinessRecord(module="case", serial_no="HZMS2600001", title="案", status="办理中", owner="admin", department="上海分所",
                                  data={"assistants": ["离职乙", "助理甲"], "hearing_lawyer": "开庭丙"}))
            await db.commit()
        app.dependency_overrides[get_db] = self._db
        app.dependency_overrides[current_identity] = lambda: ADMIN
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://preset.test")

    async def _db(self):
        async with self.sessions() as db:
            yield db

    async def asyncTearDown(self):
        await self.client.aclose(); app.dependency_overrides.clear(); await self.engine.dispose()

    async def test_case_options_carry_active_assistant_and_hearing_lawyer(self):
        response = await self.client.get(f"{API}/tasks/case-options", params={"keyword": "HZMS2600001"})
        self.assertEqual(response.status_code, 200, response.text)
        item = response.json()["items"][0]
        self.assertEqual(item["assistant_usernames"], ["zhul"], "中文名换成账号，离职的不带")
        self.assertEqual(item["hearing_lawyer_usernames"], ["kting"])


if __name__ == "__main__":
    unittest.main()
