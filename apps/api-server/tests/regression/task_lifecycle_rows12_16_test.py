"""9.2 rows 12-16: legacy task action/state parity."""

from __future__ import annotations

import unittest
from datetime import date, timedelta
from unittest.mock import patch

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database import Base, get_db
from app.main import _ensure_case_fixed_tasks, app
from app.models import BusinessRecord, User, WorkflowEvent
from app.security import current_identity


API = settings.api_prefix
INITIATOR = {"username": "row12-initiator", "role": "staff", "display_name": "发起人", "department": "事务部"}
OWNER = {"username": "row15-owner", "role": "staff", "display_name": "负责人", "department": "事务部"}
RECIPIENT = {"username": "row15-recipient", "role": "staff", "display_name": "接收人", "department": "事务部"}
ADMIN = {"username": "row15-admin", "role": "admin", "display_name": "管理员", "department": "管理部"}


class TaskLifecycleRows12To16Test(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool,
        )
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with self.sessions() as db:
            for identity in (INITIATOR, OWNER, RECIPIENT, ADMIN):
                db.add(User(
                    username=identity["username"], display_name=identity["display_name"],
                    department=identity["department"], role=identity["role"], password_hash="x", is_active=True,
                ))
            db.add(User(
                username="row15-disabled", display_name="停用接收人", department="事务部",
                role="staff", password_hash="x", is_active=False,
            ))
            await db.commit()
        self.identity = dict(INITIATOR)
        self.previous_overrides = dict(app.dependency_overrides)
        app.dependency_overrides[get_db] = self.override_db
        app.dependency_overrides[current_identity] = lambda: self.identity
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://rows12-16.test")

    async def override_db(self):
        async with self.sessions() as db:
            yield db

    async def asyncTearDown(self) -> None:
        await self.client.aclose()
        app.dependency_overrides.clear()
        app.dependency_overrides.update(self.previous_overrides)
        await self.engine.dispose()

    async def create_task(self, status: str, suffix: str) -> int:
        async with self.sessions() as db:
            task = BusinessRecord(
                module="task", serial_no=f"903{suffix}", title=f"9.2-{suffix}", customer="",
                status=status, owner=OWNER["username"], department="事务部",
                data={"initiator": INITIATOR["username"], "source": "日常任务", "rejected_reason": "缺少材料"},
            )
            db.add(task)
            await db.commit()
            await db.refresh(task)
            return task.id

    async def persisted_task(self, task_id: int) -> BusinessRecord:
        async with self.sessions() as db:
            return await db.get(BusinessRecord, task_id)

    async def create_automatic_task(self, status: str, suffix: str) -> tuple[int, int]:
        async with self.sessions() as db:
            case = BusinessRecord(
                module="case", serial_no=f"CODEX-INTERVENTION-{suffix}", title="人工干预案件",
                status="提交立案", owner=INITIATOR["username"], department="事务部",
                data={"phase_changed_at": "2026-10-13T09:00:00"},
            )
            db.add(case)
            await db.flush()
            task = BusinessRecord(
                module="task", serial_no=f"CODEX-TASK-{suffix}", title="跟进立案",
                status=status, owner=OWNER["username"], department="事务部",
                data={
                    "initiator": INITIATOR["username"], "source": "案件任务",
                    "creation_mode": "自动", "auto_task_type": "confirmed_case_rule_04",
                    "case_id": case.id, "case_record_id": case.id,
                    "deadline": str(date.today() + timedelta(days=7)),
                },
            )
            db.add(task)
            await db.commit()
            return task.id, case.id

    async def sync_automatic_case(self, case_id: int, *, stage: str | None = None) -> None:
        from app.core.case_automation import _complete_matching_tasks
        from app.core.case_automation_sources import RuleSources

        async with self.sessions() as db:
            case = await db.get(BusinessRecord, case_id)
            if stage:
                case.status = stage
                case.data = {**case.data, "phase_changed_at": "2026-10-13T10:00:00"}
            await _complete_matching_tasks(db, RuleSources(), [case])
            await db.commit()

    async def test_automatic_task_owner_and_deadline_audit_keep_normal_completion(self) -> None:
        task_id, case_id = await self.create_automatic_task("待接收", "owner")
        deadline = str(date.today() + timedelta(days=20))
        response = await self.client.post(f"{API}/tasks/batch-update", json={
            "task_ids": [task_id], "owner": RECIPIENT["username"], "deadline": deadline,
        })
        self.assertEqual(response.status_code, 200, response.text)
        await self.sync_automatic_case(case_id)
        task = await self.persisted_task(task_id)
        self.assertEqual((task.owner, task.status, task.data["deadline"]), (RECIPIENT["username"], "待接收", deadline))
        self.assertEqual(task.data["manual_intervention"]["operator"], INITIATOR["username"])
        self.assertFalse(task.data["manual_intervention"]["completion_override"])
        await self.sync_automatic_case(case_id, stage="一审准备开庭")
        self.assertEqual((await self.persisted_task(task_id)).status, "已完成")

    async def test_automatic_task_manual_start_complete_and_confirm_keep_original_permissions(self) -> None:
        task_id, case_id = await self.create_automatic_task("待接收", "lifecycle")
        self.identity = dict(OWNER)
        started = await self.client.post(f"{API}/tasks/{task_id}/restart", json={"comment": "人工开始"})
        self.assertEqual(started.status_code, 200, started.text)
        await self.sync_automatic_case(case_id)
        self.assertEqual((await self.persisted_task(task_id)).status, "处理中")
        completed = await self.client.post(f"{API}/tasks/{task_id}/complete", json={"comment": "人工完成"})
        self.assertEqual(completed.status_code, 200, completed.text)
        denied = await self.client.post(f"{API}/tasks/{task_id}/confirm", json={})
        self.assertEqual(denied.status_code, 403, denied.text)
        self.identity = dict(INITIATOR)
        confirmed = await self.client.post(f"{API}/tasks/{task_id}/confirm", json={})
        self.assertEqual(confirmed.status_code, 200, confirmed.text)
        await self.sync_automatic_case(case_id, stage="一审准备开庭")
        self.assertEqual((await self.persisted_task(task_id)).status, "已验收")
        async with self.sessions() as db:
            events = list((await db.scalars(select(WorkflowEvent).where(WorkflowEvent.record_id == task_id))).all())
        self.assertEqual([event.action for event in events], ["重新开始任务", "提交任务完成", "验收任务"])
        self.assertEqual([event.operator for event in events], [OWNER["username"], OWNER["username"], INITIATOR["username"]])

    async def test_automatic_task_batch_lifecycle_accept_complete_handoff_and_confirm(self) -> None:
        task_id, case_id = await self.create_automatic_task("待接收", "batch")
        self.identity = dict(OWNER)
        for action in ("accept", "handoff"):
            response = await self.client.post(f"{API}/tasks/batch-lifecycle", json={
                "task_ids": [task_id], "action": action, "recipient": RECIPIENT["username"],
            })
            self.assertEqual(response.status_code, 200, response.text)
            await self.sync_automatic_case(case_id)
        handed = await self.persisted_task(task_id)
        self.assertEqual((handed.owner, handed.status, handed.data["handoff_restarted"]), (RECIPIENT["username"], "待接收", False))
        self.identity = dict(RECIPIENT)
        for action in ("accept", "complete"):
            response = await self.client.post(f"{API}/tasks/batch-lifecycle", json={"task_ids": [task_id], "action": action})
            self.assertEqual(response.status_code, 200, response.text)
        self.identity = dict(INITIATOR)
        confirmed = await self.client.post(f"{API}/tasks/batch-lifecycle", json={"task_ids": [task_id], "action": "confirm"})
        self.assertEqual(confirmed.status_code, 200, confirmed.text)
        self.assertEqual((await self.persisted_task(task_id)).status, "已验收")

    async def test_automatic_task_cancel_requires_original_application_and_review(self) -> None:
        task_id, case_id = await self.create_automatic_task("处理中", "cancel")
        self.identity = dict(OWNER)
        requested = await self.client.post(f"{API}/tasks/{task_id}/exception-request", json={"action": "取消", "reason": "人工取消原因"})
        self.assertEqual(requested.status_code, 200, requested.text)
        denied = await self.client.post(f"{API}/tasks/{task_id}/exception-review", json={"approved": True})
        self.assertEqual(denied.status_code, 403, denied.text)
        await self.sync_automatic_case(case_id)
        self.assertEqual((await self.persisted_task(task_id)).status, "处理中")
        self.identity = dict(INITIATOR)
        approved = await self.client.post(f"{API}/tasks/{task_id}/exception-review", json={"approved": True})
        self.assertEqual(approved.status_code, 200, approved.text)
        await self.sync_automatic_case(case_id, stage="一审准备开庭")
        task = await self.persisted_task(task_id)
        self.assertEqual((task.status, task.data["exception_request"]["status"]), ("已取消", "已通过"))

    async def test_automatic_task_manual_override_cannot_bypass_scope_deadline_or_atomic_preflight(self) -> None:
        task_id, case_id = await self.create_automatic_task("待接收", "denied")
        self.identity = dict(RECIPIENT)
        for path, payload in (
            ("batch-update", {"task_ids": [task_id], "owner": RECIPIENT["username"]}),
            ("batch-lifecycle", {"task_ids": [task_id], "action": "complete"}),
            (f"{task_id}/restart", {}),
            (f"{task_id}/complete", {}),
            (f"{task_id}/exception-request", {"action": "取消", "reason": "越权取消"}),
        ):
            response = await self.client.post(f"{API}/tasks/{path}", json=payload)
            self.assertEqual(response.status_code, 403, response.text)
        self.identity = dict(OWNER)
        invalid_deadline = await self.client.post(f"{API}/tasks/batch-update", json={
            "task_ids": [task_id], "deadline": str(date.today() + timedelta(days=31)),
        })
        self.assertEqual(invalid_deadline.status_code, 422, invalid_deadline.text)
        stopped = await self.create_task("已停止", "manual-mixed")
        for path, payload in (
            ("batch-update", {"task_ids": [task_id, stopped], "owner": RECIPIENT["username"]}),
            ("batch-lifecycle", {"task_ids": [task_id, stopped], "action": "complete"}),
        ):
            response = await self.client.post(f"{API}/tasks/{path}", json=payload)
            self.assertEqual(response.status_code, 409, response.text)
        task = await self.persisted_task(task_id)
        self.assertEqual((task.owner, task.status), (OWNER["username"], "待接收"))
        self.assertNotIn("manual_intervention", task.data)
        async with self.sessions() as db:
            self.assertEqual(list((await db.scalars(select(WorkflowEvent).where(WorkflowEvent.record_id == task_id))).all()), [])
        await self.sync_automatic_case(case_id, stage="一审立案受理")
        self.assertEqual((await self.persisted_task(task_id)).status, "已完成")

    async def test_phase_completed_task_can_be_manually_restarted_without_immediate_recompletion(self) -> None:
        task_id, case_id = await self.create_automatic_task("已完成", "restarted")
        async with self.sessions() as db:
            task = await db.get(BusinessRecord, task_id)
            task.data = {**task.data, "auto_completed": True}
            case = await db.get(BusinessRecord, case_id)
            case.status = "一审立案受理"
            await db.commit()
        restarted = await self.client.post(f"{API}/tasks/{task_id}/restart", json={})
        self.assertEqual(restarted.status_code, 200, restarted.text)
        await self.sync_automatic_case(case_id)
        task = await self.persisted_task(task_id)
        self.assertEqual((task.status, task.data["auto_completed"]), ("处理中", False))
        self.assertTrue(task.data["manual_intervention"]["completion_override"])
        await self.sync_automatic_case(case_id, stage="一审准备开庭")
        self.assertEqual((await self.persisted_task(task_id)).status, "已完成")

    async def test_manual_completion_still_auto_confirms_after_five_days(self) -> None:
        from app.core.tasks import _apply_task_auto_completion

        task_id, _ = await self.create_automatic_task("处理中", "auto-confirm")
        self.identity = dict(OWNER)
        response = await self.client.post(f"{API}/tasks/{task_id}/complete", json={})
        self.assertEqual(response.status_code, 200, response.text)
        async with self.sessions() as db:
            task = await db.get(BusinessRecord, task_id)
            self.assertEqual(task.data["completion_auto_confirm_at"], str(date.today() + timedelta(days=5)))
            task.data = {**task.data, "completion_auto_confirm_at": str(date.today() - timedelta(days=5))}
            await db.commit()
            await _apply_task_auto_completion(db)
        self.assertEqual((await self.persisted_task(task_id)).status, "已验收")

    async def test_normal_accept_and_maintenance_do_not_disable_same_stage_auto_completion(self) -> None:
        for suffix, path in (("accept", "accept"), ("maintenance", "batch-update"), ("untouched", None)):
            task_id, case_id = await self.create_automatic_task("待接收", f"normal-{suffix}")
            clue_no = f"CODEX-UPLOADED-CERTIFICATE-{suffix}"
            async with self.sessions() as db:
                task = await db.get(BusinessRecord, task_id)
                task.data = {**task.data, "auto_task_type": "confirmed_case_rule_10", "trigger_source_id": f"clue:{clue_no}"}
                case = await db.get(BusinessRecord, case_id)
                case.data = {**case.data, "clue_nos": [clue_no]}
                await db.commit()
            self.identity = dict(OWNER)
            if path:
                payload = {"task_ids": [task_id], "deadline": str(date.today() + timedelta(days=10))} if path == "batch-update" else {}
                route = path if path == "batch-update" else f"{task_id}/{path}"
                response = await self.client.post(f"{API}/tasks/{route}", json=payload)
                self.assertEqual(response.status_code, 200, response.text)
            from app.core.case_automation import _complete_matching_tasks
            from app.core.case_automation_sources import RuleSources

            async with self.sessions() as db:
                case = await db.get(BusinessRecord, case_id)
                clue = BusinessRecord(module="clue", serial_no=clue_no, title="已入库线索", status="已入库", owner=OWNER["username"], data={"evidence_status": "已入库"})
                sources = RuleSources(current_clues={clue_no: clue}, certificate_upload_clues={clue_no})
                await _complete_matching_tasks(db, sources, [case])
                await db.commit()
            self.assertEqual((await self.persisted_task(task_id)).status, "已完成")

    async def test_normal_actions_retain_explicit_restart_override_in_same_stage(self) -> None:
        task_id, case_id = await self.create_automatic_task("已完成", "retain")
        async with self.sessions() as db:
            case = await db.get(BusinessRecord, case_id)
            case.status = "一审立案受理"
            task = await db.get(BusinessRecord, task_id)
            task.data = {**task.data, "auto_completed": True}
            await db.commit()
        response = await self.client.post(f"{API}/tasks/{task_id}/restart", json={})
        self.assertEqual(response.status_code, 200, response.text)
        response = await self.client.post(f"{API}/tasks/batch-update", json={
            "task_ids": [task_id], "deadline": str(date.today() + timedelta(days=10)),
        })
        self.assertEqual(response.status_code, 200, response.text)
        await self.sync_automatic_case(case_id)
        task = await self.persisted_task(task_id)
        self.assertEqual(task.status, "处理中")
        self.assertTrue(task.data["manual_intervention"]["completion_override"])

    async def test_initiator_can_restart_or_confirm_rejected_and_completed_tasks(self) -> None:
        rejected_restart = await self.create_task("已拒绝", "1201")
        response = await self.client.post(f"{API}/tasks/{rejected_restart}/restart", json={"comment": "补齐材料后重启"})
        self.assertEqual(response.status_code, 200, response.text)
        restarted = await self.persisted_task(rejected_restart)
        self.assertEqual(response.json()["status"], "待处理")
        self.assertEqual(restarted.status, "待处理")
        self.assertEqual((restarted.data or {}).get("rejected_reason"), "")

        rejected_confirm = await self.create_task("已拒绝", "1301")
        response = await self.client.post(f"{API}/tasks/{rejected_confirm}/confirm", json={"comment": "不再继续，确认完成"})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual((await self.persisted_task(rejected_confirm)).status, "已验收")

        completed_restart = await self.create_task("已完成", "1202")
        response = await self.client.post(f"{API}/tasks/{completed_restart}/restart", json={"comment": "验收不通过"})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual((await self.persisted_task(completed_restart)).status, "处理中")

        async with self.sessions() as db:
            events = list((await db.scalars(select(WorkflowEvent).where(
                WorkflowEvent.record_id.in_([rejected_restart, rejected_confirm, completed_restart])
            ))).all())
        self.assertEqual({event.action for event in events}, {"重新开始任务", "验收任务"})

    async def test_recipient_can_complete_or_handoff_pending_and_processing_tasks(self) -> None:
        self.identity = dict(OWNER)
        pending_complete = await self.create_task("待处理", "1501")
        response = await self.client.post(f"{API}/tasks/{pending_complete}/complete", json={"comment": "直接完成"})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual((await self.persisted_task(pending_complete)).status, "已完成")

        pending_handoff = await self.create_task("待接收", "1502")
        response = await self.client.post(f"{API}/tasks/{pending_handoff}/handoff", json={
            "recipient": RECIPIENT["username"], "comment": "转交处理",
        })
        self.assertEqual(response.status_code, 200, response.text)
        handed = await self.persisted_task(pending_handoff)
        self.assertEqual((handed.owner, handed.status), (RECIPIENT["username"], "待接收"))

        processing_complete = await self.create_task("进行中", "1601")
        response = await self.client.post(f"{API}/tasks/{processing_complete}/complete", json={"comment": "处理完成"})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual((await self.persisted_task(processing_complete)).status, "已完成")

    async def test_ended_tasks_reject_recipient_actions(self) -> None:
        self.identity = dict(OWNER)
        stopped = await self.create_task("已停止", "1602")
        accepted = await self.client.post(f"{API}/tasks/{stopped}/accept", json={"comment": "不应接收"})
        completed = await self.client.post(f"{API}/tasks/{stopped}/complete", json={"comment": "不应完成"})
        handed = await self.client.post(f"{API}/tasks/{stopped}/handoff", json={
            "recipient": RECIPIENT["username"], "comment": "不应转交",
        })
        self.assertEqual((accepted.status_code, completed.status_code, handed.status_code), (409, 409, 409))
        self.assertEqual((await self.persisted_task(stopped)).status, "已停止")

    async def test_handoff_rejects_unknown_or_inactive_recipient_without_partial_writes(self) -> None:
        self.identity = dict(OWNER)
        task_id = await self.create_task("进行中", "1603")
        for recipient in ("missing-user", "row15-disabled"):
            response = await self.client.post(f"{API}/tasks/{task_id}/handoff", json={
                "recipient": recipient, "comment": "不应写入",
            })
            self.assertEqual(response.status_code, 422, response.text)
            persisted = await self.persisted_task(task_id)
            self.assertEqual((persisted.owner, persisted.status), (OWNER["username"], "进行中"))
            self.assertNotIn("handoff_recipient", persisted.data or {})
        async with self.sessions() as db:
            event_count = len(list((await db.scalars(select(WorkflowEvent).where(
                WorkflowEvent.record_id == task_id
            ))).all()))
        self.assertEqual(event_count, 0)

    async def test_only_initiator_can_withdraw_even_when_current_user_is_admin(self) -> None:
        task_id = await self.create_task("待接收", "1504")
        batch_task_id = await self.create_task("待处理", "1505")
        self.identity = dict(ADMIN)
        denied = await self.client.post(f"{API}/tasks/{task_id}/withdraw", json={"comment": "越权撤回"})
        self.assertEqual(denied.status_code, 403, denied.text)
        batch_denied = await self.client.post(f"{API}/tasks/batch-lifecycle", json={
            "task_ids": [batch_task_id], "action": "withdraw", "comment": "批量越权撤回",
        })
        self.assertEqual(batch_denied.status_code, 403, batch_denied.text)
        self.assertEqual((await self.persisted_task(task_id)).status, "待接收")
        self.assertEqual((await self.persisted_task(batch_task_id)).status, "待处理")

        self.identity = dict(INITIATOR)
        allowed = await self.client.post(f"{API}/tasks/{task_id}/withdraw", json={"comment": "发起人撤回"})
        self.assertEqual(allowed.status_code, 200, allowed.text)
        self.assertEqual((await self.persisted_task(task_id)).status, "已撤回")

    async def test_department_initiated_scope_uses_initiator_membership_not_task_department(self) -> None:
        async with self.sessions() as db:
            db.add_all([
                BusinessRecord(
                    module="task", serial_no="9031801", title="本部门成员发起", customer="",
                    status="待接收", owner=RECIPIENT["username"], department="错误缓存部门",
                    data={"initiator": OWNER["username"], "collaborators": []},
                ),
                BusinessRecord(
                    module="task", serial_no="9031802", title="跨部门成员发起", customer="",
                    status="待接收", owner=RECIPIENT["username"], department=INITIATOR["department"],
                    data={"initiator": ADMIN["username"], "collaborators": []},
                ),
            ])
            await db.commit()
        self.identity = dict(INITIATOR)
        response = await self.client.get(f"{API}/tasks", params={
            "scope": "department", "relation": "initiated", "page_size": 200,
        })
        self.assertEqual(response.status_code, 200, response.text)
        serials = {item["serial_no"] for item in response.json()["items"]}
        self.assertIn("9031801", serials)
        self.assertNotIn("9031802", serials)

    async def test_batch_complete_and_confirm_match_single_task_state_machine(self) -> None:
        self.identity = dict(OWNER)
        pending = await self.create_task("待处理", "1503")
        response = await self.client.post(f"{API}/tasks/batch-lifecycle", json={
            "task_ids": [pending], "action": "complete", "comment": "批量完成",
        })
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual((await self.persisted_task(pending)).status, "已完成")

        rejected = await self.create_task("已拒绝", "1302")
        self.identity = dict(INITIATOR)
        response = await self.client.post(f"{API}/tasks/batch-lifecycle", json={
            "task_ids": [rejected], "action": "confirm", "comment": "批量确认",
        })
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual((await self.persisted_task(rejected)).status, "已验收")

    async def test_automatic_fixed_tasks_also_use_legacy_compact_numbers(self) -> None:
        async with self.sessions() as db:
            case = BusinessRecord(
                module="case", serial_no="CASE-903", title="测试案件", customer="测试客户", status="文书准备",
                owner=OWNER["username"], department="事务部", data={},
            )
            db.add(case)
            await db.flush()
            with patch("app.main.secrets.randbelow", side_effect=[12345, 67890]):
                tasks = await _ensure_case_fixed_tasks(case, db, operator=INITIATOR["username"])
            await db.commit()
            self.assertEqual(len(tasks), 2)
            self.assertTrue(all(len(task.serial_no) == 11 and task.serial_no.isdigit() for task in tasks))


if __name__ == "__main__":
    unittest.main()
