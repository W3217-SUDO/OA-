"""10.23 第2行：民事案件“变更阶段”选“一审补充代理意见”报“案件阶段 ID 与名称不匹配”。

生产库同名阶段有 3 条：内置 FIRST_AGENT_OPINION（民事争议）、旧系统导入 101022（民事争议，
在案件类型关联里）、旧系统导入 301022（行政案件及国家赔偿）。1.1.532 以前按名称全表取任意一条与
所选 id 比对而误报；现以所选 id 为准，两个民事可用 id 都应能保存。
"""

import unittest

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.core.constants import DEFAULT_SYSTEM_PARAMETERS
from app.database import Base, get_db
from app.main import app
from app.models import BusinessRecord, CaseTypeCasePhaseRelation, SystemParameter, User
from app.security import current_identity


API = settings.api_prefix
PREFIX = "CODEX-1023-2-"
IDENTITY = {"username": f"{PREFIX}admin", "display_name": "第2行管理员", "role": "admin", "department": "上海分所"}
PHASE = "一审补充代理意见"


class CivilDuplicatePhaseNameRow2Test(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool,
        )
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with self.sessions() as db:
            civil = SystemParameter(category="case_type", code="110", name="民事争议", extra={}, is_active=True)
            admin_type = SystemParameter(category="case_type", code="130", name="行政案件及国家赔偿", extra={}, is_active=True)
            db.add_all([
                User(username=IDENTITY["username"], display_name=IDENTITY["display_name"], department=IDENTITY["department"],
                     role="admin", password_hash="x", is_active=True),
                civil, admin_type,
            ])
            db.add_all([
                SystemParameter(category=category, code=code, name=name, extra=dict(extra),
                                sort_order=int(extra.get("sort_order") or 0), is_active=True, created_by="system")
                for category, code, name, extra in DEFAULT_SYSTEM_PARAMETERS if category == "case_phase"
            ])
            await db.flush()
            legacy_civil = SystemParameter(category="case_phase", code="101022", name=PHASE, is_active=True, created_by="migration",
                                           extra={"case_type": "民事争议", "parent_code": "1010140"})
            legacy_admin = SystemParameter(category="case_phase", code="301022", name=PHASE, is_active=True, created_by="migration",
                                           extra={"case_type": "行政案件及国家赔偿", "parent_code": "3010140"})
            db.add_all([legacy_civil, legacy_admin])
            await db.flush()
            db.add(CaseTypeCasePhaseRelation(case_type_id=civil.id, case_phase_id=legacy_civil.id))
            db.add(BusinessRecord(
                module="case", serial_no=f"{PREFIX}MS-001", title="第2行民事案件", customer=f"{PREFIX}客户", status="文书准备",
                owner=IDENTITY["username"], department=IDENTITY["department"],
                data={"case_type": "民事争议", "case_creation_step": "completed", "case_creation_approval_status": "已通过",
                      "handling_lawyer_usernames": [IDENTITY["username"]], "case_team_usernames": [IDENTITY["username"]]},
            ))
            await db.commit()
            self.builtin_id = await db.scalar(select(SystemParameter.id).where(SystemParameter.code == "FIRST_AGENT_OPINION"))
            self.second_id = await db.scalar(select(SystemParameter.id).where(SystemParameter.code == "SECOND_AGENT_OPINION"))
            self.legacy_civil_id, self.legacy_admin_id = legacy_civil.id, legacy_admin.id
        app.dependency_overrides[get_db] = self._override_db
        app.dependency_overrides[current_identity] = lambda: IDENTITY
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://row2-1023.test")

    async def _override_db(self):
        async with self.sessions() as db:
            yield db

    async def asyncTearDown(self):
        await self.client.aclose()
        app.dependency_overrides.clear()
        await self.engine.dispose()

    async def _change(self, phase_id, phase_name):
        return await self.client.post(f"{API}/cases/phase-change", json={
            "case_nos": [f"{PREFIX}MS-001"], "case_phase_id": phase_id, "case_phase_name": phase_name, "comment": f"{PREFIX}验收",
        })

    async def _case(self):
        async with self.sessions() as db:
            return await db.scalar(select(BusinessRecord).where(BusinessRecord.serial_no == f"{PREFIX}MS-001"))

    async def test_both_civil_ids_of_duplicate_name_can_be_saved(self):
        for phase_id, back in ((self.legacy_civil_id, self.second_id), (self.builtin_id, self.second_id)):
            response = await self._change(phase_id, PHASE)
            self.assertEqual(response.status_code, 200, response.text)
            self.assertNotIn("不匹配", response.text)
            record = await self._case()
            self.assertEqual(record.status, PHASE)
            self.assertEqual(record.data["case_phase_id"], phase_id)
            # 改到其他阶段再试另一个同名 id，避免“当前案件已处于所选阶段”。
            self.assertEqual((await self._change(back, "二审补充代理意见")).status_code, 200)

    async def test_real_id_name_mismatch_still_rejected(self):
        response = await self._change(self.builtin_id, "二审补充代理意见")
        self.assertEqual(response.status_code, 422, response.text)
        self.assertIn("ID 与名称不匹配", response.text)
        self.assertEqual((await self._case()).status, "文书准备")

    async def test_civil_phase_list_offers_selectable_option(self):
        response = await self.client.get(f"{API}/cases/phases", params={"case_type": "民事争议"})
        self.assertEqual(response.status_code, 200, response.text)
        ids = {item["id"] for item in response.json()["items"] if item["name"] == PHASE}
        self.assertTrue(ids & {self.builtin_id, self.legacy_civil_id})
        self.assertNotIn(self.legacy_admin_id, ids, "行政案件的同名阶段不进入民事列表")


if __name__ == "__main__":
    unittest.main()
