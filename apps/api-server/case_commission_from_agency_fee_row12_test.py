import unittest

import httpx
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database import Base, get_db
from app.main import app
from app.models import BusinessRecord, HrSubrecord, User
from app.security import current_identity


API = settings.api_prefix
IDENTITY = {
    "username": "row12-admin",
    "role": "admin",
    "display_name": "第12行管理员",
    "department": "上海分所",
}


class CaseCommissionFromAgencyFeeRow12Test(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine(
            "sqlite+aiosqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with self.sessions() as db:
            db.add(User(
                username=IDENTITY["username"], display_name=IDENTITY["display_name"],
                department=IDENTITY["department"], role="admin", password_hash="x", is_active=True,
            ))
            employees = []
            for username, display_name in (
                ("row12-hearing", "开庭律师甲"),
                ("row12-assistant", "律师助理乙"),
                ("row12-source", "案源人丙"),
                ("row12-investigator", "调查员丁"),
            ):
                db.add(User(
                    username=username, display_name=display_name, department=IDENTITY["department"],
                    role="user", password_hash="x", is_active=True,
                ))
                employee = BusinessRecord(
                    module="hr", serial_no=f"CODEX-831-R12-HR-{len(employees) + 1}",
                    title=display_name, customer="", status="在职", owner=username,
                    department=IDENTITY["department"], data={"username": username, "is_active": True},
                )
                db.add(employee)
                employees.append(employee)
            await db.flush()
            db.add_all([
                HrSubrecord(
                    employee_id=employees[0].id, kind="commission",
                    data={"start_date": "2020-01-01", "end_date": "", "hearing_rate": 0.05, "hearing_fixed": 0},
                    created_by=IDENTITY["username"], updated_by=IDENTITY["username"],
                ),
                HrSubrecord(
                    employee_id=employees[1].id, kind="commission",
                    data={"start_date": "2020-01-01", "end_date": "", "document_rate": 0, "document_fixed": 0},
                    created_by=IDENTITY["username"], updated_by=IDENTITY["username"],
                ),
                HrSubrecord(
                    employee_id=employees[2].id, kind="commission",
                    data={"start_date": "2020-01-01", "end_date": "", "source_rate": 0, "source_fixed": 300},
                    created_by=IDENTITY["username"], updated_by=IDENTITY["username"],
                ),
                HrSubrecord(
                    employee_id=employees[3].id, kind="commission",
                    data={"start_date": "2020-01-01", "end_date": "", "investigation_rate": 0.10, "investigation_fixed": 0},
                    created_by=IDENTITY["username"], updated_by=IDENTITY["username"],
                ),
            ])
            case = BusinessRecord(
                module="case", serial_no="CODEX-831-R12-CASE", title="第12行提成测试案件",
                customer="第12行客户", status="一审立案受理", owner=IDENTITY["username"],
                department=IDENTITY["department"],
                data={
                    "case_type": "民事争议", "case_creation_step": "completed",
                    "hearing_lawyer_username": "row12-hearing",
                    "assistant": "律师助理乙",
                    "source_person_username": "row12-source",
                    "investigator": "调查员丁",
                },
            )
            db.add(case)
            await db.flush()
            fee = BusinessRecord(
                module="finance", serial_no="CODEX-831-R12-FEE", title="代理费",
                customer=case.customer, status="草稿", owner=IDENTITY["username"],
                department=IDENTITY["department"],
                data={"fee_type": "代理费", "expense_scope": "律所", "expense_subtype": "代理费", "amount": 8400, "case_id": case.id, "case_no": case.serial_no},
            )
            other_fee = BusinessRecord(
                module="finance", serial_no="CODEX-831-R12-OFFICIAL", title="官费",
                customer=case.customer, status="草稿", owner=IDENTITY["username"],
                department=IDENTITY["department"],
                data={"fee_type": "官方费用", "expense_scope": "律所", "expense_subtype": "官费", "amount": 500, "case_id": case.id, "case_no": case.serial_no},
            )
            db.add_all([fee, other_fee])
            await db.commit()
            self.case_id, self.fee_id, self.other_fee_id = case.id, fee.id, other_fee.id

        async def override_db():
            async with self.sessions() as db:
                yield db

        self.previous = dict(app.dependency_overrides)
        app.dependency_overrides[get_db] = override_db
        app.dependency_overrides[current_identity] = lambda: IDENTITY
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://row12.test")

    async def asyncTearDown(self):
        await self.client.aclose()
        app.dependency_overrides.clear()
        app.dependency_overrides.update(self.previous)
        await self.engine.dispose()

    async def test_preview_uses_selected_fee_case_people_and_commission_settings(self):
        response = await self.client.get(
            f"{API}/cases/{self.case_id}/commission-preview",
            params={"source_fee_id": self.fee_id},
        )
        self.assertEqual(response.status_code, 200, response.text)
        data = response.json()
        self.assertEqual(data["source_fee"]["amount"], 8400)
        rows = {item["commission_type"]: item for item in data["items"]}
        self.assertEqual(rows["开庭提成"]["employee_display_name"], "开庭律师甲")
        self.assertEqual(rows["开庭提成"]["base_amount"], 8400)
        self.assertEqual(rows["开庭提成"]["reference_commission"], 420)
        self.assertEqual(rows["案源固定提成"]["reference_commission"], 300)
        self.assertEqual(rows["调查提成"]["reference_commission"], 840)
        self.assertIn("律师助理乙未设文书提成", data["missing_messages"])

    async def test_batch_create_is_atomic_and_persists_source_relation(self):
        preview = (await self.client.get(
            f"{API}/cases/{self.case_id}/commission-preview",
            params={"source_fee_id": self.fee_id},
        )).json()
        selected = preview["items"][:2]
        response = await self.client.post(f"{API}/cases/{self.case_id}/commissions", json={
            "source_fee_id": self.fee_id,
            "items": [
                {"preview_key": selected[0]["preview_key"], "actual_amount": 400, "remark": "调整后金额"},
                {"preview_key": selected[1]["preview_key"], "actual_amount": selected[1]["actual_amount"], "remark": ""},
            ],
        })
        self.assertEqual(response.status_code, 201, response.text)
        self.assertEqual(response.json()["total"], 2)
        async with self.sessions() as db:
            rows = list((await db.scalars(select(BusinessRecord).where(
                BusinessRecord.module == "finance",
                BusinessRecord.data["source_fee_id"].as_integer() == self.fee_id,
            ))).all())
            self.assertEqual(len(rows), 2)
            self.assertTrue(all((row.data or {}).get("base_amount") == 8400 for row in rows))
            before = await db.scalar(select(func.count()).select_from(BusinessRecord).where(BusinessRecord.module == "finance"))
        failed = await self.client.post(f"{API}/cases/{self.case_id}/commissions", json={
            "source_fee_id": self.fee_id,
            "items": [
                {"preview_key": selected[0]["preview_key"], "actual_amount": 420, "remark": ""},
                {"preview_key": "expired:person:rate", "actual_amount": 1, "remark": ""},
            ],
        })
        self.assertEqual(failed.status_code, 422, failed.text)
        async with self.sessions() as db:
            after = await db.scalar(select(func.count()).select_from(BusinessRecord).where(BusinessRecord.module == "finance"))
        self.assertEqual(after, before)

    async def test_non_agency_fee_is_rejected(self):
        response = await self.client.get(
            f"{API}/cases/{self.case_id}/commission-preview",
            params={"source_fee_id": self.other_fee_id},
        )
        self.assertEqual(response.status_code, 422, response.text)
        self.assertIn("必须选择一条代理费", response.text)


if __name__ == "__main__":
    unittest.main()
