"""Role action nodes remain independently configurable under their menus."""

import unittest
from types import SimpleNamespace

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.constants import CASE_ACTIONS_EXPLICIT_MARKER
from app.core.permissions import (
    _effective_job_role_action_keys,
    _explicit_case_role_permissions,
    _job_role_tree_checked_permissions,
    _organization_permission_tree,
    _user_permission_payload,
)
from app.database import Base
from app.models import JobRole, RolePermission, User
from app.security import hash_password


class RoleActionTreeTest(unittest.TestCase):
    def test_case_actions_are_nested_under_their_menu(self):
        menus = [
            SimpleNamespace(id=1, key="case", parent_key="", label="案件中心"),
            SimpleNamespace(id=2, key="case-mine", parent_key="case", label="我的案件"),
            SimpleNamespace(id=3, key="contract", parent_key="", label="合同中心"),
            SimpleNamespace(id=4, key="contract-audit", parent_key="contract", label="合同审批"),
        ]
        tree = _organization_permission_tree(menus, ["案件承办", "合同审批"], {"action:case.fee.create"})
        case_actions = tree[0]["children"][0]["children"]
        fee_action = next(node for node in case_actions if node["key"] == "action:case.fee.create")
        self.assertEqual(fee_action["title"], "新增案件费用")
        self.assertTrue(fee_action["state"]["checked"])
        self.assertIn("action:case.progress.update", {node["key"] for node in case_actions})
        self.assertNotIn("actions", {node["key"] for node in tree})
        self.assertIn("合同审批", {node["key"] for node in tree[1]["children"][0]["children"]})

    def test_legacy_case_grants_are_preserved_then_independently_revocable(self):
        role = JobRole(code="LAWYER", name="Lawyer", permissions=["案件承办", "合同审批"])
        checked = _job_role_tree_checked_permissions(role)
        self.assertIn("case-mine", checked)
        self.assertIn("action:case.progress.update", checked)
        self.assertIn("action:case.task.create", checked)
        self.assertNotIn("案件承办", checked)

        role.permissions = _explicit_case_role_permissions([
            *[key for key in checked if key != "action:case.progress.update"],
            "action:case.fee.create",
        ])
        self.assertIn(CASE_ACTIONS_EXPLICIT_MARKER, role.permissions)
        self.assertNotIn("case.progress.update", _effective_job_role_action_keys(role))
        self.assertIn("case.detail.update", _effective_job_role_action_keys(role))
        self.assertIn("case.fee.create", _effective_job_role_action_keys(role))
        self.assertIn("case-mine", _job_role_tree_checked_permissions(role))


class RoleActionPersistenceTest(unittest.IsolatedAsyncioTestCase):
    async def test_employee_uses_saved_case_action_selection(self):
        engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            connect_args={"check_same_thread": False}, poolclass=StaticPool,
        )
        sessions = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
        try:
            async with engine.begin() as connection:
                await connection.run_sync(lambda sync: Base.metadata.create_all(sync, tables=[
                    User.__table__, RolePermission.__table__, JobRole.__table__,
                ]))
            async with sessions() as db:
                db.add(User(
                    username="lawyer", display_name="Lawyer", department="D", role="user",
                    password_hash=hash_password("LocalOnlyPass2026!"),
                    profile={"permission_role_code": "LAWYER"},
                ))
                db.add(JobRole(code="LAWYER", name="Lawyer", permissions=["案件承办"]))
                await db.commit()

                user = await db.scalar(select(User).where(User.username == "lawyer"))
                role = await db.scalar(select(JobRole).where(JobRole.code == "LAWYER"))
                before = await _user_permission_payload(user, db)
                self.assertIn("case.progress.update", before["action_keys"])

                checked = _job_role_tree_checked_permissions(role)
                role.permissions = _explicit_case_role_permissions([
                    key for key in checked if key != "action:case.progress.update"
                ])
                await db.commit()
                await db.refresh(role)
                after = await _user_permission_payload(user, db)
                self.assertNotIn("case.progress.update", after["action_keys"])
                self.assertIn("case.detail.update", after["action_keys"])
                self.assertIn("case-mine", after["menu_keys"])
        finally:
            await engine.dispose()


if __name__ == "__main__":
    unittest.main()
