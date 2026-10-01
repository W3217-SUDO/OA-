"""8.14 row 5: case-linked task lists expose the complete case context."""

from __future__ import annotations

from datetime import date, timedelta
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
ADMIN = {
    "username": "row5-admin",
    "role": "admin",
    "display_name": "Row 5 Admin",
    "department": "诉讼部",
}


class TaskCaseElementsRow5Test(unittest.IsolatedAsyncioTestCase):
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
            db.add(User(
                username=ADMIN["username"], display_name=ADMIN["display_name"],
                department=ADMIN["department"], role="admin", password_hash="x", is_active=True,
            ))
            case = BusinessRecord(
                module="case", serial_no="CODEX-814-R5-CASE", title="Row 5 Case",
                customer="Row 5 Customer", status="办理中", owner=ADMIN["username"],
                department=ADMIN["department"],
                data={
                    "plaintiffs": ["原告甲", "原告乙"],
                    "defendants": ["被告甲"],
                    "case_stage": "一审立案",
                    "case_team_usernames": [ADMIN["username"]],
                },
            )
            db.add(case)
            await db.flush()
            db.add(BusinessRecord(
                module="task", serial_no="CODEX-814-R5-TASK", title="案件任务",
                customer=case.customer, status="待接收", owner=ADMIN["username"],
                department=ADMIN["department"],
                data={
                    "deadline": str(date.today() + timedelta(days=7)),
                    "priority": "普通", "source": "案件任务",
                    "initiator": ADMIN["username"], "collaborators": [],
                    "case_record_id": case.id, "case_no": case.serial_no,
                },
            ))
            await db.commit()
            self.case_id = case.id
        self.previous_overrides = dict(app.dependency_overrides)
        app.dependency_overrides[get_db] = self.override_db
        app.dependency_overrides[current_identity] = lambda: ADMIN
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://row5.test")

    async def override_db(self):
        async with self.sessions() as db:
            yield db

    async def asyncTearDown(self) -> None:
        await self.client.aclose()
        app.dependency_overrides.clear()
        app.dependency_overrides.update(self.previous_overrides)
        await self.engine.dispose()

    async def test_task_list_enriches_case_elements_from_linked_case(self) -> None:
        response = await self.client.get(f"{API}/tasks", params={"serial_no": "CODEX-814-R5-TASK"})
        self.assertEqual(response.status_code, 200, response.text)
        row = response.json()["items"][0]
        self.assertEqual(row["case_no"], "CODEX-814-R5-CASE")
        self.assertEqual(row["plaintiff"], "原告甲、原告乙")
        self.assertEqual(row["defendant"], "被告甲")
        self.assertEqual(row["case_stage"], "一审立案")

        case_tasks = await self.client.get(f"{API}/cases/{self.case_id}/tasks")
        self.assertEqual(case_tasks.status_code, 200, case_tasks.text)
        self.assertEqual(case_tasks.json()["items"][0]["plaintiff"], "原告甲、原告乙")


if __name__ == "__main__":
    unittest.main()
