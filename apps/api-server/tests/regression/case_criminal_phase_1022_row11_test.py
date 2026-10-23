"""10.22 第 11 行：刑事案件“修改案件阶段”按旧系统刑事阶段取范围。

根因：后端没有刑事专用阶段，且刑事类型只按 extra.case_type 取内置阶段；生产库若有旧系统
迁入的同名阶段，按名称全表取第一条会误报“案件阶段 ID 与名称不匹配”。
"""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.core.constants import DEFAULT_SYSTEM_PARAMETERS
from app.database import Base, get_db
from app.main import app
from app.models import BusinessRecord, CaseTypeCasePhaseRelation, SystemParameter, User, WorkflowEvent
from app.security import current_identity


API = settings.api_prefix
PREFIX = "CODEX-1022-11-"
IDENTITY = {"username": f"{PREFIX}admin", "display_name": "第11行管理员", "role": "admin", "department": "上海分所"}
CRIMINAL_ROOTS = ["新案待分配", "公安侦查", "批捕", "检察院审查起诉", "一审阶段", "二审阶段", "再审阶段", "归档阶段"]
CIVIL_ONLY = ["等待公证书", "审核公证书", "待主体披露", "文书准备", "客户盖章", "等待立案", "补充取证", "提交立案", "执行阶段", "准备材料", "执行和解中"]


def _default_phases():
    return [
        SystemParameter(category=category, code=code, name=name, extra=dict(extra),
                        sort_order=int(extra.get("sort_order") or 0), is_active=True, created_by="system")
        for category, code, name, extra in DEFAULT_SYSTEM_PARAMETERS if category == "case_phase"
    ]


class CriminalCasePhaseRow11Test(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool,
        )
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with self.sessions() as db:
            civil_type = SystemParameter(category="case_type", code="110", name="民事争议", extra={}, is_active=True)
            criminal_type = SystemParameter(category="case_type", code="120", name="刑事案件", extra={}, is_active=True)
            # 模拟生产：旧系统迁入的刑事阶段先于内置阶段存在（id 更小），且与内置阶段同名。
            legacy_rows = [
                SystemParameter(category="case_phase", code="9101", name="公安侦查", is_active=True, created_by="migration",
                                extra={"case_type": "刑事案件", "parent_code": "", "migration_source": "hz_crm_20260930"}),
                SystemParameter(category="case_phase", code="9102", name="一审立案受理", is_active=True, created_by="migration",
                                extra={"case_type": "刑事案件", "parent_code": "9103", "migration_source": "hz_crm_20260930"}),
            ]
            db.add_all([
                User(username=IDENTITY["username"], display_name=IDENTITY["display_name"], department=IDENTITY["department"],
                     role="admin", password_hash="x", is_active=True),
                civil_type, criminal_type, *legacy_rows,
            ])
            await db.flush()
            db.add_all(_default_phases())
            await db.flush()
            db.add_all([CaseTypeCasePhaseRelation(case_type_id=criminal_type.id, case_phase_id=row.id) for row in legacy_rows])
            db.add_all([
                self._case(f"{PREFIX}XS-001", "刑事案件", "新案待分配"),
                self._case(f"{PREFIX}MS-001", "民事争议", "文书准备"),
            ])
            await db.commit()
            self.legacy_ids = {row.name: row.id for row in legacy_rows}
            self.ids = {item.code: item.id for item in (await db.scalars(select(SystemParameter).where(
                SystemParameter.category == "case_phase"))).all()}
        app.dependency_overrides[get_db] = self._override_db
        app.dependency_overrides[current_identity] = lambda: IDENTITY
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://row11.test")

    def _case(self, serial_no, case_type, status):
        return BusinessRecord(
            module="case", serial_no=serial_no, title=f"{serial_no} 阶段", customer=f"{PREFIX}客户", status=status,
            owner=IDENTITY["username"], department=IDENTITY["department"],
            data={"case_type": case_type, "case_creation_step": "completed", "case_creation_approval_status": "已通过",
                  "handling_lawyer_usernames": [IDENTITY["username"]], "case_team_usernames": [IDENTITY["username"]]},
        )

    async def _override_db(self):
        async with self.sessions() as db:
            yield db

    async def asyncTearDown(self):
        await self.client.aclose()
        app.dependency_overrides.clear()
        await self.engine.dispose()

    async def test_criminal_phase_list_matches_legacy_criminal_tree(self):
        response = await self.client.get(f"{API}/cases/phases", params={"case_type": "刑事案件"})
        self.assertEqual(response.status_code, 200, response.text)
        items = response.json()["items"]
        names = [item["name"] for item in items]
        self.assertEqual(len(names), len(set(names)), "同名阶段必须去重")
        for name in CRIMINAL_ROOTS:
            self.assertIn(name, names)
        for name in CIVIL_ONLY:
            self.assertNotIn(name, names)
        children = {parent: [item["name"] for item in items if item["parent_code"] == parent] for parent in ("FIRST", "SECOND", "RETRIAL", "ARCHIVE")}
        # 10.22 新增第 11 行：子阶段按旧系统刑事截图，不再与民事相同。
        self.assertEqual(set(children["FIRST"]), {"一审立案受理", "一审补充证据", "一审通知开庭", "一审庭后待判", "一审一审判决", "一审等待上诉"})
        self.assertEqual(set(children["SECOND"]), {"二审上诉准备", "二审立案受理", "二审补充证据", "二审通知开庭", "二审庭后待判", "二审判决", "二审判决生效"})
        self.assertEqual(set(children["RETRIAL"]), {"再审立案受理", "再审补充证据", "再审通知开庭", "再审庭后待判", "再审待执行"})
        for name in ("一审准备开庭", "一审和解中", "二审再次开庭", "二审判决结案", "再审和解中"):
            self.assertNotIn(name, names)
        self.assertEqual(children["ARCHIVE"], ["归档审核", "已归档", "归档拒绝", "亏损内审", "亏损审核", "亏损归档", "亏损拒绝"])
        by_name = {item["name"]: item for item in items}
        self.assertEqual(by_name["公安侦查"]["code"], "CRIMINAL_POLICE_INVESTIGATION")
        self.assertEqual(by_name["一审立案受理"]["code"], "FIRST_ACCEPTED")

    async def test_civil_phase_list_is_unchanged(self):
        response = await self.client.get(f"{API}/cases/phases", params={"case_type": "民事争议"})
        self.assertEqual(response.status_code, 200, response.text)
        names = [item["name"] for item in response.json()["items"]]
        self.assertEqual(len(names), 64)
        for name in ("公安侦查", "批捕", "检察院审查起诉", "一审一审判决", "二审上诉准备", "二审判决", "二审判决生效"):
            self.assertNotIn(name, names)

    async def _change(self, case_no, phase_id, phase_name):
        return await self.client.post(f"{API}/cases/phase-change", json={
            "case_nos": [case_no], "case_phase_id": phase_id, "case_phase_name": phase_name, "comment": f"{PREFIX}验收",
        })

    async def test_criminal_case_changes_to_criminal_and_shared_phases(self):
        response = await self._change(f"{PREFIX}XS-001", self.ids["CRIMINAL_POLICE_INVESTIGATION"], "公安侦查")
        self.assertEqual(response.status_code, 200, response.text)
        # 同名旧阶段 id 更小，旧实现按名称取第一条会报“ID 与名称不匹配”。
        response = await self._change(f"{PREFIX}XS-001", self.ids["FIRST_ACCEPTED"], "一审立案受理")
        self.assertEqual(response.status_code, 200, response.text)
        async with self.sessions() as db:
            record = await db.scalar(select(BusinessRecord).where(BusinessRecord.serial_no == f"{PREFIX}XS-001"))
            self.assertEqual(record.status, "一审立案受理")
            self.assertEqual(record.data["case_phase_id"], self.ids["FIRST_ACCEPTED"])
            events = (await db.scalars(select(WorkflowEvent).where(WorkflowEvent.record_id == record.id))).all()
            self.assertEqual([event.to_status for event in events], ["公安侦查", "一审立案受理"])

    async def test_legacy_imported_criminal_phase_still_accepted(self):
        response = await self._change(f"{PREFIX}XS-001", self.legacy_ids["公安侦查"], "公安侦查")
        self.assertEqual(response.status_code, 200, response.text)

    async def test_rejections(self):
        response = await self._change(f"{PREFIX}MS-001", self.ids["CRIMINAL_POLICE_INVESTIGATION"], "公安侦查")
        self.assertEqual(response.status_code, 422, response.text)
        response = await self._change(f"{PREFIX}XS-001", self.ids["EXECUTION_ACCEPTED"], "执行受理")
        self.assertEqual(response.status_code, 422, response.text)
        response = await self._change(f"{PREFIX}XS-001", self.ids["CRIMINAL_ARREST"], "公安侦查")
        self.assertEqual(response.status_code, 422, response.text)
        self.assertIn("ID 与名称不匹配", response.text)


