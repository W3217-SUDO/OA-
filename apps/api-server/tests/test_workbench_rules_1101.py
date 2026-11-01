"""陶国南 11-01 定的工作台规则。

- 开庭排期分“个人 / 全所”：默认个人（管理员也一样），所有人都能切到全所，全所按页取。
- 管理员类账号（系统角色 admin、岗位“财务审核管理”）的工作台数字按全公司算；被驳回仍只算本人。
- 待执行含再审待执行。
"""
import unittest
from datetime import date, timedelta

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models import BusinessRecord, Department, HearingSchedule, User


def identity(username, role="staff"):
    return {"username": username, "display_name": username, "role": role, "role_ids": [role],
            "_actual_role": role, "_actual_role_ids": [role], "_request_method": "GET"}


class WorkbenchRules1101Test(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        soon = date.today() + timedelta(days=3)
        async with self.sessions() as db:
            db.add(Department(code="CODEX", name="CODEX"))
            db.add(User(username="codexlaw", display_name="律师", password_hash="isolated-only", department="CODEX", role="staff", is_active=True))
            db.add(User(username="codexadm", display_name="管理员", password_hash="isolated-only", department="CODEX", role="admin", is_active=True))
            for case_id, owner in ((1, "codexlaw"), (2, "codexother"), (3, "codexother")):
                db.add(BusinessRecord(id=case_id, module="case", serial_no=f"AJ{case_id}", title=f"案件{case_id}", status="文书准备",
                                      owner=owner, department="CODEX", customer="客户",
                                      data={"case_team_usernames": [owner], "hearing_lawyer": owner}))
                db.add(HearingSchedule(case_record_id=case_id, hearing_date=soon, hearing_time=f"0{case_id}:00", court="法院",
                                       hearing_lawyer=owner))
            await db.commit()

    async def asyncTearDown(self):
        await self.engine.dispose()

    async def test_hearings_default_personal_and_company_is_paged_for_everyone(self):
        from app.core.dashboard_cases import dashboard_hearings
        async with self.sessions() as db:
            mine, total = await dashboard_hearings(identity("codexlaw"), db)
            self.assertEqual(([row["case_no"] for row in mine], total), (["AJ1"], 1))
            # 管理员默认也只看本人相关的。
            self.assertEqual((await dashboard_hearings(identity("codexadm", "admin"), db))[1], 0)
            page, total = await dashboard_hearings(identity("codexlaw"), db, company=True, offset=0, limit=2)
            self.assertEqual(([row["case_no"] for row in page], total), (["AJ1", "AJ2"], 3))
            page, _ = await dashboard_hearings(identity("codexlaw"), db, company=True, offset=2, limit=2)
            self.assertEqual([row["case_no"] for row in page], ["AJ3"])

    async def test_admin_accounts_are_company_wide_and_urgent_follows_scope(self):
        from app.core.dashboard_scope import dashboard_company_account, dashboard_urgent_cases, load_dashboard_scope
        async with self.sessions() as db:
            self.assertTrue(await dashboard_company_account(await db.get(User, 2), db))
            self.assertFalse(await dashboard_company_account(await db.get(User, 1), db))
            admin_scope = await load_dashboard_scope(identity("codexadm", "admin"), db, include_finance=False)
            self.assertEqual({case.id for case in admin_scope.cases}, {1, 2, 3})
            urgent = await dashboard_urgent_cases(admin_scope.identity, db, admin_scope.identity["_dashboard_case_ids"],
                                                  scope_data=admin_scope)
            self.assertEqual({case.id for case in urgent}, {1, 2, 3})
            lawyer_scope = await load_dashboard_scope(identity("codexlaw"), db, include_finance=False)
            self.assertEqual({case.id for case in lawyer_scope.cases}, {1})

    def test_rejected_counts_stay_personal_and_retrial_counts_as_pending_execution(self):
        from app.core.constants import CASE_PENDING_EXECUTION_PHASES
        from app.core.dashboard_todos import REJECTED_COUNT_SCOPE
        self.assertEqual(REJECTED_COUNT_SCOPE, "personal")
        self.assertIn("再审待执行", CASE_PENDING_EXECUTION_PHASES)


if __name__ == "__main__":
    unittest.main()
