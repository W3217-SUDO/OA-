"""Route-level contract for criminal-case status normalization and role permissions."""
import asyncio
import pathlib
import sqlite3
import unittest
import uuid

from fastapi import HTTPException
from sqlalchemy import delete, select

from app.database import Base, SessionLocal, engine
from app.main import (
    CONTRACT_APPROVED_STATUS,
    CaseCreateInput,
    CaseLitigantsInput,
    create_case,
    list_case_eligible_contracts,
    update_case_litigants,
)
from app.models import (
    BusinessRecord,
    ContractApprovalStep,
    Department,
    FileAttachment,
    LegacyCase,
    LegacyCaseFile,
    LegacyCaseLog,
    LegacyCaseParticipant,
    LegacyCustomer,
    LegacyCustomerContact,
    RolePermission,
    SystemParameter,
    User,
    WorkflowEvent,
)
from app.security import hash_password

DB = pathlib.Path(__file__).with_name("legal_platform.db")
NEW_STATUS = "\u65b0\u6848\u5f85\u5206\u914d"
STATUS_ALIAS = "\u5f85\u5206\u914d"
INVALID_STATUS = "\u5df2\u5f52\u6863"
CRIMINAL = "\u5211\u4e8b\u6848\u4ef6"
CLIENT_POSITION = "\u88ab\u544a\u4eba/\u72af\u7f6a\u5acc\u7591\u4eba"
APPROVED = CONTRACT_APPROVED_STATUS
CIVIL = "\u6c11\u4e8b\u6848\u4ef6"
CIVIL_CLIENT_POSITION = "\u539f\u544a/\u7533\u8bf7\u4eba"


