"""变更案源人方案 A（陶国南 2026-11-01）。

1. 客户来源就是案源人；变更案源人只改客户来源，不改客户管理人。
2. 原有合同、调查任务、线索、案件里记录的案源人都不改（涉及原案源人提成）。
3. 以后新建的合同、案件默认用新案源人。
4. 案源人默认就有客户管理人的权限，换成新人后新人能看到、能管理这个客户。
"""
import unittest
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models import BusinessRecord, RolePermission, SystemParameter, User

OLD_TIME = datetime(2026, 1, 1, tzinfo=timezone.utc)
ADMIN = {"username": "codexadmin", "display_name": "", "role": "admin", "role_ids": ["admin"], "_actual_role": "admin",
         "_actual_role_ids": ["admin"], "_request_method": "POST", "action_keys": ["*"]}


class CustomerSourcePersonChangeTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.sessions() as db:
            for username, department, role in (("codexadmin", "CODEX-A", "admin"), ("codexold", "CODEX-A", "user"),
                                               ("codexmgr", "CODEX-A", "user"), ("codexnew", "CODEX-B", "manager")):
                db.add(User(username=username, display_name=username, password_hash="isolated-only", department=department,
                            role=role, is_active=True))
            db.add(RolePermission(role="manager", display_name="CODEX-manager", data_scope="本部门数据",
                                  menu_keys=["customer-dept"], field_keys=["*"]))
            db.add(SystemParameter(category="customer_type", code="client", name="客户", is_active=True))
            db.add(BusinessRecord(id=1, module="customer", serial_no="KH1", title="客户甲", status="T", owner="codexold",
                                  department="CODEX-A", data={"customer_source": "codexold", "source_person": "codexold",
                                                              "customer_managers": ["codexmgr"]}))
            db.add(BusinessRecord(id=11, module="contract", serial_no="HT1", title="原合同", status="已审批", owner="codexold",
                                  department="CODEX-A", customer="客户甲", created_at=OLD_TIME,
                                  data={"customer_record_id": 1, "source_person": "codexold"}))
            db.add(BusinessRecord(id=21, module="case", serial_no="AJ1", title="原案件", status="文书准备", owner="codexmgr",
                                  department="CODEX-A", customer="客户甲",
                                  data={"customer_record_id": 1, "contract_record_id": 11, "source_person": "codexold",
                                        "business_owner": "codexold"}))
            db.add(BusinessRecord(id=31, module="investigation", serial_no="DC1", title="原调查", status="待接收", owner="codexmgr",
                                  department="CODEX-A", customer="客户甲",
                                  data={"customer_record_id": 1, "contract_record_id": 11, "source_owner": "codexold"}))
            await db.commit()

    async def asyncTearDown(self):
        await self.engine.dispose()

    async def change_to_new(self):
        from app.areas.crm.router import change_customer_source_person
        from app.models_shared import CustomerSourcePersonInput
        async with self.sessions() as db:
            await change_customer_source_person(1, CustomerSourcePersonInput(source_person="codexnew"), ADMIN, db)

    async def test_change_only_customer_source_and_keeps_history_records(self):
        await self.change_to_new()
        async with self.sessions() as db:
            customer = await db.get(BusinessRecord, 1)
            self.assertEqual((customer.owner, customer.data["customer_source"], customer.data["source_person"]),
                             ("codexnew", "codexnew", "codexnew"))
            self.assertEqual(customer.data["customer_managers"], ["codexmgr"])
            contract = await db.get(BusinessRecord, 11)
            self.assertEqual((contract.owner, contract.data["source_person"]), ("codexold", "codexold"))
            case = await db.get(BusinessRecord, 21)
            self.assertEqual((case.data["source_person"], case.data["business_owner"]), ("codexold", "codexold"))
            self.assertEqual((await db.get(BusinessRecord, 31)).data["source_owner"], "codexold")

    async def test_new_contract_and_case_default_to_new_source(self):
        from app.core.contracts import _case_default_source_person, _contract_customer_source_person
        await self.change_to_new()
        async with self.sessions() as db:
            customer = await db.get(BusinessRecord, 1)
            # 新合同从客户带案源人。
            self.assertEqual(_contract_customer_source_person(customer), "codexnew")
            # 原合同下新建的案件：客户在合同之后变更过案源人，按新案源人。
            self.assertEqual(_case_default_source_person(await db.get(BusinessRecord, 11), customer), "codexnew")
            # 变更之后才签的合同，本来就是新案源人；合同上另行写了别人时以合同为准。
            later = BusinessRecord(module="contract", serial_no="HT2", title="新合同", status="已审批", owner="codexmgr",
                                   department="CODEX-A", data={"customer_record_id": 1, "source_person": "codexmgr"},
                                   created_at=datetime.now(timezone.utc) + timedelta(minutes=1))
            self.assertEqual(_case_default_source_person(later, customer), "codexmgr")
            # 从没变更过案源人的客户，照旧按合同。
            unchanged = BusinessRecord(module="customer", serial_no="KH9", title="客户乙", status="T", owner="codexold",
                                       department="CODEX-A", data={"customer_source": "codexold"})
            self.assertEqual(_case_default_source_person(await db.get(BusinessRecord, 11), unchanged), "codexold")

    async def test_eligible_contracts_carry_default_case_source(self):
        from app.areas.legal.router import list_case_eligible_contracts
        await self.change_to_new()
        async with self.sessions() as db:
            result = await list_case_eligible_contracts({**ADMIN, "_request_method": "GET"}, db)
        row = next(item for item in result["items"] if item["id"] == 11)
        self.assertEqual((row["case_source_person"], row["case_source_person_display_name"]), ("codexnew", "codexnew"))
        self.assertEqual(row["data"]["source_person"], "codexold")

    async def test_new_source_person_sees_and_manages_customer_outside_department(self):
        from app.core.permissions import _record_scope_conditions, _require_record_owner_or_manager
        reader = {"username": "codexnew", "display_name": "", "role": "manager", "role_ids": ["manager"],
                  "_actual_role": "manager", "_actual_role_ids": ["manager"], "_request_method": "GET"}

        async def visible() -> set[int]:
            async with self.sessions() as db:
                return set((await db.scalars(select(BusinessRecord.id).where(
                    BusinessRecord.module == "customer", *(await _record_scope_conditions(reader, db)),
                ))).all())

        self.assertNotIn(1, await visible())
        await self.change_to_new()
        self.assertIn(1, await visible())
        async with self.sessions() as db:
            await _require_record_owner_or_manager(await db.get(BusinessRecord, 1), {**reader, "_request_method": "POST"}, db)


if __name__ == "__main__":
    unittest.main()
