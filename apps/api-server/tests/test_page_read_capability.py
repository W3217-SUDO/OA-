"""“能看见菜单和功能就有权限”：页面顺带读取其他中心数据时按所在页面授权（钉钉新系统沟通群 2026-10-27）。

账号只开了案件中心页面：新建案件页读调查线索、案件参数关系要能读到；没带页面、页面不是自己的、写操作、
系统管理等敏感接口都保持原来的拒绝。
"""
import unittest

import httpx
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database import Base, get_db
from app.main import app
from app.models import RolePermission, User
from app.security import create_token
from tests.personnel_role_fixture import bind_system_role_pages

API = settings.api_prefix


class PageReadCapabilityTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.sessions() as db:
            db.add_all([
                User(username="CODEXPAGELAWYER", display_name="案件律师", password_hash="isolated-only",
                     department="CODEXPAGE", role="user"),
                RolePermission(role="user", display_name="普通员工", data_scope="本人数据",
                               menu_keys=["case", "case-new", "case-new-civil", "case-mine", "case-mine-civil"], field_keys=[]),
            ])
            await db.commit()

        async def override_db():
            async with self.sessions() as db:
                yield db

        app.dependency_overrides[get_db] = override_db
        token = create_token("CODEXPAGELAWYER", "user", 30)
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test",
                                        headers={"Authorization": f"Bearer {token}"})
        await bind_system_role_pages(self.sessions)

    async def asyncTearDown(self):
        await self.client.aclose()
        app.dependency_overrides.pop(get_db, None)
        await self.engine.dispose()

    async def get(self, path, page=None, **params):
        headers = {"X-OA-Page": page} if page else {}
        return await self.client.get(f"{API}{path}", params=params, headers=headers)

    async def test_case_page_reads_clue_options_and_parameter_relations(self):
        self.assertEqual((await self.get("/records", module="clue", page_size=100)).status_code, 403)
        self.assertEqual((await self.get("/records", "case-new", module="clue", page_size=100)).status_code, 200)
        relation = "/system/parameter-relations/case-type-case-phases"
        self.assertEqual((await self.get(relation)).status_code, 403)
        self.assertEqual((await self.get(relation, "case-new")).status_code, 200)

    async def test_detail_pages_count_as_their_center(self):
        response = await self.get("/records", "case-detail-108680-HZMS2600006", module="clue", page_size=10)
        self.assertEqual(response.status_code, 200)
        encoded = "customer-detail-279933-%E4%B8%93%E5%88%A9"
        self.assertEqual((await self.get("/records", encoded, module="clue")).status_code, 403)  # 没有客户中心页面

    async def test_pages_not_held_writes_and_sensitive_areas_stay_refused(self):
        self.assertEqual((await self.get("/records", "investigation-task-mine", module="clue")).status_code, 403)
        self.assertEqual((await self.get("/system/users", "case-new")).status_code, 403)
        self.assertEqual((await self.get("/system/role-permissions", "case-new")).status_code, 403)
        created = await self.client.post(f"{API}/records", headers={"X-OA-Page": "case-new"},
                                         json={"module": "clue", "serial_no": "CODEXPAGE1", "title": "CODEX-PAGE", "customer": "", "data": {}})
        self.assertEqual(created.status_code, 403)


if __name__ == "__main__":
    unittest.main()