class CriminalPhaseStartupSeedRow11Test(unittest.IsolatedAsyncioTestCase):
    async def test_startup_adds_criminal_phases_once_without_touching_existing_rows(self):
        from app.core.lifecycle import _backfill_clue_generated_case_register_dates, _upgrade_schema
        from app.core.startup_data import initialize_startup_data
        from app.core.startup_migrations import migrate_startup_schema

        with tempfile.TemporaryDirectory() as directory:
            engine = create_async_engine(f"sqlite+aiosqlite:///{Path(directory) / 'row11.db'}")
            try:
                await migrate_startup_schema(engine, _upgrade_schema)
                sessions = async_sessionmaker(engine, expire_on_commit=False)
                legacy_extra = {"case_type": "刑事案件", "parent_code": "", "migration_source": "hz_crm_20260930"}
                async with sessions() as db:
                    db.add(SystemParameter(category="case_phase", code="9101", name="公安侦查", extra=dict(legacy_extra),
                                           sort_order=7, is_active=True, created_by="migration"))
                    await db.commit()
                with patch.object(settings, "seed_demo_data", False), patch.object(settings, "initial_admin_password", "Row11Startup123!"):
                    for _ in range(2):
                        await initialize_startup_data(sessions, _backfill_clue_generated_case_register_dates)
                async with sessions() as db:
                    rows = (await db.scalars(select(SystemParameter).where(SystemParameter.category == "case_phase"))).all()
                codes = [row.code for row in rows]
                for code in ("CRIMINAL_POLICE_INVESTIGATION", "CRIMINAL_ARREST", "CRIMINAL_PROSECUTION_REVIEW"):
                    self.assertEqual(codes.count(code), 1)
                legacy = next(row for row in rows if row.code == "9101")
                self.assertEqual((legacy.name, legacy.is_active, legacy.sort_order, legacy.extra), ("公安侦查", True, 7, legacy_extra))
                self.assertEqual(sum(1 for row in rows if row.is_active and (row.extra or {}).get("case_type") == "民事争议"), 64)
            finally:
                await engine.dispose()


if __name__ == "__main__":
    unittest.main()