class CaseCreateRouteContractTest(unittest.TestCase):
    def test_status_alias_invalid_status_and_role_permission_guard(self):
        asyncio.run(self._run())

    async def _run(self):
        prefix = f"CODEX-CASE-C-NEXT-ROUTE-{uuid.uuid4().hex[:8]}"
        department_code = f"{prefix}-department"
        department_name = f"{prefix}-department"
        # This route contract owns only these records. Do not rely on a
        # pre-existing local SQLite schema, which may predate the complete
        # legacy model set merged in 1.0.161.
        tables = [
            User.__table__,
            Department.__table__,
            RolePermission.__table__,
            BusinessRecord.__table__,
            ContractApprovalStep.__table__,
            WorkflowEvent.__table__,
            FileAttachment.__table__,
            LegacyCase.__table__,
            LegacyCaseFile.__table__,
            LegacyCaseLog.__table__,
            LegacyCaseParticipant.__table__,
            LegacyCustomer.__table__,
            LegacyCustomerContact.__table__,
            SystemParameter.__table__,
        ]
        async with engine.begin() as connection:
            await connection.run_sync(
                lambda sync_connection: Base.metadata.create_all(sync_connection, tables=tables)
            )
        lawyer_username = f"codex-case-c-next-route-{uuid.uuid4().hex[:8]}-lawyer"
        denied_username = f"codex-case-c-next-route-{uuid.uuid4().hex[:8]}-denied"
        denied_role = f"codex_case_{uuid.uuid4().hex[:12]}"
        case_ids: list[int] = []
        contract_id: int | None = None
        customer_id: int | None = None
        created_admin = False
        created_party_parameter = False
        previous_party_parameter_active: bool | None = None
        async with SessionLocal() as db:
            db.add(Department(code=department_code, name=department_name, is_active=True))
            if not await db.scalar(select(User.id).where(User.username == "admin")):
                db.add(User(
                    username="admin", display_name="Codex Test Admin", department="\u4e0a\u6d77\u5206\u6240",
                    role="admin", profile={}, password_hash=hash_password("Codex-Route-Admin-123!"),
                    is_active=True, must_change_password=False,
                ))
                created_admin = True
            party_parameter = await db.scalar(select(SystemParameter).where(
                SystemParameter.category == "customer_type",
                SystemParameter.name == "当事人",
            ))
            if party_parameter is None:
                party_parameter = SystemParameter(
                    category="customer_type", code=f"{prefix}-PARTY", name="当事人",
                    sort_order=2, is_active=True,
                )
                db.add(party_parameter)
                created_party_parameter = True
            else:
                previous_party_parameter_active = party_parameter.is_active
                party_parameter.is_active = True
            lawyer = User(
                username=lawyer_username, display_name="\u7f16\u7801\u6d4b\u8bd5\u5f8b\u5e08",
                department=department_name, role="user", profile={"position": "\u5f8b\u5e08"},
                password_hash=hash_password("Codex-Route-Lawyer-123!"), is_active=True,
                must_change_password=False,
            )
            denied_user = User(
                username=denied_username, display_name=denied_username,
                department=department_name, role=denied_role, profile={},
                password_hash=hash_password("Codex-Route-Denied-123!"), is_active=True,
                must_change_password=False,
            )
            denied_permission = RolePermission(
                role=denied_role, display_name="Codex denied role", data_scope="\u672c\u4eba\u53ca\u5171\u4eab\u6570\u636e",
                menu_keys=["case-mine"], field_keys=[],
            )
            db.add_all([lawyer, denied_user, denied_permission])
            await db.flush()
            customer = BusinessRecord(
                module="customer", serial_no=f"{prefix}-CUSTOMER", title=f"{prefix} customer",
                customer="", status="我的客户", owner=lawyer_username,
                department=department_name, description="", data={"customer_managers": [lawyer_username]},
            )
            db.add(customer)
            await db.flush()
            customer_id = customer.id
            contract = BusinessRecord(
                module="contract", serial_no=f"{prefix}-CONTRACT", title=f"{prefix} contract",
                customer=f"{prefix} customer", status=APPROVED, owner=lawyer_username,
                department=department_name, description="", data={
                    "type": "general", "amount": "1.00", "source_person": lawyer_username, "shared_with": [],
                    "customer_id": customer.id, "customer_no": customer.serial_no,
                },
            )
            db.add(contract)
            await db.flush()
            contract_id = contract.id
            eligible = await list_case_eligible_contracts({"username": "admin", "role": "admin"}, db)
            listed_contract = next(item for item in eligible["items"] if item["id"] == contract_id)
            self.assertEqual(listed_contract["owner_display_name"], lawyer.display_name)
            self.assertEqual(listed_contract["data"]["source_person_display_name"], lawyer.display_name)
            base = {
                "contract_record_id": contract_id, "title": f"{prefix} criminal case",
                "customer_record_id": customer_id, "customer_no": customer.serial_no, "customer": customer.title,
                "owner": "admin", "case_type": CRIMINAL, "client_position": CLIENT_POSITION,
                "cause_or_charge": f"{prefix} cause", "handling_lawyers": [lawyer_username],
                "source_person": "admin",
            }
            try:
                created = await create_case(CaseCreateInput(**base, serial_no=f"{prefix}-VALID", status=NEW_STATUS), {"username": "admin", "role": "admin"}, db)
                case_ids.append(created["id"])
                self.assertEqual(created["status"], NEW_STATUS)
                alias = await create_case(CaseCreateInput(**base, serial_no=f"{prefix}-ALIAS", status=STATUS_ALIAS), {"username": "admin", "role": "admin"}, db)
                case_ids.append(alias["id"])
                self.assertEqual(alias["status"], NEW_STATUS)
                with self.assertRaises(HTTPException) as invalid:
                    await create_case(CaseCreateInput(**base, serial_no=f"{prefix}-INVALID", status=INVALID_STATUS), {"username": "admin", "role": "admin"}, db)
                self.assertEqual(invalid.exception.status_code, 422)
                with self.assertRaises(HTTPException) as wrong_customer:
                    await create_case(
                        CaseCreateInput(**{**base, "customer_record_id": customer_id + 9999}, serial_no=f"{prefix}-WRONG-CUSTOMER", status=NEW_STATUS),
                        {"username": "admin", "role": "admin"},
                        db,
                    )
                self.assertEqual(wrong_customer.exception.status_code, 422)
                with self.assertRaises(HTTPException) as forbidden:
                    await create_case(CaseCreateInput(**base, serial_no=f"{prefix}-FORBIDDEN", status=NEW_STATUS), {"username": denied_username, "role": denied_role}, db)
                self.assertIn(forbidden.exception.status_code, {403, 404})

                legacy_case_no = f"CX{uuid.uuid4().hex[:18]}"
                civil = await create_case(CaseCreateInput(
                    **{**base, "title": f"{prefix} civil case", "case_type": CIVIL, "client_position": CIVIL_CLIENT_POSITION},
                    serial_no=legacy_case_no,
                    status=NEW_STATUS,
                ), {"username": "admin", "role": "admin"}, db)
                case_ids.append(civil["id"])
                litigants = await update_case_litigants(
                    civil["id"],
                    CaseLitigantsInput(plaintiffs=[f"{prefix} plaintiff"], defendants=[f"{prefix} defendant"]),
                    {"username": "admin", "role": "admin"},
                    db,
                )
                self.assertEqual(litigants["data"]["defendants"], [f"{prefix} defendant"])
                self.assertEqual(litigants["data"]["opponent"], f"{prefix} defendant")
                legacy_case = await db.scalar(select(LegacyCase).where(LegacyCase.CaseNo == legacy_case_no))
                self.assertIsNotNone(legacy_case)
                self.assertEqual(legacy_case.CaseId, -civil["id"])
                self.assertEqual(legacy_case.AppelleeNames, f"{prefix} defendant")
                rows = (await db.scalars(select(BusinessRecord).where(BusinessRecord.module == "case", BusinessRecord.serial_no.like(prefix + "%")))).all()
                self.assertEqual({row.id for row in rows}, set(case_ids[:-1]))
            finally:
                party_rows = list((await db.scalars(select(BusinessRecord).where(
                    BusinessRecord.module == "customer",
                    BusinessRecord.title.like(prefix + "%"),
                    BusinessRecord.id != customer_id,
                ))).all())
                party_ids = [row.id for row in party_rows]
                party_numbers = [row.serial_no for row in party_rows]
                if party_ids:
                    await db.execute(delete(WorkflowEvent).where(WorkflowEvent.record_id.in_(party_ids)))
                    await db.execute(delete(BusinessRecord).where(BusinessRecord.id.in_(party_ids)))
                if party_numbers:
                    await db.execute(delete(LegacyCustomerContact).where(LegacyCustomerContact.CustomerNo.in_(party_numbers)))
                    await db.execute(delete(LegacyCustomer).where(LegacyCustomer.CustomerNo.in_(party_numbers)))
                if "legacy_case_no" in locals():
                    await db.execute(delete(LegacyCaseParticipant).where(LegacyCaseParticipant.CaseNo == legacy_case_no))
                    await db.execute(delete(LegacyCaseLog).where(LegacyCaseLog.CaseNo == legacy_case_no))
                    await db.execute(delete(LegacyCase).where(LegacyCase.CaseNo == legacy_case_no))
                await db.execute(delete(WorkflowEvent).where(WorkflowEvent.record_id.in_(case_ids)))
                await db.execute(delete(BusinessRecord).where(BusinessRecord.id.in_(case_ids)))
                if contract_id:
                    await db.execute(delete(WorkflowEvent).where(WorkflowEvent.record_id == contract_id))
                    await db.execute(delete(BusinessRecord).where(BusinessRecord.id == contract_id))
                if customer_id:
                    await db.execute(delete(BusinessRecord).where(BusinessRecord.id == customer_id))
                await db.execute(delete(RolePermission).where(RolePermission.role == denied_role))
                await db.execute(delete(User).where(User.username.in_([lawyer_username, denied_username])))
                if created_admin:
                    await db.execute(delete(User).where(User.username == "admin"))
                if created_party_parameter:
                    await db.delete(party_parameter)
                elif previous_party_parameter_active is not None:
                    party_parameter.is_active = previous_party_parameter_active
                await db.execute(delete(Department).where(Department.code == department_code))
                await db.commit()
        conn = sqlite3.connect(DB)
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM business_records WHERE serial_no LIKE ?", (prefix + "%",)).fetchone()[0], 0)
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM business_records WHERE title LIKE ?", (prefix + "%",)).fetchone()[0], 0)
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM workflow_events WHERE comment LIKE ?", (prefix + "%",)).fetchone()[0], 0)
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM users WHERE username IN (?, ?)", (lawyer_username, denied_username)).fetchone()[0], 0)
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM role_permissions WHERE role = ?", (denied_role,)).fetchone()[0], 0)
        conn.close()


if __name__ == "__main__":
    unittest.main()
