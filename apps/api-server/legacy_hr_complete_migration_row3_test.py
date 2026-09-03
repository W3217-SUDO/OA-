import unittest

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models import BusinessRecord, Department, HrSubrecord, User
from app.security import verify_password
from scripts.migrate_legacy_hr import SOURCE, migrate_payload


def payload():
    return {
        "source": SOURCE,
        "departments": [
            {"DepartmentId": 10, "DepartmentCode": "LIT-1", "DepartmentName": "诉讼一部"},
            {"DepartmentId": 12, "DepartmentCode": "LEFT", "DepartmentName": "离职人员"},
        ],
        "staff": [
            {"StaffId": 1, "StaffNo": "001", "StaffName": "active.user", "StaffChName": "在职员工", "DepartmentId": 10, "Company": "申浩", "JobTitle": "律师", "IsActived": "T", "JobStatus": "T", "OrgPassword": "OldPass001!"},
            {"StaffId": 2, "StaffNo": "002", "StaffName": "left.user", "StaffChName": "离职员工", "DepartmentId": 12, "Company": "申浩", "JobTitle": "律师", "IsActived": "F", "JobStatus": "F", "OrgPassword": "OldPass002!"},
            {"StaffId": 3, "StaffNo": "002", "StaffName": "duplicate.no", "StaffChName": "重复工号员工", "DepartmentId": 10, "Company": "申浩", "JobTitle": "律师", "IsActived": "T", "JobStatus": "T", "OrgPassword": "OldPass003!"},
        ],
        "performances": [
            {"SettingId": 91, "StaffName": "active.user", "Salary": "5000.00", "AnnualFrom": "2026-01-01T00:00:00", "AnnualEnd": "2026-12-31T00:00:00", "KtRate": ".10", "KtFixed": "100", "WsRate": ".05", "WsFixed": "50", "AyRate": ".04", "AyFixed": "40", "TcRate": ".03", "TcFixed": "30", "PgRate": ".02", "PgFixed": "20", "IsActived": "T"},
        ],
    }


class LegacyHrCompleteMigrationRow3Test(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as connection:
            await connection.run_sync(lambda sync: Base.metadata.create_all(sync, tables=[Department.__table__, User.__table__, BusinessRecord.__table__, HrSubrecord.__table__]))

    async def asyncTearDown(self):
        await self.engine.dispose()

    async def test_imports_status_password_department_and_commission_idempotently(self):
        async with self.sessions() as db:
            first = await migrate_payload(db, payload())
            await db.commit()
            second = await migrate_payload(db, payload())
            await db.commit()

            active = await db.scalar(select(User).where(User.username == "active.user"))
            left = await db.scalar(select(User).where(User.username == "left.user"))
            employee = await db.scalar(select(BusinessRecord).where(BusinessRecord.owner == "active.user"))
            scheme = await db.scalar(select(HrSubrecord).where(HrSubrecord.employee_id == employee.id))

            self.assertTrue(active.is_active)
            self.assertFalse(left.is_active)
            self.assertTrue(verify_password("OldPass001!", active.password_hash))
            self.assertTrue(verify_password("OldPass002!", left.password_hash))
            self.assertEqual(left.department, "离职人员")
            self.assertEqual(employee.department, "诉讼一部")
            self.assertEqual(scheme.data["legacy_setting_id"], 91)
            self.assertEqual(scheme.data["hearing_rate"], 0.1)
            self.assertEqual(scheme.data["source_fixed"], 40.0)
            self.assertEqual(first["performances"]["created"], 1)
            self.assertEqual(second["performances"]["created"], 0)
            duplicate = await db.scalar(select(BusinessRecord).where(BusinessRecord.owner == "duplicate.no"))
            self.assertEqual(employee.serial_no, "001")
            self.assertEqual(duplicate.serial_no, "002-LEGACY-3")
            self.assertEqual(duplicate.data["employee_no"], "002")
            self.assertEqual(await db.scalar(select(func.count()).select_from(User)), 3)
            self.assertEqual(await db.scalar(select(func.count()).select_from(HrSubrecord)), 1)

    async def test_missing_department_relation_rolls_back_as_one_transaction(self):
        broken = payload()
        broken["staff"][0]["DepartmentId"] = 999
        async with self.sessions() as db:
            with self.assertRaises(ValueError):
                await migrate_payload(db, broken)
            await db.rollback()
            self.assertEqual(await db.scalar(select(func.count()).select_from(User)), 0)
            self.assertEqual(await db.scalar(select(func.count()).select_from(Department)), 0)


if __name__ == "__main__":
    unittest.main()
