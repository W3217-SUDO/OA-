"""在专用 PostgreSQL 测试库中验证智能助手命令的事务边界。"""

import asyncio
import os
import unittest
from datetime import date, timedelta
from unittest.mock import patch
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import event, func, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import app.areas.legal.case_space as legal_router
from app.agent_mcp.auth import AuthContext, _auth_context
from app.case_agent import CaseAgentRuntime
from app.config import settings
from app.core import documents
from app.database import Base
from app.main import app
from app.models import BusinessRecord, Notification, User, WorkflowEvent
from app.models_shared import (
    CaseAgentDecisionInput,
    CaseAgentMessageInput,
    CaseAgentProposedAction,
    TaskInput,
)


POSTGRES_URL = os.environ.get("AGENT_COMMANDS_TEST_POSTGRES_URL", "")


@unittest.skipUnless(POSTGRES_URL, "需要显式设置 AGENT_COMMANDS_TEST_POSTGRES_URL")
class AgentCommandsPostgresTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        if make_url(POSTGRES_URL).database != "oa_test_enterprise_commands":
            raise RuntimeError("智能助手命令测试只能使用专用 PostgreSQL 测试库")
        self.schema = f"oa_test_enterprise_commands_{uuid4().hex[:12]}"
        self.admin_engine = create_async_engine(POSTGRES_URL)
        async with self.admin_engine.begin() as connection:
            await connection.execute(text(f"CREATE SCHEMA {self.schema}"))
        self.engine = create_async_engine(
            POSTGRES_URL,
            connect_args={"server_settings": {"search_path": self.schema}},
        )
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        self.runtime = CaseAgentRuntime(
            enabled=True, database_url="sqlite+aiosqlite:///:memory:"
        )
        await self.runtime.start()
        self.original_runtime = legal_router.case_agent_runtime
        legal_router.case_agent_runtime = self.runtime

    async def asyncTearDown(self):
        legal_router.case_agent_runtime = self.original_runtime
        await self.runtime.stop()
        await self.engine.dispose()
        async with self.admin_engine.begin() as connection:
            await connection.execute(text(f"DROP SCHEMA {self.schema} CASCADE"))
        await self.admin_engine.dispose()

    async def _decide_action(self, case_id, action_id, body, identity, db):
        # 保留 PostgreSQL 事务断言，仅补齐真实前端确认入口要求的请求上下文。
        context = AuthContext(app, "test-only", {
            "type": "http", "method": "POST",
            "path": f"{settings.api_prefix}/case-spaces/{case_id}/agent/actions/{action_id}/decision",
            "headers": [
                (b"origin", b"http://localhost"),
                (b"x-oa-agent-confirmation", b"frontend"),
            ],
        })
        token = _auth_context.set(context)
        try:
            return await legal_router.decide_case_agent_action(case_id, action_id, body, identity, db)
        finally:
            context.active = False
            context.bearer = ""
            context.scope.clear()
            _auth_context.reset(token)

    async def _seed(self, db):
        db.add_all(
            [
                User(
                    username="lawyer",
                    display_name="律师",
                    department="上海",
                    password_hash="x",
                    role="admin",
                ),
                User(
                    username="assistant",
                    display_name="助理",
                    department="上海",
                    password_hash="x",
                    role="user",
                ),
            ]
        )
        case = BusinessRecord(
            module="case",
            serial_no="ENTERPRISE-COMMANDS-CASE",
            title="命令事务测试案件",
            customer="测试客户",
            status="办理中",
            owner="lawyer",
            department="上海",
            data={
                "case_type": "民事案件",
                "handling_lawyer_usernames": ["lawyer"],
                "assistant_username": "assistant",
                "case_team_usernames": ["lawyer", "assistant"],
            },
        )
        db.add(case)
        await db.commit()
        await db.refresh(case)
        return case

    async def _propose(self, db, case, action_type, payload):
        identity = {"username": "lawyer", "role": "admin"}
        result = await legal_router.send_case_agent_message(
            case.id,
            CaseAgentMessageInput(
                message="验证命令事务",
                proposed_action=CaseAgentProposedAction(
                    type=action_type,
                    summary="验证命令事务",
                    payload=payload,
                ),
            ),
            identity,
            db,
        )
        return result["pending_actions"][-1]["id"]

    async def test_ipr_task_adapter_commits_once_and_rejects_mismatched_case(self):
        from app.areas.ipr.router import create_ipr_case_task

        async with self.sessions() as db:
            case = await self._seed(db)
            case.module = "ipr_case"
            case.status = "在办"
            await db.commit()
            commits = []
            event.listen(db.sync_session, "before_commit", lambda session: commits.append(session))
            identity = {"username": "lawyer", "role": "admin"}
            body = TaskInput(title="知识产权案件任务", owner="assistant", deadline=date.today() + timedelta(days=7))
            response = await create_ipr_case_task(case.id, body, identity, db)
            self.assertEqual(len(commits), 1)
            self.assertEqual(response["case_module"], "ipr_case")
            self.assertEqual(response["case_ids"], [case.id])
            self.assertEqual(response["source"], "案件任务")
            with self.assertRaises(HTTPException) as raised:
                await create_ipr_case_task(case.id, body.model_copy(update={"case_record_id": case.id + 1}), identity, db)
            self.assertEqual(raised.exception.status_code, 422)
            self.assertEqual(len(commits), 1)

        async with self.sessions() as db:
            task = await db.get(BusinessRecord, response["id"])
            self.assertEqual(task.owner, "assistant")
            self.assertEqual(task.status, "待处理")
            self.assertEqual(task.data["case_ids"], [case.id])
            self.assertEqual(await db.scalar(select(func.count()).select_from(BusinessRecord).where(BusinessRecord.module == "task")), 1)
            self.assertTrue(await db.scalar(select(WorkflowEvent.id).where(WorkflowEvent.record_id == task.id)))
            self.assertTrue(await db.scalar(select(Notification.id).where(Notification.source_id == task.id, Notification.recipient == "assistant")))

    async def test_linked_updates_and_scope_failure(self):
        async with self.sessions() as db:
            case = await self._seed(db)
            customer = BusinessRecord(
                module="customer",
                serial_no="ENTERPRISE-COMMANDS-CUSTOMER",
                title="测试客户",
                customer="测试客户",
                status="签约",
                owner="lawyer",
                department="上海",
                description="原客户说明",
                data={"customer_type": "企业客户", "customer_managers": ["lawyer"]},
            )
            db.add(customer)
            await db.flush()
            contract = BusinessRecord(
                module="contract",
                serial_no="ENTERPRISE-COMMANDS-CONTRACT",
                title="测试合同",
                customer="测试客户",
                status="草稿",
                owner="lawyer",
                department="上海",
                description="原合同说明",
                data={
                    "customer_id": customer.id,
                    "customer_no": customer.serial_no,
                    "amount": 1000,
                },
            )
            outsider = BusinessRecord(
                module="customer",
                serial_no="ENTERPRISE-COMMANDS-OUTSIDE",
                title="空间外客户",
                customer="空间外客户",
                status="签约",
                owner="lawyer",
                department="上海",
                description="保持原样",
            )
            db.add_all([contract, outsider])
            await db.flush()
            case.data = {
                **case.data,
                "customer_id": customer.id,
                "contract_id": contract.id,
                "contract_no": contract.serial_no,
            }
            await db.commit()
            identity = {"username": "lawyer", "role": "admin"}

            action_id = await self._propose(
                db,
                case,
                "customer.update",
                {
                    "target_id": customer.id,
                    "changes": {"description": "客户已更新"},
                },
            )
            await self._decide_action(
                case.id,
                action_id,
                CaseAgentDecisionInput(decision="approved"),
                identity,
                db,
            )
            action_id = await self._propose(
                db,
                case,
                "contract.update",
                {
                    "target_id": contract.id,
                    "changes": {"description": "合同已更新"},
                },
            )
            await self._decide_action(
                case.id,
                action_id,
                CaseAgentDecisionInput(decision="approved"),
                identity,
                db,
            )
            action_id = await self._propose(
                db,
                case,
                "customer.update",
                {
                    "target_id": outsider.id,
                    "changes": {"description": "不应写入"},
                },
            )
            with self.assertRaises(HTTPException) as raised:
                await self._decide_action(
                    case.id,
                    action_id,
                    CaseAgentDecisionInput(decision="approved"),
                    identity,
                    db,
                )
            self.assertEqual(raised.exception.status_code, 404)
            self.assertIsInstance(outsider.id, int)

        async with self.sessions() as db:
            self.assertEqual(
                (await db.get(BusinessRecord, customer.id)).description, "客户已更新"
            )
            self.assertEqual(
                (await db.get(BusinessRecord, contract.id)).description, "合同已更新"
            )
            self.assertEqual(
                (await db.get(BusinessRecord, outsider.id)).description, "保持原样"
            )
            audits = (
                await db.scalars(
                    select(BusinessRecord).where(
                        BusinessRecord.module == "agent_action",
                    )
                )
            ).all()
            self.assertEqual(
                sorted(item.status for item in audits), ["已执行", "已执行", "执行失败"]
            )
            for item in audits:
                if item.status == "已执行":
                    self.assertIsInstance(
                        item.data["execution_result"]["record"]["created_at"], str
                    )

    async def test_task_notification_failure_rolls_back_and_retry_commits(self):
        async with self.sessions() as db:
            case = await self._seed(db)
            identity = {"username": "lawyer", "role": "admin"}
            action_id = await self._propose(
                db,
                case,
                "case.task.create",
                {
                    "title": "补充材料",
                    "owner": "assistant",
                    "deadline": str(date.today() + timedelta(days=5)),
                },
            )
            from app.core.tasks import _add_task_message_notifications

            async def fail_after_notification(*args, **kwargs):
                await _add_task_message_notifications(*args, **kwargs)
                await args[2].flush()
                raise RuntimeError("注入通知写入后故障")

            with patch(
                "app.core.tasks._add_task_message_notifications",
                fail_after_notification,
            ):
                with self.assertRaises(HTTPException) as raised:
                    await self._decide_action(
                        case.id,
                        action_id,
                        CaseAgentDecisionInput(decision="approved"),
                        identity,
                        db,
                    )
            self.assertEqual(raised.exception.status_code, 503)
            self.assertRegex(str(raised.exception.__cause__), "注入通知写入后故障")
            self.assertIsInstance(case.id, int)

        async with self.sessions() as db:
            self.assertEqual(
                await db.scalar(
                    select(func.count())
                    .select_from(BusinessRecord)
                    .where(
                        BusinessRecord.module == "task",
                    )
                ),
                0,
            )
            self.assertEqual(
                await db.scalar(
                    select(func.count())
                    .select_from(WorkflowEvent)
                    .where(
                        WorkflowEvent.action == "发起任务",
                    )
                ),
                0,
            )
            self.assertEqual(
                await db.scalar(
                    select(func.count())
                    .select_from(Notification)
                    .where(
                        Notification.source_type == "task",
                    )
                ),
                0,
            )
            failed = await db.scalar(
                select(BusinessRecord).where(BusinessRecord.module == "agent_action")
            )
            self.assertEqual(failed.status, "执行失败")

        async with self.sessions() as db:
            await self._decide_action(
                case.id,
                action_id,
                CaseAgentDecisionInput(decision="approved"),
                identity,
                db,
            )

        async with self.sessions() as db:
            self.assertEqual(
                await db.scalar(
                    select(func.count())
                    .select_from(BusinessRecord)
                    .where(
                        BusinessRecord.module == "task",
                    )
                ),
                1,
            )
            self.assertEqual(
                await db.scalar(
                    select(func.count())
                    .select_from(WorkflowEvent)
                    .where(
                        WorkflowEvent.action == "发起任务",
                    )
                ),
                1,
            )
            self.assertEqual(
                await db.scalar(
                    select(func.count())
                    .select_from(Notification)
                    .where(
                        Notification.source_type == "task",
                    )
                ),
                1,
            )
            audit = await db.scalar(
                select(BusinessRecord).where(BusinessRecord.module == "agent_action")
            )
            self.assertEqual(audit.status, "已执行")

    async def test_concurrent_approval_keeps_one_business_change_and_executed_audit(
        self,
    ):
        async with self.sessions() as db:
            case = await self._seed(db)
            action_id = await self._propose(
                db,
                case,
                "case.update",
                {
                    "changes": {"description": "并发审批后的说明"},
                },
            )
            case_id = case.id

        original_execute = documents._execute_case_agent_action
        both_entered = asyncio.Event()
        entered = 0

        async def enter_together(*args, **kwargs):
            nonlocal entered
            entered += 1
            if entered == 2:
                both_entered.set()
            await asyncio.wait_for(both_entered.wait(), timeout=15)
            return await original_execute(*args, **kwargs)

        async def approve():
            async with self.sessions() as db:
                try:
                    return await self._decide_action(
                        case_id,
                        action_id,
                        CaseAgentDecisionInput(decision="approved"),
                        {"username": "lawyer", "role": "admin"},
                        db,
                    )
                except HTTPException as exc:
                    self.assertEqual(exc.status_code, 409)
                    return None

        with patch.object(documents, "_execute_case_agent_action", enter_together):
            await asyncio.wait_for(asyncio.gather(approve(), approve()), timeout=30)

        async with self.sessions() as db:
            updated = await db.get(BusinessRecord, case_id)
            self.assertEqual(updated.description, "并发审批后的说明")
            audits = (
                await db.scalars(
                    select(BusinessRecord).where(
                        BusinessRecord.module == "agent_action",
                    )
                )
            ).all()
            self.assertEqual(len(audits), 1)
            self.assertEqual(audits[0].status, "已执行")
            self.assertEqual(
                await db.scalar(
                    select(func.count())
                    .select_from(WorkflowEvent)
                    .where(
                        WorkflowEvent.record_id == case_id,
                        WorkflowEvent.action == "智能体审批后更新案件",
                    )
                ),
                1,
            )

    async def test_conflict_gate_commits_facts_then_returns_409(self):
        async with self.sessions() as db:
            case = await self._seed(db)
            original_status = case.status
            action_id = await self._propose(
                db,
                case,
                "case.update",
                {
                    "changes": {"title": "已核实的案件事实", "status": "已完成"},
                },
            )

            async def assess(record, *_args, **_kwargs):
                record.data = {
                    **(record.data or {}),
                    "conflict_review": {"state": "待核查"},
                }

            async def gate(record, *_args, **_kwargs):
                return {"blocking": True, "record_id": record.id, "review": {"id": 12}}

            with (
                patch("app.core.conflict_review.assess_conflict_review", assess),
                patch(
                    "app.core.conflict_review.get_conflict_review_gate",
                    gate,
                ),
            ):
                with self.assertRaises(HTTPException) as raised:
                    await self._decide_action(
                        case.id,
                        action_id,
                        CaseAgentDecisionInput(decision="approved"),
                        {"username": "lawyer", "role": "admin"},
                        db,
                    )
            self.assertEqual(raised.exception.status_code, 409)
            self.assertEqual(
                raised.exception.detail["code"], "CONFLICT_REVIEW_REQUIRED"
            )

        async with self.sessions() as db:
            updated = await db.get(BusinessRecord, case.id)
            self.assertEqual(updated.title, "已核实的案件事实")
            self.assertEqual(updated.status, original_status)
            self.assertEqual(updated.data["conflict_review"], {"state": "待核查"})
            audit = await db.scalar(
                select(BusinessRecord).where(BusinessRecord.module == "agent_action")
            )
            self.assertEqual(audit.status, "执行失败")
            self.assertEqual(
                await db.scalar(
                    select(func.count())
                    .select_from(WorkflowEvent)
                    .where(
                        WorkflowEvent.record_id == case.id,
                        WorkflowEvent.action == "智能体审批后更新案件",
                    )
                ),
                1,
            )
