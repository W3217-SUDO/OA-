"""9.22 第11、12行：通知目标按参与关系导航，任务角标按可见任务去重。"""

import unittest
from datetime import date, timedelta

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database import Base, get_db
from app.main import app
from app.models import BusinessRecord, ContractApprovalStep, Notification, User
from app.security import current_identity


class NotificationRows11And12Test(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine(
            "sqlite+aiosqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

        self.owner = "CODEX-922-notice-owner"
        self.initiator = "CODEX-922-notice-initiator"
        self.admin = "CODEX-922-notice-admin"
        async with self.sessions() as db:
            db.add_all([
                User(username=self.owner, display_name="任务负责人", role="user", password_hash="x", is_active=True),
                User(username=self.initiator, display_name="任务发起人", role="user", password_hash="x", is_active=True),
                User(username=self.admin, display_name="管理员", role="admin", password_hash="x", is_active=True),
            ])
            db.add(BusinessRecord(
                module="contract", serial_no="CODEX-922-NOTICE-CONTRACT", title="审批合同",
                owner=self.owner, status="审批中", data={},
            ))
            await db.flush()
            contract = await db.scalar(select(BusinessRecord).where(BusinessRecord.serial_no == "CODEX-922-NOTICE-CONTRACT"))
            step = ContractApprovalStep(contract_record_id=contract.id, step_order=1, approver=self.owner, status="待审批")
            db.add(step)
            await db.flush()
            db.add(Notification(
                source_key=f"contract-approval-{contract.id}-{step.id}-{self.admin}",
                source_type="contract", source_id=contract.id, sender="system", recipient=self.admin,
                title="不属于管理员的审批", content="旧通知", is_read=False,
            ))
            case = BusinessRecord(
                module="case", serial_no="CODEX-922-NOTICE-CASE", title="公司案件开庭提醒",
                owner=self.owner, status="待立案", data={},
            )
            db.add(case)
            await db.flush()
            self.case_id = case.id
            db.add(Notification(
                source_key=f"case-hearing-{case.id}-{self.owner}",
                source_type="case", source_id=case.id, sender="system", recipient=self.owner,
                title="开庭提醒", content="公司案件", is_read=False,
            ))
            today = date.today()
            tasks = []
            for suffix, owner, initiator, source in (
                ("accepted", self.owner, self.initiator, "案件任务"),
                ("investigation", self.owner, self.initiator, "调查任务"),
                ("created", self.initiator, self.owner, "日常任务"),
            ):
                task = BusinessRecord(
                    module="task", serial_no=f"CODEX-922-NOTICE-TASK-{suffix}", title=suffix,
                    owner=owner, status="待处理",
                    data={"source": source, "initiator": initiator,
                          "deadline": (today + timedelta(days=30)).isoformat(),
                          **({"investigation_record_id": 12} if source == "调查任务" else {})},
                )
                db.add(task)
                await db.flush()
                tasks.append(task)
            self.accepted_task_id = tasks[0].id
            self.accepted_task_serial = tasks[0].serial_no
            self.investigation_task_id = tasks[1].id
            completed = BusinessRecord(
                module="task", serial_no="CODEX-922-NOTICE-TASK-completed", title="已验收任务",
                owner=self.owner, status="已验收",
                data={"source": "日常任务", "initiator": self.initiator,
                      "deadline": (today - timedelta(days=1)).isoformat()},
            )
            db.add(completed)
            await db.flush()
            for sequence, task in enumerate((tasks[0], tasks[0], tasks[1], tasks[2]), start=1):
                db.add(Notification(
                    source_key=f"task-message-{task.id}-{sequence}-{self.owner}",
                    source_type="task", source_id=task.id, sender="system", recipient=self.owner,
                    title="任务新消息", content=f"消息 {sequence}", is_read=False,
                ))
            db.add(Notification(
                source_key=f"task-message-{completed.id}-terminal-{self.owner}",
                source_type="task", source_id=completed.id, sender="system", recipient=self.owner,
                title="已验收任务消息", content="历史未读", is_read=False,
            ))
            db.add(Notification(
                source_key=f"task-message-{tasks[0].id}-5-{self.initiator}",
                source_type="task", source_id=tasks[0].id, sender=self.owner, recipient=self.initiator,
                title="任务新消息", content="发起人收到消息", is_read=False,
            ))
            db.add(Notification(
                source_key=f"task-reminder-{tasks[0].id}-{self.owner}",
                source_type="task", source_id=tasks[0].id, sender="system", recipient=self.owner,
                title="到期提醒", content=f"{tasks[0].serial_no}｜任务｜负责人：{self.owner}", is_read=False,
            ))
            db.add(Notification(
                source_key="user-message-other-recipient", source_type="message", sender="system",
                recipient=self.initiator, title="其他账号消息", content="不应计入负责人", is_read=False,
            ))
            await db.commit()

        async def database():
            async with self.sessions() as db:
                yield db

        self.previous_overrides = dict(app.dependency_overrides)
        app.dependency_overrides[get_db] = database
        self.identity = {"username": self.owner, "role": "user"}
        app.dependency_overrides[current_identity] = lambda: self.identity
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://notifications-row11.test")

    async def asyncTearDown(self):
        await self.client.aclose()
        app.dependency_overrides.clear()
        app.dependency_overrides.update(self.previous_overrides)
        await self.engine.dispose()

    async def test_notification_scope_task_routes_and_display_fields(self):
        response = await self.client.get(f"{settings.api_prefix}/notifications")
        self.assertEqual(response.status_code, 200, response.text)
        items = response.json()["items"]
        self.assertTrue(all(item["recipient"] == self.owner for item in items))
        reminder = next(item for item in items if item["title"] == "到期提醒")
        self.assertEqual(reminder["source_id"], self.accepted_task_id)
        self.assertEqual(reminder["target_route"], "task-my-accepted")
        self.assertEqual(reminder["source_serial_no"], self.accepted_task_serial)
        self.assertTrue(reminder["content"].endswith("负责人：任务负责人"))
        case_notice = next(item for item in items if item["source_id"] == self.case_id)
        self.assertEqual(case_notice["source_serial_no"], "CODEX-922-NOTICE-CASE")
        investigation = next(item for item in items if item["source_id"] == self.investigation_task_id)
        self.assertEqual(investigation["target_route"], "investigation-task-sub-mine")

        self.identity = {"username": self.initiator, "role": "user"}
        initiator_response = await self.client.get(f"{settings.api_prefix}/notifications")
        self.assertEqual(initiator_response.status_code, 200, initiator_response.text)
        initiator_notice = next(item for item in initiator_response.json()["items"] if item["source_id"] == self.accepted_task_id)
        self.assertEqual(initiator_notice["target_route"], "task-my-created")
        self.assertEqual(initiator_notice["source_serial_no"], self.accepted_task_serial)

    async def test_task_badge_counts_distinct_accepted_tasks_not_messages(self):
        response = await self.client.get(f"{settings.api_prefix}/tasks/unread-messages")
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertEqual(body["accepted_unread_tasks"], 1)
        self.assertEqual(body["total"], 4)
        self.assertEqual(body["unread_messages"], 5)

    async def test_admin_receives_only_own_contract_approvals(self):
        self.identity = {"username": self.admin, "role": "admin"}
        response = await self.client.get(f"{settings.api_prefix}/notifications")
        self.assertEqual(response.status_code, 200, response.text)
        self.assertFalse(any(item["source_type"] == "contract" for item in response.json()["items"]))
        async with self.sessions() as db:
            stored = await db.scalar(select(Notification).where(Notification.recipient == self.admin))
            self.assertIsNone(stored)


if __name__ == "__main__":
    unittest.main()
