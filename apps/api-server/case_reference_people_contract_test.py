"""Regression contract for active employee-only case people options."""

from __future__ import annotations

import unittest

import httpx
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import _resolve_active_case_people, app
from app.models import BusinessRecord, User
from app.security import current_identity


class CaseReferencePeopleContractTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.engine = create_async_engine(
            "sqlite+aiosqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.session_factory = async_sessionmaker(self.engine, class_=AsyncSession, expire_on_commit=False)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

        self.previous_overrides = dict(app.dependency_overrides)

        async def override_get_db():
            async with self.session_factory() as session:
                yield session

        async def override_identity():
            return {"username": "admin", "role": "admin", "display_name": "管理员", "department": "北京分所"}

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[current_identity] = override_identity
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://case-reference.test")

        async with self.session_factory() as session:
            session.add_all([
                User(username="fanwenling", display_name="范文玲", department="北京分所", password_hash="x", role="user", profile={"position": "律师"}, is_active=True),
                User(username="ghost-user", display_name="同部门旁观经理", department="北京分所", password_hash="x", role="user", profile={"position": "律师"}, is_active=True),
                User(username="former-user", display_name="离职员工", department="北京分所", password_hash="x", role="user", profile={"position": "律师"}, is_active=True),
                BusinessRecord(module="hr", serial_no="HR-REAL", title="范文玲", customer="", status="在职", owner="fanwenling", department="北京分所", description="", data={"username": "fanwenling"}),
                BusinessRecord(module="hr", serial_no="HR-REAL-DUP", title="范文玲", customer="", status="在职", owner="fanwenling", department="北京分所", description="", data={"username": "fanwenling"}),
                BusinessRecord(module="hr", serial_no="HR-FORMER", title="离职员工", customer="", status="离职", owner="former-user", department="北京分所", description="", data={"username": "former-user"}),
            ])
            await session.commit()

    async def asyncTearDown(self) -> None:
        await self.client.aclose()
        app.dependency_overrides.clear()
        app.dependency_overrides.update(self.previous_overrides)
        await self.engine.dispose()

    async def test_directory_uses_hr_records_while_case_picker_uses_active_accounts(self) -> None:
        directory = await self.client.get("/api/v1/users/directory")
        self.assertEqual(directory.status_code, 200, directory.text)
        self.assertEqual([item["username"] for item in directory.json()["items"]], ["fanwenling"])
        self.assertEqual(directory.json()["items"][0]["display_name"], "范文玲")

        options = await self.client.get("/api/v1/cases/reference-options")
        self.assertEqual(options.status_code, 200, options.text)
        payload = options.json()
        self.assertEqual(
            payload["case_assistants"],
            [
                {"value": "ghost-user", "label": "同部门旁观经理（北京分所）", "position": "律师"},
                {"value": "former-user", "label": "离职员工（北京分所）", "position": "律师"},
                {"value": "fanwenling", "label": "范文玲（北京分所）", "position": "律师"},
            ],
        )
        self.assertEqual(payload["case_lawyers"], payload["case_assistants"])

    async def test_active_migrated_person_does_not_require_hr_position_text(self) -> None:
        async with self.session_factory() as session:
            migrated = User(
                username="legacy-lawyer",
                display_name="历史经办人",
                department="北京分所",
                password_hash="x",
                role="user",
                profile={"migration_source": "legacy"},
                is_active=True,
            )
            inactive = User(
                username="inactive-lawyer",
                display_name="停用经办人",
                department="北京分所",
                password_hash="x",
                role="user",
                profile={"position": "律师"},
                is_active=False,
            )
            session.add_all([migrated, inactive])
            await session.commit()

            labels, usernames = await _resolve_active_case_people(
                ["历史经办人"], session, field_name="经办律师"
            )
            self.assertEqual(labels, ["历史经办人"])
            self.assertEqual(usernames, ["legacy-lawyer"])

            with self.assertRaisesRegex(Exception, "停用"):
                await _resolve_active_case_people(
                    ["inactive-lawyer"], session, field_name="经办律师"
                )

    async def test_conflicting_hr_archive_cannot_hide_account_display_name(self) -> None:
        async with self.session_factory() as session:
            session.add_all([
                User(username="fwl", display_name="范文林", department="财务部", password_hash="x", role="user", is_active=True),
                BusinessRecord(module="hr", serial_no="HR-FWL-1", title="范文林", customer="", status="在职", owner="fwl", department="财务部", description="", data={"username": "fwl"}),
                BusinessRecord(module="hr", serial_no="HR-FWL-2", title="范文玲", customer="", status="在职", owner="fwl", department="财务部", description="", data={"username": "fwl"}),
            ])
            await session.commit()

        options = await self.client.get("/api/v1/cases/reference-options")
        self.assertEqual(options.status_code, 200, options.text)
        fwl_options = [item for item in options.json()["case_assistants"] if item["value"] == "fwl"]
        self.assertEqual(fwl_options, [{"value": "fwl", "label": "范文林（财务部）", "position": ""}])


if __name__ == "__main__":
    unittest.main()
