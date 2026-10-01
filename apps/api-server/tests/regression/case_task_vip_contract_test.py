"""VIP case-task creation, filtering, and customer-inheritance contract."""

from __future__ import annotations

from datetime import date, timedelta
import unittest

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database import Base, get_db
from app.main import app
from app.models import BusinessRecord, User
from app.security import current_identity


ADMIN = {"username": "vip-task-admin", "role": "admin", "display_name": "VIP Task Admin", "department": "测试部"}


class CaseTaskVipContractTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with self.sessions() as db:
            db.add(User(username=ADMIN["username"], password_hash="x", display_name=ADMIN["display_name"], role="admin", department=ADMIN["department"], is_active=True))
            db.add(User(username="vip-task-other", password_hash="x", display_name="VIP Task Other", role="user", department=ADMIN["department"], is_active=True))
            customer = BusinessRecord(module="customer", serial_no="CODEX-VIP-CUSTOMER", title="CODEX VIP Customer", customer="CODEX VIP Customer", status="正常", owner=ADMIN["username"], department=ADMIN["department"], data={"is_vip": True})
            db.add(customer)
            await db.flush()
            case = BusinessRecord(module="case", serial_no="CODEX-VIP-CASE", title="CODEX VIP Case", customer=customer.title, status="待立案审批", owner=ADMIN["username"], department=ADMIN["department"], data={"customer_id": customer.id, "handling_lawyer_usernames": [ADMIN["username"]], "case_team_usernames": [ADMIN["username"]]})
            db.add(case)
            await db.flush()
            self.case_id = case.id
            await db.commit()
        self.previous_overrides = dict(app.dependency_overrides)
        app.dependency_overrides[get_db] = self.override_db
        self.identity = ADMIN
        app.dependency_overrides[current_identity] = lambda: self.identity
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://vip-task.test")

    async def asyncTearDown(self) -> None:
        await self.client.aclose()
        app.dependency_overrides.clear()
        app.dependency_overrides.update(self.previous_overrides)
        await self.engine.dispose()

    async def override_db(self):
        async with self.sessions() as db:
            yield db

    async def test_vip_customer_is_inherited_and_filters_are_persistent(self) -> None:
        created = await self.client.post(f"{settings.api_prefix}/tasks", json={
            "title": "CODEX VIP task", "owner": ADMIN["username"], "deadline": str(date.today() + timedelta(days=7)),
            "source": "案件任务", "case_record_id": self.case_id, "is_vip": False,
        })
        self.assertEqual(created.status_code, 201, created.text)
        task_id = created.json()["id"]
        self.assertTrue(created.json()["is_vip"])

        vip_list = await self.client.get(f"{settings.api_prefix}/cases/{self.case_id}/tasks?scope=case&is_vip=true")
        self.assertEqual(vip_list.status_code, 200, vip_list.text)
        self.assertEqual([item["id"] for item in vip_list.json()["items"]], [task_id])
        normal_list = await self.client.get(f"{settings.api_prefix}/cases/{self.case_id}/tasks?scope=case&is_vip=false")
        self.assertEqual(normal_list.status_code, 200, normal_list.text)
        self.assertEqual(normal_list.json()["total"], 0)

        updated = await self.client.post(f"{settings.api_prefix}/tasks/batch-update", json={"task_ids": [task_id], "is_vip": False})
        self.assertEqual(updated.status_code, 200, updated.text)
        self.assertTrue(updated.json()["items"][0]["is_vip"])
        async with self.sessions() as db:
            task = await db.scalar(select(BusinessRecord).where(BusinessRecord.id == task_id))
            self.assertTrue((task.data or {}).get("is_vip"))

    async def test_manual_and_legacy_normal_tasks_filter_and_preserve_permissions(self) -> None:
        async with self.sessions() as db:
            customer = BusinessRecord(module="customer", serial_no="CODEX-NORMAL-CUSTOMER", title="CODEX Normal Customer", customer="CODEX Normal Customer", status="正常", owner=ADMIN["username"], department=ADMIN["department"], data={"level": "重点客户"})
            db.add(customer)
            await db.flush()
            normal_case = BusinessRecord(module="case", serial_no="CODEX-NORMAL-CASE", title="CODEX Normal Case", customer=customer.title, status="待立案审批", owner=ADMIN["username"], department=ADMIN["department"], data={"customer_id": customer.id, "handling_lawyer_usernames": [ADMIN["username"]], "case_team_usernames": [ADMIN["username"]]})
            stale_id_case = BusinessRecord(module="case", serial_no="CODEX-STALE-ID-CASE", title="CODEX Stale Id Case", customer="CODEX VIP Customer", status="待立案审批", owner=ADMIN["username"], department=ADMIN["department"], data={"customer_id": 999999, "handling_lawyer_usernames": [ADMIN["username"]], "case_team_usernames": [ADMIN["username"]]})
            db.add_all([normal_case, stale_id_case])
            await db.flush()
            normal_case_id, stale_id_case_id = normal_case.id, stale_id_case.id
            db.add(BusinessRecord(module="task", serial_no="CODEX-LEGACY-NORMAL", title="CODEX legacy normal", customer=customer.title, status="待处理", owner=ADMIN["username"], department=ADMIN["department"], data={"case_id": normal_case_id, "case_no": normal_case.serial_no, "source": "案件任务", "initiator": ADMIN["username"]}))
            await db.commit()

        manual = await self.client.post(f"{settings.api_prefix}/tasks", json={
            "title": "CODEX manual VIP", "owner": ADMIN["username"], "deadline": str(date.today() + timedelta(days=7)),
            "source": "案件任务", "case_record_id": normal_case_id, "is_vip": True,
        })
        self.assertEqual(manual.status_code, 201, manual.text)
        task_id = manual.json()["id"]
        self.assertTrue(manual.json()["is_vip"])

        cleared = await self.client.post(f"{settings.api_prefix}/tasks/batch-update", json={"task_ids": [task_id], "is_vip": False})
        self.assertEqual(cleared.status_code, 200, cleared.text)
        self.assertFalse(cleared.json()["items"][0]["is_vip"])
        normal_list = await self.client.get(f"{settings.api_prefix}/cases/{normal_case_id}/tasks?scope=case&is_vip=false&page=1&page_size=1")
        self.assertEqual(normal_list.status_code, 200, normal_list.text)
        self.assertEqual(normal_list.json()["total"], 2)
        self.assertEqual(len(normal_list.json()["items"]), 1)
        self.assertEqual(normal_list.json()["pages"], 2)

        stale = await self.client.post(f"{settings.api_prefix}/tasks", json={
            "title": "CODEX stale customer id", "owner": ADMIN["username"], "deadline": str(date.today() + timedelta(days=7)),
            "source": "案件任务", "case_record_id": stale_id_case_id, "is_vip": False,
        })
        self.assertEqual(stale.status_code, 201, stale.text)
        self.assertFalse(stale.json()["is_vip"])

        self.identity = {"username": "vip-task-other", "role": "user", "display_name": "VIP Task Other", "department": ADMIN["department"]}
        blocked = await self.client.post(f"{settings.api_prefix}/tasks/batch-update", json={"task_ids": [task_id], "is_vip": True})
        self.assertEqual(blocked.status_code, 403, blocked.text)


if __name__ == "__main__":
    unittest.main()
