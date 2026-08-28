import unittest

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.main import dashboard, list_tasks
from app.models import BusinessRecord, ContractApprovalStep


IDENTITY = {"username": "admin", "role": "admin"}


class DashboardPersonalTodoScopeRow2Test(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.sessions = async_sessionmaker(
            self.engine, expire_on_commit=False, class_=AsyncSession,
        )
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

    async def asyncTearDown(self):
        await self.engine.dispose()

    @staticmethod
    def record(module: str, serial_no: str, status: str, owner: str, data=None):
        return BusinessRecord(
            module=module,
            serial_no=serial_no,
            title=serial_no,
            customer="CODEX-827-R2-客户",
            status=status,
            owner=owner,
            department="测试部",
            data=data or {},
        )

    @staticmethod
    async def task_queue(db, relation: str, statuses: str):
        return await list_tasks(
            keyword="", status_filter="", reminder_only=False, scope="mine",
            relation=relation, statuses=statuses, page_id=None, priority="",
            serial_no="", title="", description="", initiator="", case_no="",
            source="", owner="", plaintiff="", defendant="", created_from=None,
            created_to=None, deadline_from=None, deadline_to=None, sort_by="deadline",
            sort_order="desc", page=1, page_size=15, identity=IDENTITY, db=db,
        )

    async def test_admin_dashboard_uses_personal_pending_and_rejected_queues(self):
        async with self.sessions() as db:
            pending_task = self.record("task", "CODEX-827-R2-TASK-PENDING", "待处理", "admin")
            processing_task = self.record("task", "CODEX-827-R2-TASK-PROCESSING", "处理中", "admin")
            other_task = self.record("task", "CODEX-827-R2-TASK-OTHER", "待处理", "other")
            rejected_task = self.record(
                "task", "CODEX-827-R2-TASK-REJECTED", "已拒绝", "other",
                {"initiator": "admin"},
            )
            pending_clue = self.record("clue", "CODEX-827-R2-CLUE-PENDING", "待审批", "other")
            rejected_clue = self.record("clue", "CODEX-827-R2-CLUE-REJECTED", "已驳回", "other")
            refused_clue = self.record("clue", "CODEX-827-R2-CLUE-REFUSED", "已拒绝", "other")
            unrelated_clue = self.record("clue", "CODEX-827-R2-CLUE-OTHER", "待取证", "admin")
            investigation_task = self.record(
                "task", "CODEX-827-R2-TASK-INVESTIGATION", "待处理", "admin",
                {"source": "调查任务"},
            )
            auto_completed_task = self.record(
                "task", "CODEX-827-R2-TASK-AUTO", "待接收", "admin",
                {"handoff_auto_complete_at": "2020-01-01"},
            )
            overdue_task = self.record(
                "task", "CODEX-827-R2-TASK-OVERDUE", "待处理", "admin",
                {"deadline": "2020-01-01"},
            )
            pending_contract = self.record("contract", "CODEX-827-R2-CONTRACT-PENDING", "审批中", "other")
            rejected_contract = self.record("contract", "CODEX-827-R2-CONTRACT-REJECTED", "已驳回", "admin")
            other_rejected_contract = self.record("contract", "CODEX-827-R2-CONTRACT-OTHER", "已驳回", "other")
            pending_seal = self.record(
                "seal", "CODEX-827-R2-SEAL-PENDING", "待审批", "other",
                {"approver": "admin"},
            )
            other_seal = self.record(
                "seal", "CODEX-827-R2-SEAL-OTHER", "待审批", "other",
                {"approver": "other"},
            )
            rejected_seal = self.record("seal", "CODEX-827-R2-SEAL-REJECTED", "已拒绝", "admin")
            pending_archive = self.record(
                "case", "CODEX-827-R2-ARCHIVE-PENDING", "待归档审核", "admin",
                {"archive_submitter": "other"},
            )
            other_pending_archive = self.record(
                "case", "CODEX-827-R2-ARCHIVE-OTHER", "待归档审核", "other",
                {"archive_submitter": "other"},
            )
            own_pending_archive = self.record(
                "case", "CODEX-827-R2-ARCHIVE-OWN", "待归档审核", "admin",
                {"archive_submitter": "admin"},
            )
            rejected_archive = self.record(
                "case", "CODEX-827-R2-ARCHIVE-REJECTED", "执行", "admin",
                {"archive_submitter": "admin", "archive_reject_reason": "材料不全"},
            )
            db.add_all([
                pending_task, processing_task, other_task, rejected_task, investigation_task, auto_completed_task, overdue_task,
                pending_clue, rejected_clue, refused_clue, unrelated_clue,
                pending_contract, rejected_contract, other_rejected_contract,
                pending_seal, other_seal, rejected_seal,
                pending_archive, other_pending_archive, own_pending_archive, rejected_archive,
            ])
            await db.flush()
            db.add(ContractApprovalStep(
                contract_record_id=pending_contract.id,
                step_order=1,
                approver="admin",
                status="待审批",
            ))
            await db.commit()

            result = await dashboard(IDENTITY, db)
            pending_queue = await self.task_queue(db, "owned", "待接收,待处理")
            rejected_queue = await self.task_queue(db, "initiated", "已拒绝")

        todos = {row[0]: (row[1], row[2]) for row in result["todos"]}
        self.assertEqual(todos["待处理任务"], (1, 1))
        self.assertEqual(todos["待处理任务"], (pending_queue["total"], rejected_queue["total"]))
        self.assertEqual(todos["待审批线索"], (1, 2))
        self.assertEqual(todos["待审批合同"], (1, 1))
        self.assertEqual(todos["待审批用印"], (1, 1))
        self.assertEqual(todos["待审核归档"], (1, 1))
        self.assertEqual(auto_completed_task.status, "已完成")


if __name__ == "__main__":
    unittest.main()
