"""MVP contract tests for the LangGraph-backed case agent."""

import unittest
from datetime import date, timedelta
from unittest.mock import AsyncMock

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

import app.main as main_module
from app.case_agent import CaseAgentRuntime, _checkpoint_url, _extract_proposed_action
from app.database import Base
from app.main import (
    CaseAgentDecisionInput,
    CaseAgentMessageInput,
    CaseAgentProposedAction,
    case_agent_state,
    case_agent_status,
    decide_case_agent_action,
    get_case_workflow_guide,
    send_case_agent_message,
)
from app.models import BusinessRecord, FileAttachment, User, WorkflowEvent


class CaseAgentRuntimeTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.runtime = CaseAgentRuntime(enabled=True, database_url="sqlite+aiosqlite:///:memory:")
        await self.runtime.start()

    async def asyncTearDown(self):
        await self.runtime.stop()

    def test_model_action_block_is_removed_from_chat_and_normalized(self):
        content, action = _extract_proposed_action(
            '我可以为你更新案件说明。<proposed_action>{"type":"case.update","summary":"更新说明","payload":{"changes":{"description":"已沟通"}}}</proposed_action>'
        )
        self.assertEqual(content, "我可以为你更新案件说明。")
        self.assertEqual(action["type"], "case.update")
        self.assertEqual(action["payload"]["changes"]["description"], "已沟通")

    async def test_case_thread_persists_messages_and_approval_state(self):
        snapshot = {
            "case": {"id": 7, "serial_no": "SHMS-MVP-007"},
            "capabilities": {"can_create_reminder": True},
            "contracts": [{}],
            "documents": [{}, {}],
            "deadlines": [{}],
            "tasks": [],
            "finances": {"fees": [{}], "invoices": [{}]},
        }
        first = await self.runtime.invoke(
            case_id=7,
            operator="lawyer",
            message="请概括案件空间",
            case_snapshot=snapshot,
        )
        self.assertEqual(first["thread_id"], self.runtime.thread_id(7, "lawyer"))
        self.assertEqual(first["shared_space_id"], "case:7")
        self.assertIn("SHMS-MVP-007", first["last_response"])
        self.assertEqual(len(first["messages"]), 2)

        second = await self.runtime.invoke(
            case_id=7,
            operator="lawyer",
            message="准备新增案件提醒",
            case_snapshot=snapshot,
            proposed_action={
                "type": "case.reminder.create",
                "summary": "新增上诉期限提醒",
                "payload": {"deadline": "2026-08-31"},
            },
        )
        self.assertEqual(len(second["messages"]), 4)
        self.assertEqual(second["pending_actions"][0]["status"], "pending")
        action_id = second["pending_actions"][0]["id"]

        decided = await self.runtime.decide_action(
            case_id=7,
            action_id=action_id,
            decision="approved",
            operator="lawyer",
            comment="同意测试",
        )
        self.assertEqual(decided["pending_actions"][0]["status"], "approved")
        self.assertEqual(decided["pending_actions"][0]["decided_by"], "lawyer")
        self.assertEqual(len((await self.runtime.get_state(8, "lawyer"))["messages"]), 0)

    async def test_same_case_keeps_private_conversations_separate(self):
        snapshot = {"case": {"id": 17, "serial_no": "SHMS-SHARED-017"}, "documents": [{"id": 1}]}
        lawyer_state = await self.runtime.invoke(
            case_id=17,
            operator="lawyer",
            message="private lawyer note",
            case_snapshot=snapshot,
        )
        assistant_before = await self.runtime.get_state(17, "assistant")
        self.assertEqual(assistant_before["messages"], [])
        self.assertEqual(assistant_before["pending_actions"], [])
        self.assertEqual(assistant_before["shared_space_id"], lawyer_state["shared_space_id"])
        self.assertNotEqual(assistant_before["thread_id"], lawyer_state["thread_id"])

        assistant_state = await self.runtime.invoke(
            case_id=17,
            operator="assistant",
            message="private assistant note",
            case_snapshot=snapshot,
        )
        self.assertIn("SHMS-SHARED-017", assistant_state["last_response"])
        self.assertEqual(len(assistant_state["messages"]), 2)
        lawyer_after = await self.runtime.get_state(17, "lawyer")
        self.assertEqual(len(lawyer_after["messages"]), 2)
        self.assertEqual(lawyer_after["messages"][0]["content"], "private lawyer note")

    async def test_configured_model_receives_authorized_case_snapshot(self):
        self.runtime.api_base_url = "https://model.example/v1"
        self.runtime.api_key = "test-only"
        self.runtime.model_provider = "openai-compatible"
        self.runtime.model = "gpt-test"
        self.runtime._request_model = AsyncMock(return_value="这是基于案件空间生成的回答。")
        result = await self.runtime.invoke(
            case_id=9,
            operator="lawyer",
            message="案件有哪些期限风险？",
            case_snapshot={"case": {"id": 9, "serial_no": "SHMS-MODEL-009"}, "deadlines": [{}]},
        )
        self.assertTrue(self.runtime.status()["model_configured"])
        self.assertEqual(result["last_response"], "这是基于案件空间生成的回答。")
        snapshot, messages, skill, images = self.runtime._request_model.await_args.args
        self.assertEqual(snapshot["case"]["serial_no"], "SHMS-MODEL-009")
        self.assertEqual(messages[-1]["content"], "案件有哪些期限风险？")
        self.assertEqual(skill.id, "general-office")
        self.assertEqual(images, [])

    async def test_model_write_proposal_is_blocked_by_original_user_capability(self):
        self.runtime.api_base_url = "https://model.example/v1"
        self.runtime.api_key = "test-only"
        self.runtime.model = "gpt-test"
        self.runtime._request_model = AsyncMock(return_value=(
            "我可以修改案件说明。",
            {"type": "case.update", "summary": "越权修改案件", "payload": {"changes": {"description": "不应写入"}}},
        ))
        result = await self.runtime.invoke(
            case_id=12,
            operator="assistant",
            message="修改案件说明",
            case_snapshot={
                "case": {"id": 12, "serial_no": "SHMS-MODEL-012"},
                "capabilities": {"can_write": True, "can_edit_basic": False},
            },
        )
        self.assertEqual(result["pending_actions"], [])
        self.assertIn("原有业务权限不允许", result["last_response"])

    async def test_selected_office_skill_routes_without_exposing_marker(self):
        self.runtime.api_base_url = "https://model.example/v1"
        self.runtime.api_key = "test-only"
        self.runtime.model = "gpt-test"
        self.runtime._request_model = AsyncMock(return_value="已完成数据分析。")
        result = await self.runtime.invoke(
            case_id=10,
            operator="lawyer",
            message="[[skill:data-analysis]]\n检查费用异常",
            case_snapshot={"case": {"id": 10}, "finances": {"fees": []}},
        )
        self.assertEqual(result["active_skill"], "data-analysis")
        self.assertEqual(result["messages"][0]["content"], "检查费用异常")
        self.assertNotIn("[[skill:", result["messages"][0]["content"])
        self.assertEqual(self.runtime._request_model.await_args.args[2].id, "data-analysis")

    async def test_screenshot_skill_forwards_images_without_persisting_base64(self):
        self.runtime.api_base_url = "https://model.example/v1"
        self.runtime.api_key = "test-only"
        self.runtime.model = "gpt-test"
        self.runtime._request_model = AsyncMock(return_value="已分析截图。")
        result = await self.runtime.invoke(
            case_id=11,
            operator="lawyer",
            message="[[skill:screenshot-evidence]]\n分析截图证据",
            case_snapshot={"case": {"id": 11}},
            images=[{"id": 91, "name": "evidence.png", "mime_type": "image/png", "data_url": "data:image/png;base64,dGVzdA=="}],
        )
        self.assertEqual(result["active_skill"], "screenshot-evidence")
        self.assertEqual(result["messages"][0]["attachments"][0]["name"], "evidence.png")
        self.assertNotIn("data_url", result["messages"][0]["attachments"][0])
        self.assertEqual(self.runtime._request_model.await_args.args[3][0]["data_url"], "data:image/png;base64,dGVzdA==")

    def test_sqlalchemy_postgres_url_is_normalized_for_psycopg(self):
        self.assertEqual(
            _checkpoint_url("postgresql+asyncpg://user:pass@postgres:5432/legal", ""),
            "postgresql://user:pass@postgres:5432/legal",
        )


class CaseAgentApiContractTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.runtime = CaseAgentRuntime(enabled=True, database_url="sqlite+aiosqlite:///:memory:")
        await self.runtime.start()
        self.original_runtime = main_module.case_agent_runtime
        main_module.case_agent_runtime = self.runtime

    async def asyncTearDown(self):
        main_module.case_agent_runtime = self.original_runtime
        await self.runtime.stop()
        await self.engine.dispose()

    async def _seed(self, db: AsyncSession) -> BusinessRecord:
        db.add_all([
            User(username="lawyer", display_name="范文玲", department="上海", password_hash="x", role="admin"),
            User(username="assistant", display_name="律师助理", department="上海", password_hash="x", role="user"),
            User(username="outsider", display_name="外部人员", department="北京", password_hash="x", role="user"),
        ])
        case = BusinessRecord(
            module="case",
            serial_no="SHMS-MVP-001",
            title="LangGraph MVP 案件",
            customer="测试客户",
            status="办理中",
            owner="lawyer",
            department="上海",
            data={"case_type": "民事案件", "handling_lawyer_usernames": ["lawyer"], "assistant_username": "assistant", "case_team_usernames": ["lawyer", "assistant"]},
        )
        db.add(case)
        await db.commit()
        await db.refresh(case)
        return case

    async def _seed_linked_customer_and_contract(self, db: AsyncSession, case: BusinessRecord):
        customer = BusinessRecord(
            module="customer", serial_no="SHKH-MVP-001", title="测试客户", customer="测试客户",
            status="签约", owner="lawyer", department="上海", description="原客户说明",
            data={"customer_type": "企业客户", "customer_managers": ["lawyer"]},
        )
        db.add(customer)
        await db.flush()
        contract = BusinessRecord(
            module="contract", serial_no="HT-MVP-001", title="测试客户服务合同", customer=customer.title,
            status="草稿", owner="lawyer", department="上海", description="原合同说明",
            data={"customer_id": customer.id, "customer_no": customer.serial_no, "amount": 1000},
        )
        db.add(contract)
        await db.flush()
        case.customer = customer.title
        case.data = {**(case.data or {}), "customer_id": customer.id, "contract_id": contract.id, "contract_no": contract.serial_no}
        await db.commit()
        await db.refresh(customer)
        await db.refresh(contract)
        await db.refresh(case)
        return customer, contract

    async def test_authorized_api_flow_and_action_decision(self):
        async with self.sessions() as db:
            case = await self._seed(db)
            identity = {"username": "lawyer", "role": "admin"}
            status = await case_agent_status(case.id, identity, db)
            self.assertTrue(status["ready"])
            workflow = await get_case_workflow_guide(case.id, identity, db)
            self.assertEqual(workflow["manual"]["version"], "2026-08")
            self.assertEqual(workflow["current_phase"]["code"], "document-preparation")
            self.assertTrue(workflow["materials"])
            result = await send_case_agent_message(
                case.id,
                CaseAgentMessageInput(
                    message="准备更新案件信息",
                    proposed_action=CaseAgentProposedAction(
                        type="case.update",
                        summary="更新案件备注",
                        payload={"description": "MVP only"},
                    ),
                ),
                identity,
                db,
            )
            self.assertEqual(result["pending_actions"][0]["status"], "pending")
            state = await case_agent_state(case.id, identity, db)
            self.assertEqual(state["thread_id"], main_module.case_agent_runtime.thread_id(case.id, identity["username"]))
            self.assertEqual(state["shared_space_id"], f"case:{case.id}")
            result = await decide_case_agent_action(
                case.id,
                result["pending_actions"][0]["id"],
                CaseAgentDecisionInput(decision="rejected", comment="测试不落库"),
                identity,
                db,
            )
            self.assertEqual(result["pending_actions"][0]["status"], "rejected")
            unchanged = await db.get(BusinessRecord, case.id)
            self.assertEqual(unchanged.description, "")

    async def test_approved_case_update_is_applied_and_audited(self):
        async with self.sessions() as db:
            case = await self._seed(db)
            identity = {"username": "lawyer", "role": "admin"}
            result = await send_case_agent_message(
                case.id,
                CaseAgentMessageInput(
                    message="把案件说明改为已完成客户沟通",
                    proposed_action=CaseAgentProposedAction(
                        type="case.update",
                        summary="更新案件说明",
                        payload={"changes": {"description": "已完成客户沟通"}},
                    ),
                ),
                identity,
                db,
            )
            action = result["pending_actions"][0]
            self.assertEqual(action["preview"]["changes"][0]["before"], "")
            self.assertEqual(action["preview"]["changes"][0]["after"], "已完成客户沟通")
            decided = await decide_case_agent_action(
                case.id,
                action["id"],
                CaseAgentDecisionInput(decision="approved", comment="同意执行"),
                identity,
                db,
            )
            approved = decided["pending_actions"][0]
            self.assertEqual(approved["status"], "approved")
            self.assertEqual(approved["execution_result"]["updated_fields"]["description"], "已完成客户沟通")
            updated = await db.get(BusinessRecord, case.id)
            self.assertEqual(updated.description, "已完成客户沟通")
            events = list((await db.scalars(select(WorkflowEvent).where(WorkflowEvent.record_id == case.id))).all())
            self.assertTrue(any(item.action == "智能体审批后更新案件" for item in events))

    async def test_approved_linked_customer_update_uses_customer_business_guard(self):
        async with self.sessions() as db:
            case = await self._seed(db)
            customer, _ = await self._seed_linked_customer_and_contract(db, case)
            identity = {"username": "lawyer", "role": "admin"}
            result = await send_case_agent_message(
                case.id,
                CaseAgentMessageInput(
                    message="修改关联客户说明",
                    proposed_action=CaseAgentProposedAction(
                        type="customer.update",
                        summary="更新客户说明",
                        payload={"target_id": customer.id, "changes": {"description": "智能体审批后的客户说明"}},
                    ),
                ),
                identity,
                db,
            )
            action = result["pending_actions"][-1]
            self.assertEqual(action["preview"]["target"], customer.serial_no)
            await decide_case_agent_action(case.id, action["id"], CaseAgentDecisionInput(decision="approved"), identity, db)
            updated = await db.get(BusinessRecord, customer.id)
            self.assertEqual(updated.description, "智能体审批后的客户说明")

    async def test_approved_linked_contract_update_uses_contract_draft_guard(self):
        async with self.sessions() as db:
            case = await self._seed(db)
            _, contract = await self._seed_linked_customer_and_contract(db, case)
            identity = {"username": "lawyer", "role": "admin"}
            result = await send_case_agent_message(
                case.id,
                CaseAgentMessageInput(
                    message="修改关联合同说明",
                    proposed_action=CaseAgentProposedAction(
                        type="contract.update",
                        summary="更新合同说明",
                        payload={"target_id": contract.id, "changes": {"description": "智能体审批后的合同说明"}},
                    ),
                ),
                identity,
                db,
            )
            action = result["pending_actions"][-1]
            self.assertEqual(action["preview"]["target"], contract.serial_no)
            await decide_case_agent_action(case.id, action["id"], CaseAgentDecisionInput(decision="approved"), identity, db)
            updated = await db.get(BusinessRecord, contract.id)
            self.assertEqual(updated.description, "智能体审批后的合同说明")

    async def test_agent_cannot_update_customer_outside_current_case_space(self):
        async with self.sessions() as db:
            case = await self._seed(db)
            _, _ = await self._seed_linked_customer_and_contract(db, case)
            outsider = BusinessRecord(
                module="customer", serial_no="SHKH-MVP-OUTSIDE", title="其他客户", customer="其他客户",
                status="签约", owner="lawyer", department="上海", description="不可修改",
            )
            db.add(outsider)
            await db.commit()
            identity = {"username": "lawyer", "role": "admin"}
            result = await send_case_agent_message(
                case.id,
                CaseAgentMessageInput(
                    message="尝试修改空间外客户",
                    proposed_action=CaseAgentProposedAction(
                        type="customer.update",
                        summary="错误目标测试",
                        payload={"target_id": outsider.id, "changes": {"description": "不应写入"}},
                    ),
                ),
                identity,
                db,
            )
            action = result["pending_actions"][-1]
            with self.assertRaises(HTTPException) as raised:
                await decide_case_agent_action(case.id, action["id"], CaseAgentDecisionInput(decision="approved"), identity, db)
            self.assertEqual(raised.exception.status_code, 404)
            unchanged = await db.get(BusinessRecord, outsider.id)
            self.assertEqual(unchanged.description, "不可修改")

    async def test_assistant_cannot_see_or_approve_another_users_pending_action(self):
        async with self.sessions() as db:
            case = await self._seed(db)
            manager_identity = {"username": "lawyer", "role": "admin"}
            result = await send_case_agent_message(
                case.id,
                CaseAgentMessageInput(
                    message="修改案件说明",
                    proposed_action=CaseAgentProposedAction(
                        type="case.update",
                        summary="修改案件说明",
                        payload={"changes": {"description": "不应由助理写入"}},
                    ),
                ),
                manager_identity,
                db,
            )
            action = result["pending_actions"][0]
            assistant_identity = {"username": "assistant", "role": "user"}
            assistant_state = await case_agent_state(case.id, assistant_identity, db)
            self.assertEqual(assistant_state["messages"], [])
            self.assertEqual(assistant_state["pending_actions"], [])
            self.assertEqual(assistant_state["shared_space_id"], result["shared_space_id"])
            self.assertNotEqual(assistant_state["thread_id"], result["thread_id"])
            with self.assertRaises(HTTPException) as raised:
                await decide_case_agent_action(
                    case.id,
                    action["id"],
                    CaseAgentDecisionInput(decision="approved"),
                    assistant_identity,
                    db,
                )
            self.assertEqual(raised.exception.status_code, 404)
            unchanged = await db.get(BusinessRecord, case.id)
            self.assertEqual(unchanged.description, "")

    async def test_approved_task_and_reminder_proposals_create_linked_records(self):
        async with self.sessions() as db:
            case = await self._seed(db)
            identity = {"username": "lawyer", "role": "admin"}
            deadline = date.today() + timedelta(days=5)
            task_result = await send_case_agent_message(
                case.id,
                CaseAgentMessageInput(
                    message="创建案件任务",
                    proposed_action=CaseAgentProposedAction(
                        type="case.task.create",
                        summary="创建补充材料任务",
                        payload={"title": "补充立案材料", "owner": "lawyer", "deadline": str(deadline), "priority": "普通"},
                    ),
                ),
                identity,
                db,
            )
            task_action = task_result["pending_actions"][-1]
            await decide_case_agent_action(case.id, task_action["id"], CaseAgentDecisionInput(decision="approved"), identity, db)
            tasks = list((await db.scalars(select(BusinessRecord).where(BusinessRecord.module == "task"))).all())
            self.assertTrue(any((item.data or {}).get("case_record_id") == case.id for item in tasks))

            reminder_result = await send_case_agent_message(
                case.id,
                CaseAgentMessageInput(
                    message="创建案件提醒",
                    proposed_action=CaseAgentProposedAction(
                        type="case.reminder.create",
                        summary="创建材料期限提醒",
                        payload={"content": "检查立案材料", "reminder_date": str(date.today() + timedelta(days=2)), "deadline": str(deadline)},
                    ),
                ),
                identity,
                db,
            )
            reminder_action = reminder_result["pending_actions"][-1]
            await decide_case_agent_action(case.id, reminder_action["id"], CaseAgentDecisionInput(decision="approved"), identity, db)
            reminders = list((await db.scalars(select(BusinessRecord).where(BusinessRecord.module == "case_reminder"))).all())
            self.assertTrue(any((item.data or {}).get("case_id") == case.id for item in reminders))

    async def test_unauthorized_user_cannot_open_case_agent(self):
        async with self.sessions() as db:
            case = await self._seed(db)
            with self.assertRaises(HTTPException) as raised:
                await case_agent_status(
                    case.id,
                    {"username": "outsider", "role": "user"},
                    db,
                )
        self.assertEqual(raised.exception.status_code, 404)

    async def test_screenshot_attachment_is_scoped_to_case_and_forwarded(self):
        target = main_module.UPLOAD_ROOT / "case-agent-contract-screenshot.png"
        target.write_bytes(b"test-png")
        try:
            async with self.sessions() as db:
                case = await self._seed(db)
                attachment = FileAttachment(
                    record_id=case.id,
                    category="智能体截图证据",
                    original_name="contract-screenshot.png",
                    stored_name=target.name,
                    content_type="image/png",
                    size=target.stat().st_size,
                    path=str(target),
                    uploader="lawyer",
                    remark="test",
                )
                db.add(attachment)
                await db.commit()
                await db.refresh(attachment)
                result = await send_case_agent_message(
                    case.id,
                    CaseAgentMessageInput(
                        message="[[skill:screenshot-evidence]]\n分析截图证据",
                        attachment_ids=[attachment.id],
                    ),
                    {"username": "lawyer", "role": "admin"},
                    db,
                )
                self.assertEqual(result["messages"][0]["attachments"][0]["id"], attachment.id)
                self.assertEqual(result["messages"][0]["attachments"][0]["name"], "contract-screenshot.png")
        finally:
            target.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
