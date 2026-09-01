"""9.1 row 5: ordinary cases retain ordered assistants and project the latest."""

from __future__ import annotations

import unittest

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.main import CaseNormalBasicInput, _case_assistant_display, _case_team_role, update_normal_case_basic
from app.models import BusinessRecord, User


ADMIN = {"username": "admin", "role": "admin", "display_name": "管理员", "department": "上海分所"}


class CaseMultipleAssistantsRow5Test(unittest.IsolatedAsyncioTestCase):
    def test_scalar_projection_missing_only_tracks_latest_assistant(self) -> None:
        users = {
            "latest": User(
                username="latest", display_name="最新助理", department="上海分所",
                role="user", password_hash="x", is_active=True,
            )
        }
        display, missing = _case_assistant_display(
            {"assistant_usernames": ["latest", "unresolved-old"]}, users
        )
        self.assertEqual(display, "最新助理")
        self.assertFalse(missing)

        display, missing = _case_assistant_display(
            {"assistant_usernames": ["unresolved-latest", "latest"]}, users
        )
        self.assertTrue(missing)

    async def asyncSetUp(self) -> None:
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

    async def asyncTearDown(self) -> None:
        await self.engine.dispose()

    async def test_latest_assistant_is_scalar_projection_and_all_remain_team_members(self) -> None:
        async with self.sessions() as db:
            customer = BusinessRecord(module="customer", serial_no="CODEX-901-R5-CUSTOMER", title="第5行客户", customer="第5行客户", status="正常", owner="admin", department="上海分所", data={})
            case = BusinessRecord(module="case", serial_no="CODEX-901-R5-CASE", title="第5行案件", customer="第5行客户", status="办理中", owner="admin", department="上海分所", data={"case_type":"民事案件","customer_record_id":1,"cause_or_charge":"合同纠纷","handling_lawyers":["管理员"],"handling_lawyer_usernames":["admin"],"assistant":"旧助理","assistant_username":"old"})
            db.add_all([customer, case,
                User(username="admin", display_name="管理员", department="上海分所", role="admin", password_hash="x", is_active=True),
                User(username="new", display_name="最新助理", department="上海分所", role="user", password_hash="x", is_active=True),
                User(username="old", display_name="旧助理", department="上海分所", role="user", password_hash="x", is_active=True),
            ])
            await db.commit()
            result = await update_normal_case_basic(case.id, CaseNormalBasicInput(customer_record_id=customer.id,title=case.title,case_phase=case.status,cause_or_charge="合同纠纷",handling_lawyers=["admin"],assistants=["new","old"]), ADMIN, db)
            await db.refresh(case)
            old_role = await _case_team_role(case, {"username":"old","role":"user","display_name":"旧助理","department":"上海分所"}, db)

        self.assertEqual(case.data["assistants"], ["最新助理", "旧助理"])
        self.assertEqual(case.data["assistant_usernames"], ["new", "old"])
        self.assertEqual(case.data["assistant"], "最新助理")
        self.assertEqual(case.data["assistant_username"], "new")
        self.assertEqual(case.data["case_team_usernames"], ["admin", "new", "old"])
        self.assertEqual(result["data"]["assistant"], "最新助理")
        self.assertEqual(_case_assistant_display(case.data, {})[0], "最新助理")
        self.assertEqual(old_role, "assistant")


if __name__ == "__main__":
    unittest.main()
