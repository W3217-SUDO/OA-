"""Criminal case detail-maintenance parity for legacy post-create edit actions.

CodeGraph evidence used for this contract:
- codegraph explore "PublicSecurityUnitEdit FirstProcuratorateUnitEdit SecondProcuratorateUnitEdit LastProcuratorateUnitEdit FirstCourtEdit SecondCourtEdit ExecutionCourtEdit LastCourtEdit LitigantEdit"
  found the legacy Legal CaseController post-create modal actions.
- codegraph explore "ExecutionCourtEdit callers Legal.Case.Court.Invoke.js Cases.Case.Court Edit Load"
  found the legacy execution-court edit action and the detail page caller.

The new implementation must stay on dedicated criminal maintenance endpoints;
generic record PATCH or the creation-only /cases/{id}/judicial route is not an
acceptable substitute for completed cases.
"""

from __future__ import annotations

import pathlib
import re
import unittest

import httpx
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database import Base, get_db
from app.main import app
from app.models import BusinessRecord
from app.security import current_identity


API = settings.api_prefix
IDENTITY = {
    "username": "criminal-detail-admin",
    "role": "admin",
    "display_name": "Criminal Detail Admin",
    "department": "Criminal Detail Department",
}
FRONTEND_SOURCE = (
    pathlib.Path(__file__).resolve().parents[1]
    / "admin-web"
    / "src"
    / "CaseCenterPage.tsx"
).read_text(encoding="utf-8")


class CriminalDetailMaintenanceContractTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

        async with self.sessions() as db:
            case = BusinessRecord(
                module="case",
                serial_no="CRIMINAL-MAINT-001",
                title="Criminal post-create detail maintenance",
                customer="Criminal Customer",
                status="在办",
                owner=IDENTITY["username"],
                department=IDENTITY["department"],
                data={
                    "case_type": "刑事案件",
                    "case_creation_step": "completed",
                    "case_creation_approval_status": "已通过",
                    "case_team_usernames": [IDENTITY["username"]],
                },
            )
            db.add(case)
            await db.flush()
            self.case_id = case.id
            await db.commit()

        self.previous_overrides = dict(app.dependency_overrides)
        app.dependency_overrides[get_db] = self.override_db
        app.dependency_overrides[current_identity] = lambda: IDENTITY
        self.client = httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://criminal-detail-maintenance.test",
        )

    async def asyncTearDown(self) -> None:
        await self.client.aclose()
        app.dependency_overrides.clear()
        app.dependency_overrides.update(self.previous_overrides)
        await self.engine.dispose()

    async def override_db(self):
        async with self.sessions() as db:
            yield db

    def test_frontend_uses_dedicated_criminal_routes_not_creation_judicial_or_generic_patch(self) -> None:
        save_start = FRONTEND_SOURCE.index("const saveCriminalMaintenance")
        save_block = FRONTEND_SOURCE[save_start : FRONTEND_SOURCE.index("const openCaseLitigants", save_start)]
        self.assertIn("/criminal/${criminalMaintenance.kind}", save_block)
        self.assertNotIn("/judicial", save_block)
        self.assertNotIn("/records/", save_block)

    def test_frontend_criminal_court_maintenance_exposes_legacy_execution_level(self) -> None:
        courts_block = re.search(
            r'criminalMaintenance\?\.kind==="courts"&&(?P<body>.+?)<Form\.Item label="修改说明"',
            FRONTEND_SOURCE,
            re.S,
        )
        self.assertIsNotNone(courts_block, "criminal court maintenance block must exist")
        self.assertRegex(
            courts_block.group("body"),
            r'\["first","second","execution","retrial"\]',
            "legacy ExecutionCourtEdit requires an execution-court branch between second and retrial",
        )
        self.assertIn("execution_court_name", courts_block.group("body"))
        self.assertIn("执行法院", courts_block.group("body"))

    async def test_completed_criminal_courts_preserve_legacy_execution_court_fields(self) -> None:
        payload = {
            "first_court_enabled": True,
            "first_court_name": "一审法院",
            "first_court_case_no": "一案号",
            "execution_court_enabled": True,
            "execution_court_name": "执行法院",
            "execution_court_case_no": "执案号",
            "execution_court_courtroom": "执行庭",
            "execution_court_judge": "执行法官",
            "execution_court_clerk": "执行书记员",
            "execution_court_filing_date": "2026-08-01",
            "execution_court_hearing_date": "2026-08-15",
            "comment": "legacy ExecutionCourtEdit parity",
        }

        response = await self.client.put(f"{API}/cases/{self.case_id}/criminal/courts", json=payload)
        self.assertEqual(response.status_code, 200, response.text)
        data = response.json()["data"]
        for key in (
            "execution_court_enabled",
            "execution_court_name",
            "execution_court_case_no",
            "execution_court_courtroom",
            "execution_court_judge",
            "execution_court_clerk",
            "execution_court_filing_date",
            "execution_court_hearing_date",
        ):
            self.assertEqual(data.get(key), payload[key], f"{key} must be saved for completed criminal cases")


if __name__ == "__main__":
    unittest.main()
