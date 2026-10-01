"""9.4 row 3: document-preparation stage task automation."""

import unittest

import httpx
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database import Base, get_db
from app.main import app
from app.models import BusinessRecord, Notification, RolePermission, SystemParameter, User, WorkflowEvent
from app.security import current_identity


API = settings.api_prefix
ADMIN = {"username": "row3-admin", "role": "admin", "display_name": "管理员", "department": "管理部"}
LAWYER = {"username": "row3-lawyer", "role": "user", "display_name": "经办律师", "department": "诉讼部"}
ASSISTANT = {"username": "row3-assistant", "role": "user", "display_name": "律师助理", "department": "诉讼部"}
TIMESTAMP_OWNER = {"username": "row4-owner", "role": "user", "display_name": "范应根", "department": "调查部"}


class DocumentPreparationAutoTask94Row3Test(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with self.sessions() as db:
            for identity in (ADMIN, LAWYER, ASSISTANT, TIMESTAMP_OWNER):
                db.add(User(
                    username=identity["username"],
                    display_name=identity["display_name"],
                    department=identity["department"],
                    role=identity["role"],
                    password_hash="x",
                    is_active=True,
                ))
            db.add(RolePermission(
                role="user",
                display_name="普通用户",
                data_scope="本人及共享数据",
                menu_keys=["case", "@action:case.phase.update"],
                field_keys=[],
            ))
            customer = BusinessRecord(
                module="customer",
                serial_no="CODEX-94-CUSTOMER",
                title="测试客户",
                customer="",
                status="正常",
                owner=ADMIN["username"],
                department="诉讼部",
                data={},
            )
            db.add(customer)
            phase = SystemParameter(
                category="case_phase",
                code="DOCUMENT",
                name="文书准备",
                sort_order=20,
                is_active=True,
                extra={"case_type": "民事争议", "parent_code": "NEW"},
            )
            db.add(phase)
            await db.flush()
            self.phase_id = phase.id
            self.customer_id = customer.id
            await db.commit()

        self.identity = dict(ADMIN)
        self.previous_overrides = dict(app.dependency_overrides)
        app.dependency_overrides[get_db] = self.override_db
        app.dependency_overrides[current_identity] = lambda: self.identity
        self.client = httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://document-preparation-task.test",
        )

    async def asyncTearDown(self) -> None:
        await self.client.aclose()
        app.dependency_overrides.clear()
        app.dependency_overrides.update(self.previous_overrides)
        await self.engine.dispose()

    async def override_db(self):
        async with self.sessions() as db:
            yield db

    async def create_case(self, serial_no: str, status: str, *, with_team: bool) -> int:
        data = {
            "case_type": "民事争议",
            "case_creation_step": "completed",
            "case_creation_approval_status": "已通过",
        }
        if with_team:
            data.update({
                "handling_lawyers": [LAWYER["display_name"]],
                "handling_lawyer_usernames": [LAWYER["username"]],
                "assistant": ASSISTANT["display_name"],
                "assistants": [ASSISTANT["display_name"]],
                "assistant_username": ASSISTANT["username"],
                "assistant_usernames": [ASSISTANT["username"]],
                "case_team_usernames": [LAWYER["username"], ASSISTANT["username"]],
            })
        async with self.sessions() as db:
            record = BusinessRecord(
                module="case",
                serial_no=serial_no,
                title=f"{serial_no} 案件",
                customer="测试客户",
                status=status,
                owner=ADMIN["username"],
                department="诉讼部",
                data=data,
            )
            db.add(record)
            await db.commit()
            await db.refresh(record)
            return record.id

    async def tasks_for_case(self, case_id: int) -> list[BusinessRecord]:
        async with self.sessions() as db:
            return list((await db.scalars(select(BusinessRecord).where(
                BusinessRecord.module == "task",
                BusinessRecord.data["case_id"].as_integer() == case_id,
            ).order_by(BusinessRecord.id))).all())

    async def test_assignment_creates_complete_legacy_task_once(self) -> None:
        case_id = await self.create_case("CODEX-94-R3-ASSIGN", "新案待分配", with_team=False)
        payload = {
            "customer_manager": "",
            "hearing_lawyer": LAWYER["username"],
            "handling_lawyers": [LAWYER["username"]],
            "assistant": ASSISTANT["username"],
            "comment": "分配人员",
        }
        first = await self.client.post(f"{API}/cases/{case_id}/assign", json=payload)
        second = await self.client.post(f"{API}/cases/{case_id}/assign", json=payload)
        self.assertEqual((first.status_code, second.status_code), (200, 200), second.text)

        tasks = await self.tasks_for_case(case_id)
        self.assertEqual(len(tasks), 1)
        task = tasks[0]
        data = task.data or {}
        self.assertEqual((task.title, task.status, task.owner), ("文书准备阶段", "待接收", ASSISTANT["username"]))
        self.assertEqual(data["initiator"], LAWYER["username"])
        self.assertEqual(data["collaborators"], [ASSISTANT["username"]])
        self.assertEqual(data["creation_mode"], "自动")
        self.assertEqual(data["task_type"], "自动任务")
        self.assertEqual(data["source"], "案件任务")
        self.assertEqual(data["auto_task_type"], "document_preparation_stage")
        self.assertEqual(data["case_no"], "CODEX-94-R3-ASSIGN")
        self.assertEqual(data["case_nos"], ["CODEX-94-R3-ASSIGN"])
        self.assertEqual(data["case_id"], case_id)
        self.assertEqual(data["case_record_id"], case_id)
        self.assertEqual(data["case_ids"], [case_id])
        self.assertEqual(data["case_module"], "case")
        self.assertEqual(data["case_stage"], "文书准备")
        self.assertEqual(task.description, "CODEX-94-R3-ASSIGN已经分案,尽快完成文书.")
        start_year, start_month, start_day = map(int, data["start_at"].split("-"))
        end_year, end_month, end_day = map(int, data["deadline"].split("-"))
        self.assertEqual((end_year * 12 + end_month) - (start_year * 12 + start_month), 1)
        self.assertLessEqual(end_day, start_day)
        self.assertEqual(data["end_at"], data["deadline"])

        async with self.sessions() as db:
            case_record = await db.get(BusinessRecord, case_id)
            task_events = list((await db.scalars(select(WorkflowEvent).where(
                WorkflowEvent.record_id == task.id,
            ))).all())
            notice_count = int(await db.scalar(select(func.count(Notification.id)).where(
                Notification.source_type == "task",
                Notification.source_id == task.id,
            )) or 0)
        self.assertEqual((case_record.data or {})["document_preparation_task_id"], task.id)
        self.assertEqual([event.action for event in task_events], ["系统生成文书准备阶段任务"])
        self.assertEqual(task_events[0].operator, LAWYER["username"])
        self.assertEqual(
            task_events[0].comment,
            "经办律师新建任务给负责人(律师助理)，协作人(律师助理)，附言：\n\n"
            "CODEX-94-R3-ASSIGN已经分案,尽快完成文书.",
        )
        self.assertEqual(notice_count, 1)

        for identity, relation in (
            (LAWYER, "initiated"),
            (ASSISTANT, "owned"),
            (ASSISTANT, "collaborating"),
        ):
            self.identity = dict(identity)
            response = await self.client.get(f"{API}/tasks", params={
                "relation": relation,
                "case_no": "CODEX-94-R3-ASSIGN",
            })
            self.assertEqual(response.status_code, 200, response.text)
            items = response.json()["items"]
            self.assertEqual(len(items), 1)
            self.assertEqual(items[0]["title"], "文书准备阶段")
            self.assertEqual(items[0]["initiator_display_name"], LAWYER["display_name"])
            self.assertEqual(items[0]["owner_display_name"], ASSISTANT["display_name"])
            self.assertEqual(items[0]["collaborator_display_names"], [ASSISTANT["display_name"]])
        self.identity = dict(ADMIN)

    async def test_phase_change_creates_task_and_missing_assistant_does_not(self) -> None:
        ready_id = await self.create_case("CODEX-94-R3-PHASE", "新案待分配", with_team=True)
        missing_id = await self.create_case("CODEX-94-R3-NOASSIST", "新案待分配", with_team=False)
        response = await self.client.post(f"{API}/cases/phase-change", json={
            "case_nos": ["CODEX-94-R3-PHASE", "CODEX-94-R3-NOASSIST"],
            "case_phase_id": self.phase_id,
            "comment": "进入文书准备",
        })
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(len(await self.tasks_for_case(ready_id)), 1)
        self.assertEqual(await self.tasks_for_case(missing_id), [])

    async def test_normal_basic_entry_creates_document_and_timestamp_tasks_once(self) -> None:
        case_id = await self.create_case("CODEX-94-R3-R4-NORMAL", "新案待分配", with_team=True)
        async with self.sessions() as db:
            case_record = await db.get(BusinessRecord, case_id)
            case_record.data = {**(case_record.data or {}), "source_is_timestamp_evidence": True}
            await db.commit()
        payload = {
            "customer_record_id": self.customer_id,
            "title": "普通基本信息入口案件",
            "case_phase": "文书准备",
            "cause_or_charge": "合同纠纷",
            "handling_lawyers": [LAWYER["username"]],
            "assistants": [ASSISTANT["username"]],
            "assistant": ASSISTANT["username"],
            "business_owner": "",
            "investigator": "",
            "investigation_clue_ids": [],
            "right_type": "",
            "source_person": "",
            "comment": "经普通基本信息入口进入文书准备",
        }
        first = await self.client.put(f"{API}/cases/{case_id}/normal-basic", json=payload)
        second = await self.client.put(f"{API}/cases/{case_id}/normal-basic", json=payload)
        self.assertEqual((first.status_code, second.status_code), (200, 200), second.text)
        tasks = await self.tasks_for_case(case_id)
        self.assertEqual(
            [(task.title, task.owner) for task in tasks],
            [("文书准备阶段", ASSISTANT["username"]), ("交接时间戳文件", TIMESTAMP_OWNER["username"])],
        )


if __name__ == "__main__":
    unittest.main()
