"""Direct local API contract for customer-note editing.

The test calls the route function with a real async SQLite session, so it exercises
the same validation, customer scope and audit writes as the HTTP endpoint without
requiring an administrator password in the test environment.
"""

import unittest
import uuid

from fastapi import HTTPException
from sqlalchemy import delete

from app import main
from app.database import SessionLocal
from app.models import BusinessRecord, User, WorkflowEvent


class CustomerNoteUpdateContract(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.db = SessionLocal()
        self.marker = f"CODEX-CUSTOMER-A2-NOTE-{uuid.uuid4().hex[:10]}"
        self.note_id = uuid.uuid4().hex
        self.customer = BusinessRecord(
            module="customer",
            serial_no=f"{self.marker}-SERIAL",
            title=self.marker,
            customer=self.marker,
            status="正常",
            owner="admin",
            department="测试部门",
            data={"notes": [{"id": self.note_id, "type": "跟进记录", "content": "before", "operator": "admin", "created_at": "2026-08-02T00:00:00"}]},
        )
        self.other = User(
            username=f"{self.marker.lower()}-other",
            display_name="CODEX note other",
            department="测试部门",
            password_hash="test-only-no-login",
            role="user",
            is_active=True,
        )
        self.db.add_all([self.customer, self.other])
        await self.db.commit()
        await self.db.refresh(self.customer)

    async def asyncTearDown(self):
        await self.db.execute(delete(WorkflowEvent).where(WorkflowEvent.record_id == self.customer.id))
        await self.db.delete(self.customer)
        await self.db.delete(self.other)
        await self.db.commit()
        await self.db.close()

    def update_handler(self):
        handler = getattr(main, "update_customer_note", None)
        self.assertIsNotNone(handler, "customer note update route is required")
        return handler

    async def test_update_preserves_note_identity_and_audit_fields(self):
        updated = await self.update_handler()(
            self.customer.id,
            self.note_id,
            main.CustomerNoteInput(note_type="会议纪要", content="after"),
            {"username": "admin", "role": "admin"},
            self.db,
        )
        self.assertEqual(updated["id"], self.note_id)
        self.assertEqual(updated["operator"], "admin")
        self.assertEqual(updated["created_at"], "2026-08-02T00:00:00")
        self.assertEqual(updated["type"], "会议纪要")
        self.assertEqual(updated["content"], "after")

    async def test_update_rejects_blank_content(self):
        with self.assertRaises(HTTPException) as error:
            await self.update_handler()(
                self.customer.id, self.note_id, main.CustomerNoteInput(note_type="跟进记录", content=" "),
                {"username": "admin", "role": "admin"}, self.db,
            )
        self.assertEqual(error.exception.status_code, 422)

    async def test_update_rejects_missing_note_and_public_customer_write(self):
        with self.assertRaises(HTTPException) as missing:
            await self.update_handler()(
                self.customer.id, "missing-note", main.CustomerNoteInput(note_type="跟进记录", content="after"),
                {"username": "admin", "role": "admin"}, self.db,
            )
        self.assertEqual(missing.exception.status_code, 404)
        self.customer.status = "公海"
        await self.db.commit()
        with self.assertRaises(HTTPException) as forbidden:
            await self.update_handler()(
                self.customer.id, self.note_id, main.CustomerNoteInput(note_type="跟进记录", content="after"),
                {"username": self.other.username, "role": "user"}, self.db,
            )
        self.assertEqual(forbidden.exception.status_code, 403)


if __name__ == "__main__":
    unittest.main()
