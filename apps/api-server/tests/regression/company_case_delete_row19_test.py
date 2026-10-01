import unittest
from datetime import date

import httpx
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy import select

from app.config import settings
from app.database import Base, get_db
from app.main import app
from app.models import BusinessRecord, HearingSchedule, Notification, WorkflowEvent
from app.security import current_identity


IDENTITY = {"username": "CODEX-812-ROW19-admin", "display_name": "第19行验收管理员", "role": "admin", "department": "上海分所"}


class CompanyCaseDeleteRow19Test(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with self.sessions() as db:
            case = BusinessRecord(module="case", serial_no="CODEX-812-ROW19-CASE", title="CODEX-812-ROW19-CASE", customer="CODEX-812-ROW19-CUSTOMER", status="新案待分配", owner=IDENTITY["username"], department=IDENTITY["department"], data={"case_type": "民事案件"})
            db.add(case)
            await db.flush()
            db.add(BusinessRecord(module="task", serial_no="CODEX-812-ROW19-TASK", title="CODEX-812-ROW19-TASK", customer=case.customer, status="待接收", owner=IDENTITY["username"], department=case.department, data={"case_id": case.id}))
            db.add(WorkflowEvent(record_id=case.id, action="CODEX-812-ROW19", from_status=case.status, to_status=case.status, operator=IDENTITY["username"], comment=""))
            db.add(Notification(source_key="CODEX-812-ROW19", source_type="case", source_id=case.id, recipient=IDENTITY["username"], title="CODEX-812-ROW19", content="CODEX-812-ROW19"))
            db.add(HearingSchedule(case_record_id=case.id, hearing_date=date(2026, 8, 13), hearing_time="09:00", court="CODEX-812-ROW19", courtroom="1", hearing_type="一审开庭", hearing_lawyer=IDENTITY["username"]))
            await db.commit()
            self.case_id = case.id

        async def override_db():
            async with self.sessions() as db:
                yield db

        app.dependency_overrides[get_db] = override_db
        app.dependency_overrides[current_identity] = lambda: IDENTITY
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://row19.test")

    async def asyncTearDown(self):
        await self.client.aclose()
        app.dependency_overrides.clear()
        await self.engine.dispose()

    async def test_delete_case_cascades_case_owned_records(self):
        response = await self.client.delete(f"{settings.api_prefix}/cases/{self.case_id}")
        self.assertEqual(response.status_code, 204, response.text)
        async with self.sessions() as db:
            self.assertIsNone(await db.get(BusinessRecord, self.case_id))
            self.assertEqual((await db.scalars(select(BusinessRecord).where(BusinessRecord.serial_no.like("CODEX-812-ROW19-%")))).all(), [])
            self.assertEqual((await db.scalars(select(WorkflowEvent).where(WorkflowEvent.record_id == self.case_id))).all(), [])
            self.assertEqual((await db.scalars(select(HearingSchedule).where(HearingSchedule.case_record_id == self.case_id))).all(), [])


if __name__ == "__main__":
    unittest.main()
