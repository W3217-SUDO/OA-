"""IPR case list page metadata contract.

CodeGraph evidence:
- Areas/IPR/Controllers/CaseListController.cs List initializes PageNo=1 and
  PageSize=15.
- CaseSearchList keeps PageNo/PageSize and TotalItemCount in the response
  payload after service pagination.
"""

from datetime import datetime, timedelta, timezone
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
    "username": "ipr-pages-admin",
    "role": "admin",
    "display_name": "IPR Pages Admin",
    "department": "IPR Department",
}


class IprCaseListPagesContract(unittest.IsolatedAsyncioTestCase):
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
            base_time = datetime(2026, 8, 4, 12, 0, tzinfo=timezone.utc)
            db.add_all(
                BusinessRecord(
                    module="ipr_case",
                    serial_no=f"IPR-PAGES-{index:03d}",
                    title=f"IPR pages contract case {index:03d}",
                    customer="IPR Pages Customer",
                    status="active",
                    owner=IDENTITY["username"],
                    department=IDENTITY["department"],
                    data={
                        "case_kind": "patent",
                        "application_no": f"APP-PAGES-{index:03d}",
                    },
                    created_at=base_time - timedelta(minutes=index),
                    updated_at=base_time - timedelta(minutes=index),
                )
                for index in range(16)
            )
            await db.commit()
        app.dependency_overrides[get_db] = self.override_db
        app.dependency_overrides[current_identity] = lambda: IDENTITY
        self.client = httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://ipr-pages.test",
        )

    async def override_db(self):
        async with self.sessions() as db:
            yield db

    async def asyncTearDown(self):
        await self.client.aclose()
        app.dependency_overrides.clear()
        await self.engine.dispose()

    async def test_ipr_cases_reports_pages_and_second_page_boundary(self):
        first = await self.client.get(f"{API}/ipr/cases?page=1&page_size=15")
        self.assertEqual(first.status_code, 200, first.text)
        first_payload = first.json()
        self.assertEqual(first_payload["total"], 16)
        self.assertEqual(first_payload["page"], 1)
        self.assertEqual(first_payload["page_size"], 15)
        self.assertEqual(first_payload["pages"], 2)
        self.assertEqual(len(first_payload["items"]), 15)
        self.assertEqual(first_payload["items"][0]["serial_no"], "IPR-PAGES-000")

        second = await self.client.get(f"{API}/ipr/cases?page=2&page_size=15")
        self.assertEqual(second.status_code, 200, second.text)
        second_payload = second.json()
        self.assertEqual(second_payload["total"], 16)
        self.assertEqual(second_payload["page"], 2)
        self.assertEqual(second_payload["page_size"], 15)
        self.assertEqual(second_payload["pages"], 2)
        self.assertEqual(len(second_payload["items"]), 1)
        self.assertEqual(second_payload["items"][0]["serial_no"], "IPR-PAGES-015")


if __name__ == "__main__":
    unittest.main()
