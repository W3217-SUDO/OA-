"""8.13 row 11: clue writes follow effective account/menu action grants."""

import unittest

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.main import (
    RecordInput,
    RecordUpdate,
    TaskActionInput,
    create_investigation_record,
    submit_investigation_clue,
    update_investigation_record,
)
from app.models import BusinessRecord, JobRole, User


def identity(username: str) -> dict:
    return {"username": username, "role": "user"}


class InvestigationCluePermissionRow11Test(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.sessions = async_sessionmaker(
            self.engine, expire_on_commit=False, class_=AsyncSession
        )
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

    async def asyncTearDown(self):
        await self.engine.dispose()

    @staticmethod
    def _source_task(username: str) -> BusinessRecord:
        return BusinessRecord(
            module="task", serial_no=f"RW-ROW11-{username}",
            title="调查子任务", customer="CODEX客户", status="进行中",
            owner=username, department="调查部",
            data={"investigation_record_id": 11},
        )

    @staticmethod
    def _clue_input(source_task_id: int, title: str) -> RecordInput:
        return RecordInput(
            module="clue", serial_no="ignored", title=title, customer="",
            owner="", data={
                "source_task_id": source_task_id,
                "platform": "淘宝",
                "product": "CODEX产品",
            },
        )

    async def test_effective_clue_menu_grant_can_create_submit_and_resubmit(self):
        async with self.sessions() as db:
            menu_user = User(
                username="row11-menu", display_name="菜单授权用户",
                department="调查部", password_hash="x", role="user",
                profile={"permission_overrides": {"menu_keys": ["clue"]}},
            )
            source_task = self._source_task(menu_user.username)
            db.add_all([menu_user, source_task])
            await db.commit()

            created = await create_investigation_record(
                self._clue_input(source_task.id, "菜单授权线索"),
                identity(menu_user.username), db,
            )
            submitted = await submit_investigation_clue(
                created["id"], TaskActionInput(comment="提交审批"),
                identity(menu_user.username), db,
            )

            clue = await db.get(BusinessRecord, created["id"])
            clue.status = "已驳回"
            await db.commit()
            resubmitted = await update_investigation_record(
                clue.id, RecordUpdate(status="待审批"), identity(menu_user.username), db,
            )

        self.assertEqual(submitted["status"], "待审批")
        self.assertEqual(resubmitted["status"], "待审批")

    async def test_explicit_submit_action_can_create_without_menu_override(self):
        async with self.sessions() as db:
            action_role = JobRole(
                code="ROW11-CLUE-ACTION", name="线索提交岗位",
                permissions=["线索提交"], is_active=True,
            )
            action_user = User(
                username="row11-action", display_name="动作授权用户",
                department="调查部", password_hash="x", role="user",
                profile={
                    "position": action_role.name,
                    "permission_overrides": {"menu_keys": []},
                },
            )
            source_task = self._source_task(action_user.username)
            db.add_all([action_role, action_user, source_task])
            await db.commit()

            created = await create_investigation_record(
                self._clue_input(source_task.id, "动作授权线索"),
                identity(action_user.username), db,
            )

        self.assertEqual(created["owner"], action_user.username)
        self.assertEqual(created["status"], "草稿")

    async def test_account_without_clue_menu_or_action_is_denied(self):
        async with self.sessions() as db:
            denied_user = User(
                username="row11-denied", display_name="无授权用户",
                department="调查部", password_hash="x", role="user",
                profile={"permission_overrides": {"menu_keys": []}},
            )
            source_task = self._source_task(denied_user.username)
            db.add_all([denied_user, source_task])
            await db.commit()

            with self.assertRaises(HTTPException) as captured:
                await create_investigation_record(
                    self._clue_input(source_task.id, "无授权线索"),
                    identity(denied_user.username), db,
                )

        self.assertEqual(captured.exception.status_code, 403)


if __name__ == "__main__":
    unittest.main()
