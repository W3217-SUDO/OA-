"""Route-level contract for criminal-case status normalization and role permissions."""
import asyncio
import pathlib
import sqlite3
import unittest
import uuid

from fastapi import HTTPException
from sqlalchemy import delete, select

from app.database import SessionLocal
from app.main import CaseCreateInput, create_case, list_case_eligible_contracts
from app.models import BusinessRecord, RolePermission, User, WorkflowEvent
from app.security import hash_password

DB = pathlib.Path(__file__).with_name("legal_platform.db")
NEW_STATUS = "\u65b0\u6848\u5f85\u5206\u914d"
STATUS_ALIAS = "\u5f85\u5206\u914d"
INVALID_STATUS = "\u5df2\u5f52\u6863"
CRIMINAL = "\u5211\u4e8b\u6848\u4ef6"
CLIENT_POSITION = "\u88ab\u544a\u4eba/\u72af\u7f6a\u5acc\u7591\u4eba"
APPROVED = "\u5df2\u901a\u8fc7"


class CaseCreateRouteContractTest(unittest.TestCase):
    def test_status_alias_invalid_status_and_role_permission_guard(self):
        asyncio.run(self._run())

    async def _run(self):
        prefix = f"CODEX-CASE-C-NEXT-ROUTE-{uuid.uuid4().hex[:8]}"
        lawyer_username = f"codex-case-c-next-route-{uuid.uuid4().hex[:8]}-lawyer"
        denied_username = f"codex-case-c-next-route-{uuid.uuid4().hex[:8]}-denied"
        denied_role = f"codex_case_{uuid.uuid4().hex[:12]}"
        case_ids: list[int] = []
        contract_id: int | None = None
        async with SessionLocal() as db:
            lawyer = User(
                username=lawyer_username, display_name="\u7f16\u7801\u6d4b\u8bd5\u5f8b\u5e08",
                department="\u4e0a\u6d77\u5206\u6240", role="user", profile={"position": "\u5f8b\u5e08"},
                password_hash=hash_password("Codex-Route-Lawyer-123!"), is_active=True,
                must_change_password=False,
            )
            denied_user = User(
                username=denied_username, display_name=denied_username,
                department="\u4e0a\u6d77\u5206\u6240", role=denied_role, profile={},
                password_hash=hash_password("Codex-Route-Denied-123!"), is_active=True,
                must_change_password=False,
            )
            denied_permission = RolePermission(
                role=denied_role, display_name="Codex denied role", data_scope="\u672c\u4eba\u53ca\u5171\u4eab\u6570\u636e",
                menu_keys=["case-mine"], field_keys=[],
            )
            db.add_all([lawyer, denied_user, denied_permission])
            await db.flush()
            contract = BusinessRecord(
                module="contract", serial_no=f"{prefix}-CONTRACT", title=f"{prefix} contract",
                customer=f"{prefix} customer", status=APPROVED, owner=lawyer_username,
                department="\u4e0a\u6d77\u5206\u6240", description="", data={"type": "general", "amount": "1.00", "source_person": lawyer_username, "shared_with": []},
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
                with self.assertRaises(HTTPException) as forbidden:
                    await create_case(CaseCreateInput(**base, serial_no=f"{prefix}-FORBIDDEN", status=NEW_STATUS), {"username": denied_username, "role": denied_role}, db)
                self.assertEqual(forbidden.exception.status_code, 403)
                rows = (await db.scalars(select(BusinessRecord).where(BusinessRecord.module == "case", BusinessRecord.serial_no.like(prefix + "%")))).all()
                self.assertEqual({row.id for row in rows}, set(case_ids))
            finally:
                await db.execute(delete(WorkflowEvent).where(WorkflowEvent.record_id.in_(case_ids)))
                await db.execute(delete(BusinessRecord).where(BusinessRecord.id.in_(case_ids)))
                if contract_id:
                    await db.execute(delete(WorkflowEvent).where(WorkflowEvent.record_id == contract_id))
                    await db.execute(delete(BusinessRecord).where(BusinessRecord.id == contract_id))
                await db.execute(delete(RolePermission).where(RolePermission.role == denied_role))
                await db.execute(delete(User).where(User.username.in_([lawyer_username, denied_username])))
                await db.commit()
        conn = sqlite3.connect(DB)
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM business_records WHERE serial_no LIKE ?", (prefix + "%",)).fetchone()[0], 0)
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM workflow_events WHERE comment LIKE ?", (prefix + "%",)).fetchone()[0], 0)
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM users WHERE username IN (?, ?)", (lawyer_username, denied_username)).fetchone()[0], 0)
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM role_permissions WHERE role = ?", (denied_role,)).fetchone()[0], 0)
        conn.close()


if __name__ == "__main__":
    unittest.main()
