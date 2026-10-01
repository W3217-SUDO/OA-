"""Regression coverage for deleting tasks that already own investigation clues."""
from __future__ import annotations

import unittest

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models import BusinessRecord, InvestigationClueLink, User
from app.security import current_identity


class InvestigationBatchDeleteLinkedClueTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.identity = {
            "username": "batch-delete-admin",
            "role": "admin",
            "role_ids": ["admin"],
            "department": "调查部",
        }
        self.engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.sessions = async_sessionmaker(
            self.engine,
            expire_on_commit=False,
            class_=AsyncSession,
        )
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with self.sessions() as db:
            db.add(
                User(
                    username="batch-delete-admin",
                    display_name="批量删除管理员",
                    department="调查部",
                    role="admin",
                    role_ids=["admin"],
                    password_hash="x",
                    is_active=True,
                )
            )
            investigation = BusinessRecord(
                module="investigation",
                serial_no="CODEX-BATCH-DELETE-ROOT",
                title="调查任务",
                customer="测试客户",
                status="进行中",
                owner="batch-delete-admin",
                department="调查部",
                data={"publisher": "batch-delete-admin"},
            )
            db.add(investigation)
            await db.flush()
            linked_task = BusinessRecord(
                module="task",
                serial_no="CODEX-BATCH-DELETE-LINKED",
                title="已有线索的子任务",
                customer="测试客户",
                status="未开始",
                owner="batch-delete-admin",
                department="调查部",
                data={"initiator": "batch-delete-admin", "investigation_record_id": investigation.id},
            )
            deletable_task = BusinessRecord(
                module="task",
                serial_no="CODEX-BATCH-DELETE-PLAIN",
                title="可删除的子任务",
                customer="测试客户",
                status="未开始",
                owner="batch-delete-admin",
                department="调查部",
                data={"initiator": "batch-delete-admin", "investigation_record_id": investigation.id},
            )
            db.add_all([linked_task, deletable_task])
            await db.flush()
            clue = BusinessRecord(
                module="clue",
                serial_no="CODEX-BATCH-DELETE-CLUE",
                title="已关联线索",
                customer="测试客户",
                status="已转案件",
                owner="batch-delete-admin",
                department="调查部",
                data={"source_task_id": linked_task.id},
            )
            db.add(clue)
            await db.flush()
            db.add(
                InvestigationClueLink(
                    clue_record_id=clue.id,
                    task_record_id=linked_task.id,
                    investigation_record_id=investigation.id,
                    legacy_clue_no="CODEX-BATCH-DELETE-CLUE",
                )
            )
            await db.commit()
            self.linked_task_id = linked_task.id
            self.deletable_task_id = deletable_task.id
            self.clue_id = clue.id

        self.previous_overrides = dict(app.dependency_overrides)
        app.dependency_overrides[get_db] = self.override_db
        app.dependency_overrides[current_identity] = lambda: self.identity
        self.client = httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://batch-delete.test",
        )

    async def override_db(self):
        async with self.sessions() as db:
            yield db

    async def asyncTearDown(self):
        await self.client.aclose()
        app.dependency_overrides.clear()
        app.dependency_overrides.update(self.previous_overrides)
        await self.engine.dispose()

    async def test_linked_task_is_reported_while_unlinked_task_is_deleted(self):
        response = await self.client.post(
            "/api/v1/investigations/batch-delete",
            json={"record_ids": [self.linked_task_id, self.deletable_task_id]},
        )

        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["deleted"], 1)
        self.assertEqual(response.json()["failed"], 1)
        self.assertEqual(response.json()["errors"][0]["record_id"], self.linked_task_id)
        self.assertIn("已有调查线索", response.json()["errors"][0]["error"])
        async with self.sessions() as db:
            self.assertIsNotNone(await db.get(BusinessRecord, self.linked_task_id))
            self.assertIsNone(await db.get(BusinessRecord, self.deletable_task_id))
            self.assertIsNotNone(await db.get(BusinessRecord, self.clue_id))
            self.assertIsNotNone(
                await db.scalar(
                    select(InvestigationClueLink).where(
                        InvestigationClueLink.task_record_id == self.linked_task_id,
                    )
                )
            )


if __name__ == "__main__":
    unittest.main()
