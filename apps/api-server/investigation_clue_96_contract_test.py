import unittest

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.main import get_investigation_clue_workspace, list_records
from app.models import BusinessRecord, FileAttachment, JobRole, RolePermission, User


class InvestigationClue96ContractTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with self.sessions() as db:
            db.add(RolePermission(
                role="user", display_name="普通用户", data_scope="全所数据",
                menu_keys=["investigation"], field_keys=[],
            ))
            db.add_all([
                JobRole(code="CODEX-CLUE-REVIEW", name="线索审核岗位", permissions=["investigation", "线索审批"], is_active=True),
                JobRole(code="CODEX-CLUE-NO-REVIEW", name="线索普通岗位", permissions=["investigation"], is_active=True),
            ])
            db.add_all([
                User(
                    username="clue_reviewer", display_name="线索审核员", department="调查部",
                    role="user", role_ids=["user"], password_hash="x", is_active=True,
                    profile={"permission_role": "线索审核岗位"},
                ),
                User(
                    username="clue_submitter", display_name="线索发起人", department="调查部",
                    role="user", role_ids=["user"], password_hash="x", is_active=True,
                    profile={"permission_role": "线索普通岗位"},
                ),
                User(
                    username="file_uploader", display_name="文件上传人", department="调查部",
                    role="user", role_ids=["user"], password_hash="x", is_active=True,
                    profile={"permission_role": "线索普通岗位"},
                ),
            ])
            task = BusinessRecord(
                module="task", serial_no="CODEX-96-TASK", title="调查任务", customer="测试客户",
                status="待处理", owner="clue_submitter", department="调查部",
                data={
                    "start_date": "2026-09-01", "end_date": "2026-09-10",
                    "assigner": "clue_reviewer",
                },
            )
            db.add(task)
            await db.flush()
            clue = BusinessRecord(
                module="clue", serial_no="CODEX-96-CLUE", title="测试线索", customer="测试客户",
                status="待审批", owner="clue_submitter", department="调查部",
                data={
                    "source_task_id": task.id,
                    "source_task_no": task.serial_no,
                    "indictees": [{
                        "nature": "企业", "name": "测试主体", "confirmation_method": "现场核验",
                        "identity_no": "统一社会信用代码", "region": ["上海市", "浦东新区"],
                        "business_address": "测试地址",
                    }],
                },
            )
            refused = BusinessRecord(
                module="clue", serial_no="CODEX-96-REFUSED", title="已拒绝线索", customer="测试客户",
                status="已驳回", owner="clue_submitter", department="调查部", data={},
            )
            db.add_all([clue, refused])
            await db.flush()
            db.add(FileAttachment(
                record_id=clue.id, category="线索文件", original_name="证据.txt", stored_name="codex-96.txt",
                content_type="text/plain", size=4, path="/tmp/codex-96.txt", uploader="file_uploader", remark="",
            ))
            await db.commit()

    async def asyncTearDown(self):
        await self.engine.dispose()

    async def test_audit_scope_requires_clue_review_job_permission(self):
        async with self.sessions() as db:
            reviewer = await list_records(
                module="clue", keyword="", record_status="", scope="audit", statuses="待审批",
                customer_id=None, customer="", customer_no="", exclude_archived=False,
                title="", serial_no="", record_type="", case_no="", fee_type="", contract_body="",
                source_person="", signed_at_start="", signed_at_end="", investigation_view="",
                archive_view="", pending_approver_only=False, page=1, page_size=20,
                identity={"username": "clue_reviewer", "role": "user", "role_ids": ["user"]}, db=db,
            )
            ordinary = await list_records(
                module="clue", keyword="", record_status="", scope="audit", statuses="待审批",
                customer_id=None, customer="", customer_no="", exclude_archived=False,
                title="", serial_no="", record_type="", case_no="", fee_type="", contract_body="",
                source_person="", signed_at_start="", signed_at_end="", investigation_view="",
                archive_view="", pending_approver_only=False, page=1, page_size=20,
                identity={"username": "clue_submitter", "role": "user", "role_ids": ["user"]}, db=db,
            )

        self.assertEqual(reviewer["total"], 1)
        self.assertEqual(reviewer["items"][0]["serial_no"], "CODEX-96-CLUE")
        self.assertEqual(ordinary["total"], 0)

    async def test_workspace_resolves_uploader_and_source_task_fields(self):
        async with self.sessions() as db:
            clue = await db.scalar(select(BusinessRecord).where(BusinessRecord.serial_no == "CODEX-96-CLUE"))
            workspace = await get_investigation_clue_workspace(
                clue.id,
                {"username": "clue_reviewer", "role": "admin"},
                db,
            )

        self.assertEqual(workspace["clue_files"][0]["uploader_display_name"], "文件上传人")
        self.assertEqual(workspace["clue"]["data"]["source_task_start_date"], "2026-09-01")
        self.assertEqual(workspace["clue"]["data"]["source_task_end_date"], "2026-09-10")
        self.assertEqual(workspace["clue"]["data"]["source_task_assigner_display_name"], "线索审核员")


if __name__ == "__main__":
    unittest.main()
