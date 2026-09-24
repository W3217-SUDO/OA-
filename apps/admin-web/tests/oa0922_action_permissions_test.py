"""9.22 案件文档、操作菜单和票据上传动作权限。"""

import unittest
from unittest.mock import AsyncMock, patch

import httpx
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.constants import SYSTEM_ACTION_BY_CODE
from app.database import Base, get_db
from app.main import app
from app.models import BusinessRecord
from app.security import current_identity


class CaseActionPermissionsTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool,
        )
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.previous_overrides = dict(app.dependency_overrides)
        app.dependency_overrides[get_db] = self.override_db
        app.dependency_overrides[current_identity] = lambda: {
            "username": "CODEX-0922-reader", "role": "user", "role_ids": ["user"], "department": "测试部",
        }
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://actions.test")

    async def asyncTearDown(self):
        await self.client.aclose()
        app.dependency_overrides.clear()
        app.dependency_overrides.update(self.previous_overrides)
        await self.engine.dispose()

    async def override_db(self):
        async with self.sessions() as db:
            yield db

    async def test_receipt_action_is_under_receipt_menu_and_upload_denied_without_grant(self):
        self.assertEqual(SYSTEM_ACTION_BY_CODE["case.fee.receipt.upload"]["menu_key"], "case-files-receipt")
        response = await self.client.post(
            "/api/v1/finance/receipt-files/batch",
            data={"fee_ids": "1", "bill_no": "CODEX-0922-bill", "bill_date": "2026-09-25"},
            files={"file": ("CODEX-0922-bill.pdf", b"x", "application/pdf")},
        )
        self.assertEqual(response.status_code, 403, response.text)

    async def test_delete_requires_its_own_action_and_admin_passes_action_gate(self):
        response = await self.client.post(
            "/api/v1/cases/attachments/delete", json={"attachment_ids": [123]},
        )
        self.assertEqual(response.status_code, 403, response.text)
        app.dependency_overrides[current_identity] = lambda: {
            "username": "admin", "role": "admin", "role_ids": ["admin"], "department": "测试部",
        }
        response = await self.client.post(
            "/api/v1/cases/attachments/delete", json={"attachment_ids": [123]},
        )
        self.assertEqual(response.status_code, 404, response.text)

    async def test_detail_actions_are_in_case_tree_and_document_manage_is_independent(self):
        for action in (
            "case.court.update", "case.notary.update", "case.litigants.update",
            "case.settlement.update", "case.criminal.public_security.update",
            "case.criminal.procuratorate.update", "case.criminal.court.update",
            "case.document.manage",
        ):
            self.assertEqual(SYSTEM_ACTION_BY_CODE[action]["menu_key"], "case-mine")
        record = BusinessRecord(
            id=1, module="case", serial_no="CODEX-0922-case", title="CODEX-0922-case",
            owner="CODEX-0922-reader", department="测试部", status="在办", data={},
        )
        with patch("app.core.permissions._ensure_record_module", new=AsyncMock(return_value=record)):
            response = await self.client.post(
                "/api/v1/cases/1/document-folders", json={"name": "CODEX-0922-folder"},
            )
            court_response = await self.client.put(
                "/api/v1/cases/1/court-info", json={"first_instance_court": "CODEX-0922-court"},
            )
        self.assertEqual(response.status_code, 403, response.text)
        self.assertEqual(court_response.status_code, 403, court_response.text)


if __name__ == "__main__":
    unittest.main()
