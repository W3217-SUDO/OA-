"""9.30 第5行：调查主管归属与分配权限的隔离数据库验证。"""

import os
from pathlib import Path
import unittest

from fastapi import HTTPException
from sqlalchemy import select


evidence = Path(os.environ["OA_BATCH_EVIDENCE"]).resolve()
evidence.mkdir(parents=True, exist_ok=True)
database = evidence / "supervisor-scope.db"
if database.exists():
    raise RuntimeError("隔离测试数据库必须不存在")
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{database.as_posix()}"
os.environ["SEED_DEMO_DATA"] = "false"
os.environ["DINGTALK_NOTIFICATIONS_ENABLED"] = "false"
os.environ["SECRET_KEY"] = "isolated-930-supervisor-test-key"

from app.database import Base, SessionLocal, engine
from app.models import BusinessRecord, User
from app.core.permissions import (
    _investigation_supervisor_condition,
    _require_investigation_assignment_access,
)


class SupervisorScopeTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with SessionLocal() as db:
            db.add_all([
                User(username=name, display_name=name, department="调查部", password_hash="test",
                     role="admin" if name == "admin" else "user", role_ids=[], is_active=True)
                for name in ("supervisor", "publisher", "assignee", "admin")
            ])
            db.add_all([
                BusinessRecord(
                    module="investigation", serial_no="TEST-LEGACY", title="历史父调查",
                    customer="隔离客户", status="进行中", owner="assignee", department="调查部",
                    data={"migration_source": "legacy", "legacy_investigation_id": 1,
                          "legacy_record": {"Auditor": "supervisor"}, "assigner": "publisher"},
                ),
                BusinessRecord(
                    module="investigation", serial_no="TEST-UNKNOWN", title="未知主管父调查",
                    customer="隔离客户", status="进行中", owner="assignee", department="调查部",
                    data={"assigner": "publisher"},
                ),
                BusinessRecord(
                    module="investigation", serial_no="TEST-CURRENT", title="现行父调查",
                    customer="隔离客户", status="进行中", owner="assignee", department="调查部",
                    data={"auditor": "publisher", "legacy_record": {"Auditor": "supervisor"},
                          "migration_source": "legacy", "legacy_investigation_id": 2},
                ),
            ])
            await db.commit()

    async def asyncTearDown(self):
        await engine.dispose()
        database.unlink(missing_ok=True)

    async def test_authoritative_auditor_and_unknown_supervisor(self):
        async with SessionLocal() as db:
            records = {row.serial_no: row for row in (await db.scalars(select(BusinessRecord))).all()}

            async def visible(username):
                rows = (await db.scalars(select(BusinessRecord).where(
                    BusinessRecord.module == "investigation",
                    _investigation_supervisor_condition(username),
                ))).all()
                return {row.serial_no for row in rows}

            self.assertEqual(await visible("supervisor"), {"TEST-LEGACY"})
            self.assertEqual(await visible("publisher"), {"TEST-CURRENT"})
            self.assertEqual(await visible("assignee"), set())

            async def can_assign(serial_no, username):
                identity = {"username": username, "role": "user"}
                try:
                    await _require_investigation_assignment_access(records[serial_no], identity, db)
                    return True
                except HTTPException as error:
                    self.assertEqual(error.status_code, 403)
                    return False

            self.assertTrue(await can_assign("TEST-LEGACY", "supervisor"))
            self.assertFalse(await can_assign("TEST-LEGACY", "publisher"))
            self.assertFalse(await can_assign("TEST-LEGACY", "assignee"))
            self.assertFalse(await can_assign("TEST-UNKNOWN", "publisher"))
            self.assertFalse(await can_assign("TEST-UNKNOWN", "assignee"))
            self.assertFalse(await can_assign("TEST-CURRENT", "supervisor"))
            self.assertTrue(await can_assign("TEST-CURRENT", "publisher"))
            self.assertTrue(await can_assign("TEST-UNKNOWN", "admin"))


if __name__ == "__main__":
    unittest.main()
