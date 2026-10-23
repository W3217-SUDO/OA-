"""10.22 批次任务 D 后端聚焦回归。

- 第13行：检察院信息按审级单独保存，未提交的审级保留原值（exclude_unset 合并）。
- 第14行：案件建成后（三步完成）刑事资料维护不再要求案件主管审批；未完成三步、归档中仍阻断。
- 第9行法律顾问（用户答复“第9行是加一个”）：新建与修改基本信息保存选填案由并可回读。
"""

from __future__ import annotations

import unittest
from datetime import date

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database import Base, get_db
from app.main import app
from app.models import BusinessRecord, Department, User, WorkflowEvent
from app.security import current_identity


API = settings.api_prefix
PREFIX = "CODEX-1022-14-"
IDENTITY = {
    "username": "codex-1022-admin",
    "role": "admin",
    "role_ids": ["admin"],
    "display_name": "CODEX-1022 管理员",
    "department": "诉讼一部",
}


class CaseDetail1022CriminalCounselTest(unittest.IsolatedAsyncioTestCase):
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
            db.add(Department(code="CODEX-1022-DEPT", name=IDENTITY["department"], is_active=True))
            db.add(User(
                username=IDENTITY["username"], display_name=IDENTITY["display_name"], department=IDENTITY["department"],
                role="admin", role_ids=["admin"], password_hash="x", profile={"position": "律师"}, is_active=True,
            ))
            pending = self._criminal_case(f"{PREFIX}PENDING", {"case_creation_step": "completed", "case_creation_approval_status": "待审批"}, status="待立案审批")
            draft = self._criminal_case(f"{PREFIX}DRAFT", {"case_creation_step": "judicial", "case_creation_approval_status": ""})
            archived = self._criminal_case(f"{PREFIX}ARCHIVED", {"case_creation_step": "completed", "case_creation_approval_status": "已通过"}, status="已归档")
            customer = BusinessRecord(
                module="customer", serial_no="CODEX-1022-9-CUSTOMER", title="CODEX-1022-9 客户", customer="",
                status="正常", owner=IDENTITY["username"], department=IDENTITY["department"], data={"organization_type": "企业", "credit_code": "CODEX1022CREDIT0009"},
            )
            db.add(customer)
            await db.flush()
            contract = BusinessRecord(
                module="contract", serial_no="CODEX-1022-9-CONTRACT", title="CODEX-1022-9 顾问合同", customer="CODEX-1022-9 客户",
                status="已通过", owner=IDENTITY["username"], department=IDENTITY["department"],
                data={"type": "general", "amount": "1.00", "shared_with": [], "customer_id": customer.id, "customer_no": customer.serial_no},
            )
            db.add_all([pending, draft, archived, contract])
            await db.flush()
            self.pending_id, self.draft_id, self.archived_id, self.contract_id = pending.id, draft.id, archived.id, contract.id
            await db.commit()
        self.previous_overrides = dict(app.dependency_overrides)
        app.dependency_overrides[get_db] = self.override_db
        app.dependency_overrides[current_identity] = lambda: IDENTITY
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://case-detail-1022.test")

    @staticmethod
    def _criminal_case(serial_no: str, extra: dict, status: str = "在办") -> BusinessRecord:
        return BusinessRecord(
            module="case", serial_no=serial_no, title=f"{serial_no} 刑事案件", customer="CODEX-1022 客户", status=status,
            owner=IDENTITY["username"], department=IDENTITY["department"],
            data={
                "case_type": "刑事案件",
                "case_team_usernames": [IDENTITY["username"]],
                "first_procuratorate_name": "原一审检察院",
                "retrial_procuratorate_name": "原再审检察院",
                **extra,
            },
        )

    async def asyncTearDown(self) -> None:
        await self.client.aclose()
        app.dependency_overrides.clear()
        app.dependency_overrides.update(self.previous_overrides)
        await self.engine.dispose()

    async def override_db(self):
        async with self.sessions() as db:
            yield db

    async def test_row14_pending_approval_case_can_maintain_procuratorate_public_security_and_courts(self) -> None:
        response = await self.client.put(f"{API}/cases/{self.pending_id}/criminal/procuratorates", json={
            "second_procuratorate_name": f"{PREFIX}二审检察院",
            "second_procuratorate_case_no": "二检案号",
            "second_procuratorate_address": "地址",
            "second_procuratorate_operator": "经办人",
            "second_procuratorate_phone": "123",
        })
        self.assertEqual(response.status_code, 200, response.text)
        self.assertNotIn("主管审批", response.text)
        for path, payload in (
            ("public-security", {"public_security_name": f"{PREFIX}公安"}),
            ("courts", {"first_court_enabled": True, "first_court_name": f"{PREFIX}法院"}),
        ):
            result = await self.client.put(f"{API}/cases/{self.pending_id}/criminal/{path}", json=payload)
            self.assertEqual(result.status_code, 200, result.text)
        async with self.sessions() as db:
            record = await db.get(BusinessRecord, self.pending_id)
            self.assertEqual(record.data["case_creation_approval_status"], "待审批", "放开维护不改变审批状态")
            self.assertEqual(record.data["public_security_name"], f"{PREFIX}公安")
            actions = [event.action for event in (await db.scalars(select(WorkflowEvent).where(WorkflowEvent.record_id == self.pending_id))).all()]
            self.assertIn("修改刑事案件检察院信息", actions)

    async def test_row13_single_level_save_keeps_other_levels(self) -> None:
        response = await self.client.put(f"{API}/cases/{self.pending_id}/criminal/procuratorates", json={"second_procuratorate_name": f"{PREFIX}二审"})
        self.assertEqual(response.status_code, 200, response.text)
        data = response.json()["data"]
        self.assertEqual(data["second_procuratorate_name"], f"{PREFIX}二审")
        self.assertEqual(data["first_procuratorate_name"], "原一审检察院")
        self.assertEqual(data["retrial_procuratorate_name"], "原再审检察院")
        self.assertNotIn("second_procuratorate_phone", data, "未提交字段不写默认空值")
        too_long = await self.client.put(f"{API}/cases/{self.pending_id}/criminal/procuratorates", json={"first_procuratorate_name": "检" * 300})
        self.assertEqual(too_long.status_code, 422, too_long.text)

    async def test_row14_incomplete_creation_and_archived_cases_still_blocked(self) -> None:
        draft = await self.client.put(f"{API}/cases/{self.draft_id}/criminal/procuratorates", json={"first_procuratorate_name": "不应写入"})
        self.assertEqual(draft.status_code, 409, draft.text)
        self.assertIn("三步", draft.text)
        archived = await self.client.put(f"{API}/cases/{self.archived_id}/criminal/procuratorates", json={"first_procuratorate_name": "不应写入"})
        self.assertEqual(archived.status_code, 409, archived.text)
        async with self.sessions() as db:
            for case_id in (self.draft_id, self.archived_id):
                self.assertEqual((await db.get(BusinessRecord, case_id)).data["first_procuratorate_name"], "原一审检察院")

    async def test_row9_counsel_case_create_and_basic_edit_persist_optional_cause(self) -> None:
        payload = {
            "contract_record_id": self.contract_id,
            "title": "CODEX-1022-9 法律顾问案件",
            "status": "新案待分配",
            "owner": IDENTITY["username"],
            "case_type": "法律顾问",
            "client_position": "",
            "cause_or_charge": "  合同纠纷  ",
            "counsel_type": "常年法律顾问",
            "counsel_start": "2026-10-01",
            "counsel_end": "2027-09-30",
            "handling_lawyers": [IDENTITY["username"]],
            "source_person": IDENTITY["username"],
        }
        created = await self.client.post(f"{API}/cases", json=payload)
        self.assertEqual(created.status_code, 201, created.text)
        case_id = created.json()["id"]
        self.assertEqual(created.json()["data"]["cause_or_charge"], "合同纠纷")
        without_cause = await self.client.post(f"{API}/cases", json={**payload, "title": "CODEX-1022-9 无案由顾问", "cause_or_charge": ""})
        self.assertEqual(without_cause.status_code, 201, without_cause.text)
        self.assertEqual(without_cause.json()["data"].get("cause_or_charge", ""), "")

        async with self.sessions() as db:
            record = await db.get(BusinessRecord, case_id)
            record.data = {**(record.data or {}), "case_creation_step": "completed"}
            await db.commit()
        edit = {
            "title": "CODEX-1022-9 法律顾问案件",
            "counsel_type": "常年法律顾问",
            "counsel_start": str(date(2026, 10, 1)),
            "counsel_end": str(date(2027, 9, 30)),
            "handling_lawyers": [IDENTITY["username"]],
            "assistant": "",
        }
        kept = await self.client.put(f"{API}/cases/{case_id}/counsel-basic", json=edit)
        self.assertEqual(kept.status_code, 200, kept.text)
        self.assertEqual(kept.json()["data"]["cause_or_charge"], "合同纠纷", "未提交案由时保留原值")
        changed = await self.client.put(f"{API}/cases/{case_id}/counsel-basic", json={**edit, "cause_or_charge": "劳动争议"})
        self.assertEqual(changed.status_code, 200, changed.text)
        async with self.sessions() as db:
            self.assertEqual((await db.get(BusinessRecord, case_id)).data["cause_or_charge"], "劳动争议")
            event = await db.scalar(select(WorkflowEvent).where(WorkflowEvent.record_id == case_id, WorkflowEvent.action == "修改法律顾问案件基本信息").order_by(WorkflowEvent.id.desc()))
            self.assertIn("案由：合同纠纷", event.comment)


if __name__ == "__main__":
    unittest.main()
