"""IPR detail child-list pagination contract.

CodeGraph evidence:
- Areas/IPR/Controllers/CaseController.cs CaseFileList accepts pageNo/pageSize,
  defaults to 1/15, sets TotalCount, then Skip/Take's the case files.
- Areas/IPR/Controllers/CaseController.cs CaseAssistedFeeList accepts
  pageNo/pageSize, defaults to 1/15, sets TotalCount, then Skip/Take's assisted
  fees.
- Areas/IPR/Controllers/CaseController.cs CaseEventList is the legacy event
  reminder-style detail list; the new dedicated reminder endpoint must expose
  the same server-page envelope used by the IPR detail child lists.
"""

from datetime import date, datetime, timedelta, timezone
import unittest

import httpx
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database import Base, get_db
from app.main import app
from app.models import BusinessRecord, FileAttachment, IprCaseAssistedFee, IprCaseReminder
from app.security import current_identity


API = settings.api_prefix
IDENTITY = {
    "username": "ipr-detail-pages-admin",
    "role": "admin",
    "display_name": "IPR Detail Pages Admin",
    "department": "IPR Department",
}


class IprCaseDetailListsPaginationContract(unittest.IsolatedAsyncioTestCase):
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
            case = BusinessRecord(
                module="ipr_case",
                serial_no="IPR-DETAIL-PAGES-001",
                title="IPR detail child-list pagination case",
                customer="IPR Detail Customer",
                status="在办",
                owner=IDENTITY["username"],
                department=IDENTITY["department"],
                data={"case_kind": "patent", "application_no": "APP-DETAIL-PAGES"},
                created_at=base_time,
                updated_at=base_time,
            )
            db.add(case)
            await db.flush()
            self.case_id = case.id

            for index in range(16):
                db.add(
                    FileAttachment(
                        record_id=case.id,
                        category="IPR 文件",
                        file_type_code="official",
                        original_name=f"detail-file-{index:03d}.pdf",
                        stored_name=f"detail-file-{index:03d}.pdf",
                        content_type="application/pdf",
                        size=100 + index,
                        path=f"/tmp/detail-file-{index:03d}.pdf",
                        uploader=IDENTITY["username"],
                        document_date=date(2026, 8, 4) - timedelta(days=index),
                        created_at=base_time - timedelta(minutes=index),
                    )
                )
                db.add(
                    IprCaseReminder(
                        case_record_id=case.id,
                        event_type_id=index + 1,
                        event_type="自定义提醒",
                        reminder_date=date(2026, 8, 4) + timedelta(days=index),
                        deadline=date(2026, 9, 4) + timedelta(days=index),
                        content=f"detail reminder {index:03d}",
                        creator=IDENTITY["username"],
                        created_at=base_time - timedelta(minutes=index),
                        updated_at=base_time - timedelta(minutes=index),
                    )
                )
                db.add(
                    IprCaseAssistedFee(
                        case_record_id=case.id,
                        assisted_type=f"资助类别 {index:03d}",
                        status="待办理",
                        request_date=date(2026, 8, 4) - timedelta(days=index),
                        request_user=IDENTITY["username"],
                        response_user="",
                        remark=f"detail assisted fee {index:03d}",
                        created_at=base_time - timedelta(minutes=index),
                        updated_at=base_time - timedelta(minutes=index),
                    )
                )
            await db.commit()

        app.dependency_overrides[get_db] = self.override_db
        app.dependency_overrides[current_identity] = lambda: IDENTITY
        self.client = httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://ipr-detail-pages.test",
        )

    async def override_db(self):
        async with self.sessions() as db:
            yield db

    async def asyncTearDown(self):
        await self.client.aclose()
        app.dependency_overrides.clear()
        await self.engine.dispose()

    async def test_detail_lists_return_server_page_envelope_and_second_page(self):
        endpoints = {
            "files": f"{API}/ipr/cases/{self.case_id}/files",
            "reminders": f"{API}/ipr/cases/{self.case_id}/reminders",
            "assisted_fees": f"{API}/ipr/cases/{self.case_id}/assisted-fees",
        }
        issues = []
        for name, url in endpoints.items():
            for page, expected_count in ((1, 15), (2, 1)):
                response = await self.client.get(url, params={"page": page, "page_size": 15})
                if response.status_code != 200:
                    issues.append(f"{name} page {page}: expected HTTP 200, got {response.status_code}: {response.text}")
                    continue
                payload = response.json()
                missing = [key for key in ("total", "page", "page_size", "pages") if key not in payload]
                if missing:
                    issues.append(f"{name} page {page}: missing page envelope keys {missing}; keys={sorted(payload.keys())}")
                else:
                    expected_meta = {"total": 16, "page": page, "page_size": 15, "pages": 2}
                    actual_meta = {key: payload[key] for key in expected_meta}
                    if actual_meta != expected_meta:
                        issues.append(f"{name} page {page}: expected {expected_meta}, got {actual_meta}")
                item_count = len(payload.get("items", []))
                if item_count != expected_count:
                    issues.append(f"{name} page {page}: expected {expected_count} items, got {item_count}")
        self.assertFalse(issues, "\n".join(issues))


if __name__ == "__main__":
    unittest.main()
