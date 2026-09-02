import importlib.util
import sys
import unittest
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.main import _collect_hr_employee_deletion_blockers, delete_hr_employee, get_hr_employee_deletion_impact
from app.models import BusinessRecord, FileAttachment, HrSubrecord, User, WorkflowEvent


SCRIPT = Path(__file__).resolve().parent / "scripts" / "repair_duplicate_hr_identities.py"
SPEC = importlib.util.spec_from_file_location("repair_duplicate_hr_identities", SCRIPT)
assert SPEC and SPEC.loader
REPAIR = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = REPAIR
SPEC.loader.exec_module(REPAIR)


class HrDuplicateIdentityReworkRow9Test(unittest.IsolatedAsyncioTestCase):
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

    async def seed_conflict(self, db: AsyncSession):
        user = User(
            username="fwlll",
            display_name="范文玲",
            department="财务部",
            password_hash="test",
            role="user",
            role_ids=["user"],
            profile={"employee_no": "1"},
            is_active=True,
        )
        db.add(user)
        await db.flush()
        legacy = {
            "legacy_staff_id": 301,
            "legacy_staff_no": "415",
            "legacy_staff_name": "fwl",
            "legacy_staff_ch_name": "范文玲",
        }
        canonical = BusinessRecord(
            module="hr", serial_no="1", title="范文玲", customer="上海申浩律师事务所",
            status="在职", owner="fwlll", department="财务部",
            data={"username": "fwlll", "system_user_id": user.id, "legacy_staff_id": 301, "legacy_hr_identity": legacy},
        )
        duplicate = BusinessRecord(
            module="hr", serial_no="415", title="范文林", customer="上海申浩律师事务所",
            status="在职", owner="fwlll", department="财务部",
            data={"username": "fwlll", "system_user_id": user.id, "legacy_staff_id": 301, "legacy_hr_identity": {"legacy_staff_id": 301}},
        )
        business_case = BusinessRecord(
            module="case", serial_no="ROW9-CASE", title="关联案件", customer="", status="办理中",
            owner="fwlll", department="财务部", data={"handling_lawyer_usernames": ["fwlll"]},
        )
        db.add_all([canonical, duplicate, business_case])
        await db.flush()
        db.add_all([
            HrSubrecord(employee_id=canonical.id, kind="event", data={}, created_by="admin", updated_by="admin"),
            WorkflowEvent(record_id=canonical.id, action="导入主档案", from_status="", to_status="在职", operator="admin", comment=""),
            WorkflowEvent(record_id=canonical.id, action="维护主档案", from_status="在职", to_status="在职", operator="admin", comment=""),
            WorkflowEvent(record_id=duplicate.id, action="导入重复档案", from_status="", to_status="在职", operator="admin", comment=""),
        ])
        await db.commit()
        return user, canonical, duplicate, business_case

    async def test_redundant_file_can_be_deleted_without_deleting_shared_login(self):
        async with self.sessions() as db:
            user, canonical, duplicate, business_case = await self.seed_conflict(db)
            blockers, linked_user = await _collect_hr_employee_deletion_blockers(duplicate, {"username": "admin", "role": "admin"}, db)
            self.assertEqual(blockers, [])
            self.assertIsNone(linked_user)
            impact = await get_hr_employee_deletion_impact(duplicate.id, {"username": "admin", "role": "admin"}, db)
            self.assertTrue(impact["duplicate_cleanup"])
            self.assertEqual(impact["canonical_employee_id"], canonical.id)

            response = await delete_hr_employee(duplicate.id, {"username": "admin", "role": "admin"}, db)
            self.assertEqual(response.status_code, 204)
            self.assertIsNotNone(await db.get(BusinessRecord, canonical.id))
            self.assertIsNotNone(await db.get(BusinessRecord, business_case.id))
            self.assertIsNotNone(await db.get(User, user.id))
            self.assertIsNone(await db.get(BusinessRecord, duplicate.id))

    async def test_canonical_file_is_protected_until_duplicate_is_removed(self):
        async with self.sessions() as db:
            _, canonical, duplicate, _ = await self.seed_conflict(db)
            blockers, linked_user = await _collect_hr_employee_deletion_blockers(canonical, {"username": "admin", "role": "admin"}, db)
            self.assertIsNotNone(linked_user)
            duplicate_blocker = next(item for item in blockers if item["kind"] == "重复身份主档案")
            self.assertEqual(duplicate_blocker["records"], [duplicate.serial_no])
            self.assertTrue(any(item["kind"] == "可能业务关联" for item in blockers))

    async def test_repair_merges_children_preserves_login_and_restores_legacy_number(self):
        async with self.sessions() as db:
            user, canonical, duplicate, business_case = await self.seed_conflict(db)
            attachment = FileAttachment(
                record_id=duplicate.id,
                original_name="重复档案附件.txt",
                stored_name="row9-duplicate-file.txt",
                path="row9-duplicate-file.txt",
                uploader="admin",
            )
            db.add(attachment)
            await db.commit()

            result = await REPAIR.repair_session(db, apply=True)
            self.assertEqual(result["groups_repaired"], 1)
            self.assertEqual(result["duplicates_deleted"], 1)
            repaired = await db.get(BusinessRecord, canonical.id)
            self.assertEqual(repaired.serial_no, "415")
            self.assertEqual(repaired.title, "范文玲")
            self.assertEqual((repaired.data or {})["username"], "fwlll")
            self.assertEqual((repaired.data or {})["legacy_staff_id"], 301)
            self.assertIsNone(await db.get(BusinessRecord, duplicate.id))
            self.assertIsNotNone(await db.get(User, user.id))
            self.assertIsNotNone(await db.get(BusinessRecord, business_case.id))
            self.assertEqual(await db.scalar(select(func.count()).select_from(FileAttachment).where(FileAttachment.record_id == canonical.id)), 1)
            self.assertEqual(await db.scalar(select(func.count()).select_from(WorkflowEvent).where(WorkflowEvent.record_id == canonical.id)), 4)

            second = await REPAIR.repair_session(db, apply=True)
            self.assertEqual(second["duplicate_groups"], 0)
            self.assertEqual(second["duplicates_deleted"], 0)

    async def test_repair_dry_run_is_non_mutating(self):
        async with self.sessions() as db:
            user, canonical, duplicate, _ = await self.seed_conflict(db)
            user_id = user.id
            canonical_id = canonical.id
            duplicate_id = duplicate.id
            result = await REPAIR.repair_session(db, apply=False)
            self.assertEqual(result["mode"], "audit")
            self.assertEqual(result["duplicate_groups"], 1)
            self.assertIsNotNone(await db.get(BusinessRecord, canonical_id))
            self.assertIsNotNone(await db.get(BusinessRecord, duplicate_id))
            self.assertIsNotNone(await db.get(User, user_id))

    async def test_targeted_repair_requires_the_expected_identity_tokens(self):
        async with self.sessions() as db:
            _, canonical, duplicate, _ = await self.seed_conflict(db)
            canonical_id = canonical.id
            duplicate_id = duplicate.id

            with self.assertRaisesRegex(RuntimeError, "identity tokens changed"):
                await REPAIR.repair_session(
                    db,
                    apply=True,
                    canonical_ids={canonical_id},
                    expected_tokens={"legacy_staff_id:999"},
                )

            self.assertIsNotNone(await db.get(BusinessRecord, canonical_id))
            self.assertIsNotNone(await db.get(BusinessRecord, duplicate_id))

    async def test_targeted_repair_applies_only_to_the_selected_identity_group(self):
        async with self.sessions() as db:
            _, canonical, duplicate, _ = await self.seed_conflict(db)
            other_user = User(
                username="row9_other",
                display_name="Row 9 Other",
                department="Test",
                password_hash="test",
                role="user",
                role_ids=["user"],
                profile={},
                is_active=True,
            )
            db.add(other_user)
            await db.flush()
            other_main = BusinessRecord(
                module="hr", serial_no="ROW9-OTHER-MAIN", title="Row 9 Other",
                customer="Test", status="Active", owner="row9_other", department="Test",
                data={"username": "row9_other", "system_user_id": other_user.id, "legacy_staff_id": 999},
            )
            other_duplicate = BusinessRecord(
                module="hr", serial_no="ROW9-OTHER-DUP", title="Row 9 Other Duplicate",
                customer="Test", status="Active", owner="row9_other", department="Test",
                data={"username": "row9_other", "system_user_id": other_user.id, "legacy_staff_id": 999},
            )
            db.add_all([other_main, other_duplicate])
            await db.commit()

            result = await REPAIR.repair_session(
                db,
                apply=True,
                canonical_ids={canonical.id},
                expected_tokens={"username:fwlll", "legacy_staff_id:301"},
            )

            self.assertEqual(result["duplicate_groups"], 2)
            self.assertEqual(result["selected_groups"], 1)
            self.assertEqual(result["duplicates_deleted"], 1)
            self.assertIsNone(await db.get(BusinessRecord, duplicate.id))
            self.assertIsNotNone(await db.get(BusinessRecord, other_main.id))
            self.assertIsNotNone(await db.get(BusinessRecord, other_duplicate.id))


if __name__ == "__main__":
    unittest.main()
