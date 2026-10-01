"""8.31 row 8: company task filters search system people by Chinese name."""

from datetime import date, timedelta
import unittest

import httpx
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database import Base, get_db
from app.main import app
from app.models import BusinessRecord, RolePermission, User
from app.security import current_identity


API = settings.api_prefix
VIEWER = {
    "username": "fwl",
    "role": "user",
    "display_name": "范文林",
    "department": "测试部",
}


class TaskCompanyPeopleSearchRow8Test(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.sessions = async_sessionmaker(
            self.engine, expire_on_commit=False, class_=AsyncSession,
        )
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with self.sessions() as db:
            db.add_all([
                User(
                    username="fwl", display_name="范文林", department="测试部",
                    role="user", password_hash="x", is_active=True,
                ),
                User(
                    username="admin", display_name="陶威", department="管理部",
                    role="admin", password_hash="x", is_active=True,
                ),
                RolePermission(
                    role="user", display_name="公司发起任务查看",
                    data_scope="全所数据", menu_keys=["task-company-created"],
                    field_keys=[],
                ),
                BusinessRecord(
                    module="task", serial_no="CODEX-831-R8-FWL",
                    title="范文林发起的任务", customer="8.31客户",
                    status="处理中", owner="admin", department="测试部",
                    data={
                        "deadline": str(date.today() + timedelta(days=7)),
                        "source": "日常任务", "initiator": "fwl",
                        "collaborators": [],
                    },
                ),
                BusinessRecord(
                    module="task", serial_no="CODEX-831-R8-OTHER",
                    title="其他人员发起的任务", customer="8.31客户",
                    status="处理中", owner="fwl", department="管理部",
                    data={
                        "deadline": str(date.today() + timedelta(days=7)),
                        "source": "日常任务", "initiator": "admin",
                        "collaborators": [],
                    },
                ),
            ])
            await db.commit()

        self.previous_overrides = dict(app.dependency_overrides)
        app.dependency_overrides[get_db] = self.override_db
        app.dependency_overrides[current_identity] = lambda: VIEWER
        self.client = httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://row8.test",
        )

    async def override_db(self):
        async with self.sessions() as db:
            yield db

    async def asyncTearDown(self) -> None:
        await self.client.aclose()
        app.dependency_overrides.clear()
        app.dependency_overrides.update(self.previous_overrides)
        await self.engine.dispose()

    async def search(self, **params):
        return await self.client.get(
            f"{API}/tasks",
            params={"scope": "company", "relation": "initiated", **params},
        )

    async def test_initiator_filter_matches_full_and_partial_chinese_name(self) -> None:
        for value in ("范文林", "文林", "fwl"):
            response = await self.search(initiator=value)
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(
                [item["serial_no"] for item in response.json()["items"]],
                ["CODEX-831-R8-FWL"],
            )

    async def test_owner_and_keyword_filters_match_display_names(self) -> None:
        owner_response = await self.search(owner="陶威")
        self.assertEqual(owner_response.status_code, 200, owner_response.text)
        self.assertEqual(owner_response.json()["total"], 1)
        self.assertEqual(owner_response.json()["items"][0]["serial_no"], "CODEX-831-R8-FWL")

        keyword_response = await self.search(keyword="范文")
        self.assertEqual(keyword_response.status_code, 200, keyword_response.text)
        self.assertEqual(keyword_response.json()["total"], 2)
        self.assertEqual(
            {item["serial_no"] for item in keyword_response.json()["items"]},
            {"CODEX-831-R8-FWL", "CODEX-831-R8-OTHER"},
        )


if __name__ == "__main__":
    unittest.main()
