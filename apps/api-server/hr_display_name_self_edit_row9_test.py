from pathlib import Path
from types import SimpleNamespace
import unittest

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.main import _hr_record_linked_username, _require_unique_hr_display_name
from app.models import BusinessRecord


SOURCE = Path(__file__).with_name("app") / "main.py"


class HrDisplayNameSelfEditRow9Test(unittest.TestCase):
    def test_uniqueness_excludes_current_employee_and_linked_user(self):
        source = SOURCE.read_text(encoding="utf-8")
        start = source.index("async def _require_unique_hr_display_name")
        end = source.index('@app.get(f"{settings.api_prefix}/hr/employees")', start)
        branch = source[start:end]
        self.assertIn("BusinessRecord.id != employee_id", branch)
        self.assertIn("User.username != linked_username.strip().lower()", branch)
        self.assertIn("_hr_record_linked_username(employee) != normalized_linked_username", branch)

    def test_only_exact_normalized_names_conflict_and_other_people_still_block(self):
        source = SOURCE.read_text(encoding="utf-8")
        start = source.index("async def _require_unique_hr_display_name")
        end = source.index('@app.get(f"{settings.api_prefix}/hr/employees")', start)
        branch = source[start:end]
        self.assertIn("func.lower(func.trim(BusinessRecord.title)) == name_key", branch)
        self.assertIn("func.lower(func.trim(User.display_name)) == name_key", branch)
        self.assertNotIn("ilike", branch)
        self.assertEqual(branch.count('detail="中文姓名已存在"'), 2)

    def test_duplicate_migrated_hr_files_resolve_to_the_same_login_identity(self):
        primary = SimpleNamespace(data={"username": "fwl"}, owner="legacy-owner")
        duplicate = SimpleNamespace(data={}, owner="FWL")
        other_person = SimpleNamespace(data={"username": "fwll"}, owner="fwl")
        self.assertEqual(_hr_record_linked_username(primary), "fwl")
        self.assertEqual(_hr_record_linked_username(duplicate), "fwl")
        self.assertEqual(_hr_record_linked_username(other_person), "fwll")


    def test_account_only_employee_update_uses_the_same_uniqueness_gate(self):
        source = SOURCE.read_text(encoding="utf-8")
        start = source.index("async def update_system_user(")
        end = source.index('@app.get(f"{settings.api_prefix}/system/users/{{user_id}}/permissions")', start)
        branch = source[start:end]
        self.assertIn("await _require_unique_hr_display_name(", branch)
        self.assertIn("linked_username=user.username", branch)


class HrDisplayNameMigratedIdentityTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

    async def asyncTearDown(self):
        await self.engine.dispose()

    async def test_same_login_identity_does_not_conflict_across_migrated_hr_files(self):
        async with self.sessions() as db:
            db.add_all([
                BusinessRecord(module="hr", serial_no="HR-1", title="范文林", customer="", status="在职", owner="fwl", data={"username": "fwl"}),
                BusinessRecord(module="hr", serial_no="HR-2", title="范文玲", customer="", status="在职", owner="fwl", data={"username": "fwl"}),
            ])
            await db.commit()
            duplicate = await db.scalar(select(BusinessRecord).where(BusinessRecord.serial_no == "HR-2"))
            normalized = await _require_unique_hr_display_name("范文林", db, employee_id=duplicate.id, linked_username="fwl")
        self.assertEqual(normalized, "范文林")

    async def test_other_login_identity_with_the_same_name_still_conflicts(self):
        async with self.sessions() as db:
            db.add_all([
                BusinessRecord(module="hr", serial_no="HR-1", title="范文林", customer="", status="在职", owner="fwl", data={"username": "fwl"}),
                BusinessRecord(module="hr", serial_no="HR-3", title="范文林", customer="", status="在职", owner="other", data={"username": "other"}),
            ])
            await db.commit()
            with self.assertRaises(HTTPException) as caught:
                await _require_unique_hr_display_name("范文林", db, linked_username="fwl")
        self.assertEqual(caught.exception.status_code, 409)


if __name__ == "__main__":
    unittest.main()
