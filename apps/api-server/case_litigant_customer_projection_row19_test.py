"""8.27 row 19: case parties persist into personal/company customer ledgers."""

from __future__ import annotations

import unittest

import httpx
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database import Base, get_db
from app.main import app
from app.models import BusinessRecord, LegacyCustomer, SystemParameter, User, WorkflowEvent
from app.security import current_identity


API = settings.api_prefix
IDENTITY = {
    "username": "row19-admin",
    "role": "admin",
    "role_ids": ["admin"],
    "display_name": "第19行管理员",
    "department": "诉讼部",
}


class CaseLitigantCustomerProjectionRow19Test(unittest.IsolatedAsyncioTestCase):
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
            db.add_all([
                User(
                    username=IDENTITY["username"], display_name=IDENTITY["display_name"],
                    department=IDENTITY["department"], role="admin", role_ids=["admin"],
                    password_hash="x", profile={}, is_active=True,
                ),
                SystemParameter(category="customer_type", code="CUSTOMER", name="客户", sort_order=1, is_active=True),
                SystemParameter(category="customer_type", code="PARTY", name="当事人", sort_order=2, is_active=True),
                BusinessRecord(
                    module="customer", serial_no="CODEX-827-19-EXISTING", title="既有原告客户",
                    customer="既有原告客户", status="潜在", owner=IDENTITY["username"],
                    department=IDENTITY["department"],
                    data={"customer_type": "客户", "customer_managers": [IDENTITY["username"]]},
                ),
                BusinessRecord(
                    module="case", serial_no="CODEX-827-19-CASE", title="第19行当事人同步案件",
                    customer="既有原告客户", status="待立案审批", owner=IDENTITY["username"],
                    department=IDENTITY["department"],
                    data={"case_type": "民事案件", "case_creation_step": "basic"},
                ),
                BusinessRecord(
                    module="case", serial_no="CODEX-827-19-CRIMINAL", title="第19行刑事当事人案件",
                    customer="既有原告客户", status="侦查", owner=IDENTITY["username"],
                    department=IDENTITY["department"],
                    data={"case_type": "刑事案件", "case_creation_step": "completed"},
                ),
            ])
            await db.commit()
            self.case_id = await db.scalar(select(BusinessRecord.id).where(BusinessRecord.serial_no == "CODEX-827-19-CASE"))
            self.criminal_case_id = await db.scalar(select(BusinessRecord.id).where(BusinessRecord.serial_no == "CODEX-827-19-CRIMINAL"))

        self.previous_overrides = dict(app.dependency_overrides)
        app.dependency_overrides[get_db] = self.override_db
        app.dependency_overrides[current_identity] = lambda: IDENTITY
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://row19.test")

    async def asyncTearDown(self) -> None:
        await self.client.aclose()
        app.dependency_overrides.clear()
        app.dependency_overrides.update(self.previous_overrides)
        await self.engine.dispose()

    async def override_db(self):
        async with self.sessions() as db:
            yield db

    @staticmethod
    def payload() -> dict:
        return {
            "plaintiffs": ["既有原告客户"],
            "plaintiff_agents": ["原告代理律师（不入客户台账）"],
            "defendants": ["CODEX-827-19-张三"],
            "defendant_agents": ["被告代理律师（不入客户台账）"],
            "third_parties": ["CODEX-827-19-第三人", "CODEX-827-19-张三"],
            "third_party_agents": [],
            "comment": "CODEX-827-19 保存当事人",
        }

    async def test_new_parties_reach_mine_company_and_legacy_without_duplicates(self) -> None:
        first = await self.client.put(f"{API}/cases/{self.case_id}/litigants", json=self.payload())
        self.assertEqual(first.status_code, 200, first.text)
        second = await self.client.put(f"{API}/cases/{self.case_id}/litigants", json=self.payload())
        self.assertEqual(second.status_code, 200, second.text)

        async with self.sessions() as db:
            rows = list((await db.scalars(select(BusinessRecord).where(
                BusinessRecord.module == "customer",
                BusinessRecord.title.like("CODEX-827-19-%"),
            ))).all())
            self.assertEqual({row.title for row in rows}, {"CODEX-827-19-张三", "CODEX-827-19-第三人"})
            self.assertEqual(len(rows), 2)
            for row in rows:
                self.assertEqual(row.owner, IDENTITY["username"])
                self.assertEqual(row.department, IDENTITY["department"])
                self.assertEqual(row.data["customer_type"], "当事人")
                self.assertEqual(row.data["customer_managers"], [IDENTITY["username"]])
                self.assertEqual(row.data["customer_source"], "案件当事人")
            existing = await db.scalar(select(BusinessRecord).where(BusinessRecord.serial_no == "CODEX-827-19-EXISTING"))
            self.assertEqual(existing.data["customer_type"], "客户")
            self.assertEqual(await db.scalar(select(func.count()).select_from(BusinessRecord).where(
                BusinessRecord.module == "customer", BusinessRecord.title == "既有原告客户",
            )), 1)
            self.assertEqual(await db.scalar(select(func.count()).select_from(BusinessRecord).where(
                BusinessRecord.module == "customer", BusinessRecord.title.like("%代理律师%"),
            )), 0)
            legacy_names = set((await db.scalars(select(LegacyCustomer.CustomerName).where(
                LegacyCustomer.CustomerName.like("CODEX-827-19-%"),
            ))).all())
            self.assertEqual(legacy_names, {"CODEX-827-19-张三", "CODEX-827-19-第三人"})

        for scope in ("mine", "company"):
            response = await self.client.get(f"{API}/customers", params={
                "scope": scope, "customer_type": "当事人", "customer_name": "CODEX-827-19-张三",
            })
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual([item["title"] for item in response.json()["items"]], ["CODEX-827-19-张三"])

        conflict = await self.client.get(f"{API}/customers/conflicts", params={"name": "CODEX-827-19-张三"})
        self.assertEqual(conflict.status_code, 200, conflict.text)
        self.assertTrue(conflict.json()["found"])
        self.assertEqual(conflict.json()["latest_case_no"], "CODEX-827-19-CASE")
        self.assertEqual(conflict.json()["customer_managers"], [IDENTITY["display_name"]])

    async def test_missing_party_dictionary_rolls_back_case_and_customer_writes(self) -> None:
        async with self.sessions() as db:
            parameter = await db.scalar(select(SystemParameter).where(SystemParameter.name == "当事人"))
            parameter.is_active = False
            await db.commit()

        response = await self.client.put(f"{API}/cases/{self.case_id}/litigants", json=self.payload())
        self.assertEqual(response.status_code, 422, response.text)
        self.assertIn("当事人", response.text)
        async with self.sessions() as db:
            case = await db.get(BusinessRecord, self.case_id)
            self.assertNotIn("defendants", case.data)
            self.assertEqual(await db.scalar(select(func.count()).select_from(BusinessRecord).where(
                BusinessRecord.module == "customer", BusinessRecord.title.like("CODEX-827-19-%"),
            )), 0)
            self.assertEqual(await db.scalar(select(func.count()).select_from(WorkflowEvent)), 0)

    async def test_criminal_detail_uses_the_same_party_register(self) -> None:
        payload = {
            "plaintiffs": ["CODEX-827-19-刑事原告"],
            "plaintiff_agents": ["刑事原告代理人"],
            "defendants": ["CODEX-827-19-刑事被告"],
            "defendant_agents": [],
            "third_parties": [],
            "third_party_agents": [],
            "comment": "CODEX-827-19 刑事当事人同步",
        }
        response = await self.client.put(f"{API}/cases/{self.criminal_case_id}/criminal/litigants", json=payload)
        self.assertEqual(response.status_code, 200, response.text)
        async with self.sessions() as db:
            titles = set((await db.scalars(select(BusinessRecord.title).where(
                BusinessRecord.module == "customer",
                BusinessRecord.title.like("CODEX-827-19-刑事%"),
            ))).all())
            self.assertEqual(titles, {"CODEX-827-19-刑事原告", "CODEX-827-19-刑事被告"})
            self.assertEqual(await db.scalar(select(func.count()).select_from(BusinessRecord).where(
                BusinessRecord.module == "customer", BusinessRecord.title == "刑事原告代理人",
            )), 0)


if __name__ == "__main__":
    unittest.main()
