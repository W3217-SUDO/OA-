import unittest
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool
from fastapi import HTTPException

from app.database import Base
from app.main import (
    InvestigationTaskInput,
    RecordInput,
    _ensure_record_visible,
    create_investigation_record,
    create_investigation_task,
    list_investigation_tasks,
    list_records,
)
from app.models import BusinessRecord, SystemConfig, User


class InvestigationTaskAssigneeContractAccessTest(unittest.IsolatedAsyncioTestCase):
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

    async def test_assignee_can_create_subtask_from_assigned_survey_with_bound_contract(self):
        async with self.sessions() as db:
            db.add_all([
                User(username="admin", display_name="管理员", department="总部", password_hash="x", role="admin"),
                User(username="fwl", display_name="范文玲", department="调查部", password_hash="x", role="user"),
            ])
            contract = BusinessRecord(
                module="contract", serial_no="HT-CODEX-ASSIGNEE", title="管理员合同",
                customer="CODEX 客户", status="已通过", owner="admin", department="总部", data={},
            )
            db.add(contract)
            await db.flush()
            survey = BusinessRecord(
                module="investigation", serial_no="DC-CODEX-ASSIGNEE", title="范文玲调查任务",
                customer="CODEX 客户", status="待分配", owner="fwl", department="调查部",
                data={"contract_id": contract.id, "contract_no": contract.serial_no},
            )
            db.add(survey)
            await db.commit()

            result = await create_investigation_task(
                survey.id,
                InvestigationTaskInput(title="范文玲子任务", owner="fwl", deadline=date.today()),
                {"username": "fwl", "role": "user"},
                db,
            )

        self.assertEqual(result["owner"], "fwl")
        self.assertEqual(result["data"]["investigation_record_id"], survey.id)
        self.assertEqual(result["data"]["contract_id"], contract.id)

        async with self.sessions() as db:
            with self.assertRaises(HTTPException):
                await _ensure_record_visible(
                    contract.id, {"username": "fwl", "role": "user"}, db
                )

    async def test_configured_supervisor_can_assign_another_user_and_both_can_see_child(self):
        async with self.sessions() as db:
            db.add_all([
                User(username="admin", display_name="管理员", department="总部", password_hash="x", role="admin"),
                User(username="fwl", display_name="范文玲", department="调查部", password_hash="x", role="user"),
                User(username="investigator", display_name="调查员甲", department="调查部", password_hash="x", role="user"),
                SystemConfig(
                    key="investigation_assignment", label="调查任务分配人",
                    value={"supervisor_username": "fwl"}, updated_by="admin",
                ),
            ])
            contract = BusinessRecord(
                module="contract", serial_no="HT-CODEX-DELEGATE", title="调查合同",
                customer="CODEX 双账号客户", status="已通过", owner="admin", department="总部", data={},
            )
            db.add(contract)
            await db.flush()
            survey = BusinessRecord(
                module="investigation", serial_no="DC-CODEX-DELEGATE", title="合同父调查任务",
                customer="CODEX 双账号客户", status="进行中", owner="fwl", department="调查部",
                data={
                    "contract_id": contract.id, "contract_no": contract.serial_no,
                    "publisher": "admin", "authorized_from": "2026-08-12",
                    "authorized_to": "2026-09-12", "region": "全国",
                    "source_owner": "admin", "assigner": "admin", "right_type": "商标",
                },
            )
            db.add(survey)
            await db.commit()

            created = await create_investigation_task(
                survey.id,
                InvestigationTaskInput(
                    title="分配给调查员甲", owner="investigator", deadline=date(2026, 9, 11),
                ),
                {"username": "fwl", "role": "user"},
                db,
            )
            supervisor_view = await list_investigation_tasks(
                survey.id, {"username": "fwl", "role": "user"}, db,
            )
            investigator_view = await list_records(
                module="task", keyword="", record_status="", scope="all", statuses="",
                customer_id=None, customer="", customer_no="", exclude_archived=False,
                investigation_view="", page=1, page_size=100,
                identity={"username": "investigator", "role": "user"}, db=db,
            )

        self.assertEqual(created["owner"], "investigator")
        self.assertEqual(created["owner_display_name"], "调查员甲")
        self.assertEqual(created["data"]["investigation_record_id"], survey.id)
        self.assertEqual(created["data"]["investigation_no"], survey.serial_no)
        self.assertEqual(created["data"]["authorized_from"], "2026-08-12")
        self.assertEqual(created["data"]["authorized_to"], "2026-09-12")
        self.assertEqual(created["data"]["region"], "全国")
        self.assertEqual(created["data"]["source_owner"], "admin")
        self.assertEqual({item["id"] for item in supervisor_view["items"]}, {created["id"]})
        self.assertEqual({item["id"] for item in investigator_view["items"]}, {created["id"]})
        investigator_row = investigator_view["items"][0]
        self.assertEqual(investigator_row["owner_display_name"], "调查员甲")
        self.assertEqual(investigator_row["data"]["source_owner_display_name"], "管理员")

    async def test_generic_parent_creation_requires_a_contract_without_migrating_legacy_rows(self):
        async with self.sessions() as db:
            db.add(User(
                username="admin", display_name="管理员", department="总部",
                password_hash="x", role="admin",
            ))
            await db.commit()

            with self.assertRaises(HTTPException) as caught:
                await create_investigation_record(
                    RecordInput(
                        module="investigation", serial_no="DC-CODEX-NO-CONTRACT",
                        title="无合同父任务", owner="admin",
                    ),
                    {"username": "admin", "role": "admin"},
                    db,
                )

        self.assertEqual(caught.exception.status_code, 422)
        self.assertIn("必须从合同创建", str(caught.exception.detail))


if __name__ == "__main__":
    unittest.main()
