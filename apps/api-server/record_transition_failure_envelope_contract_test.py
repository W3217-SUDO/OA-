"""Runtime contract for generic status-transition failure envelopes.

CodeGraph evidence:
- `codegraph explore "PostResponse IsSuccess Message status approval reject"`
  surfaced `Models/PostResponse.cs:10-27`: old write endpoints share an
  `IsSuccess/Data/Message` envelope and set `IsSuccess=false` plus
  `Message` when a business action fails.
- The same query showed old controllers such as
  `Areas/Account/Controllers/MessageCenterController.cs:163-177` returning
  failure through `PostResponse` rather than dropping the message body.

This red test locks the shared API gap: a failed generic transition must not
write status or audit rows, and it must preserve a legacy-compatible failure
envelope instead of only returning FastAPI's default `{"detail": "..."}`.
"""

import unittest

import httpx
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database import Base, get_db
from app.main import app
from app.models import BusinessRecord, User, WorkflowEvent
from app.security import current_identity


API = settings.api_prefix
IDENTITY = {
    "username": "transition-admin",
    "role": "admin",
    "display_name": "Transition Admin",
    "department": "Transition Department",
}


class RecordTransitionFailureEnvelopeContract(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with self.sessions() as db:
            db.add(
                User(
                    username=IDENTITY["username"],
                    display_name=IDENTITY["display_name"],
                    department=IDENTITY["department"],
                    role=IDENTITY["role"],
                    password_hash="x",
                    is_active=True,
                )
            )
            record = BusinessRecord(
                module="report",
                serial_no="TRANSITION-FAIL-001",
                title="Transition failure contract",
                customer="",
                status="生成中",
                owner=IDENTITY["username"],
                department=IDENTITY["department"],
                data={"kind": "status-envelope-contract"},
            )
            db.add(record)
            await db.commit()
            self.record_id = record.id
        app.dependency_overrides[get_db] = self.override_db
        app.dependency_overrides[current_identity] = lambda: IDENTITY
        self.client = httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://transition-envelope.test",
        )

    async def override_db(self):
        async with self.sessions() as db:
            yield db

    async def asyncTearDown(self):
        await self.client.aclose()
        app.dependency_overrides.clear()
        await self.engine.dispose()

    async def test_illegal_transition_keeps_audit_clean_and_returns_legacy_failure_envelope(self):
        response = await self.client.post(
            f"{API}/records/{self.record_id}/transition",
            json={"to_status": "已发布", "comment": "invalid direct publish"},
        )

        async with self.sessions() as db:
            record = await db.get(BusinessRecord, self.record_id)
            event_count = await db.scalar(
                select(func.count(WorkflowEvent.id)).where(WorkflowEvent.record_id == self.record_id)
            )
        self.assertEqual(record.status, "生成中")
        self.assertEqual(event_count, 0)

        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        self.assertEqual(payload["IsSuccess"], False)
        self.assertIn("不能从", payload["Message"])


if __name__ == "__main__":
    unittest.main()
