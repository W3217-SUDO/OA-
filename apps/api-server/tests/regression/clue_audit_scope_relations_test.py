"""线索→客户关联与线索审批可见范围：编号/案号/间接来源各种匹配情形的语义必须保持。"""
import json
import unittest

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.clue_audit_scope import _customer_relations, clue_audit_condition
from app.database import Base
from app.models import BusinessRecord, User


def record(module, serial, owner="admin", **data):
    return BusinessRecord(module=module, serial_no=serial, title=serial, customer="", status="正常", owner=owner, data=data)


class ClueAuditScopeRelationsTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool,
        )
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with self.sessions() as db:
            db.add_all([User(username=name, display_name=name, role="user", role_ids=["user"], password_hash="x") for name in ("u1", "u2", "u3", "nobody")])
            customer_a = record("customer", "CODEX-REL-CA", customer_managers=["u1"])
            customer_b = record("customer", "CODEX-REL-CB", owner="u2", customer_managers=[])
            customer_c = record("customer", "CODEX-REL-CC", customer_managers=["u3"])
            db.add_all([customer_a, customer_b, customer_c])
            await db.flush()
            contract = record("contract", "CODEX-REL-K1", customer_id=customer_c.id)
            task = record("task", "CODEX-REL-T1", customer_record_id=customer_b.id)
            db.add_all([contract, task])
            await db.flush()
            self.ids = {"A": customer_a.id, "B": customer_b.id, "C": customer_c.id}
            clues = {
                "by_id": record("clue", "CODEX-REL-L1", customer_record_id=customer_a.id),
                "by_serial": record("clue", "CODEX-REL-L2", customer_no="CODEX-REL-CB"),
                # 编号非空但客户不存在：不能退回到案号匹配
                "missing_id": record("clue", "CODEX-REL-L3", customer_id=999999, customer_no="CODEX-REL-CA"),
                # 编号为 0 视为未填：按案号匹配
                "zero_id": record("clue", "CODEX-REL-L4", customer_id=0, customer_no="CODEX-REL-CA"),
                "via_task": record("clue", "CODEX-REL-L5", source_task_id=task.id),
                "via_contract": record("clue", "CODEX-REL-L6", contract_no="CODEX-REL-K1"),
                "no_customer": record("clue", "CODEX-REL-L7"),
                "unknown_serial": record("clue", "CODEX-REL-L8", customer_no="CODEX-REL-NOPE"),
            }
            db.add_all(clues.values())
            await db.commit()
            self.clues = {key: item.id for key, item in clues.items()}

    async def asyncTearDown(self):
        await self.engine.dispose()

    async def test_customer_relations_resolve_each_matching_case(self):
        statement, record_alias, _ = _customer_relations()
        async with self.sessions() as db:
            mapping = dict((await db.execute(statement.where(record_alias.module == "clue"))).all())
        expected = {
            self.clues["by_id"]: self.ids["A"], self.clues["by_serial"]: self.ids["B"], self.clues["zero_id"]: self.ids["A"],
            self.clues["via_task"]: self.ids["B"], self.clues["via_contract"]: self.ids["C"],
        }
        self.assertEqual(mapping, expected)

    async def _visible(self, username, record_ids=None):
        async with self.sessions() as db:
            condition = await clue_audit_condition(
                {"username": username, "role": "user"}, db, include_job_permission=False, record_ids=record_ids)
            return {i for (i,) in (await db.execute(select(BusinessRecord.id).where(condition))).all()}

    async def test_non_admin_sees_only_clues_of_customers_they_manage(self):
        # u1 管理客户 A；u2 是客户 B 的负责人（无客户经理列表时按负责人）；u3 管理客户 C。
        self.assertEqual(await self._visible("u1"), {self.clues["by_id"], self.clues["zero_id"]})
        self.assertEqual(await self._visible("u2"), {self.clues["by_serial"], self.clues["via_task"]})
        self.assertEqual(await self._visible("u3"), {self.clues["via_contract"]})
        self.assertEqual(await self._visible("nobody"), set())

    async def test_record_ids_fast_path_gives_the_same_answer_as_the_overall_scope(self):
        every_clue = set(self.clues.values())
        subsets = [every_clue, {self.clues["by_id"]}, {self.clues["by_serial"], self.clues["no_customer"]},
                   {self.clues["via_task"], 999999, self.ids["A"]}, set()]
        for username in ("u1", "u2", "u3", "nobody", "ghost"):
            overall = await self._visible(username)
            for subset in subsets:
                with self.subTest(user=username, subset=sorted(subset)):
                    self.assertEqual(await self._visible(username, record_ids=subset), overall & subset)

    async def test_unknown_or_inactive_user_sees_nothing(self):
        self.assertEqual(await self._visible("ghost"), set())

    async def test_manager_username_must_match_whole_name_not_a_substring(self):
        async with self.sessions() as db:
            db.add(User(username="u", display_name="u", role="user", role_ids=["user"], password_hash="x"))
            await db.commit()
        # "u" 是 "u1"/"u2"/"u3" 的前缀，JSON 里带引号匹配，不能因为子串而看到别人的线索
        self.assertEqual(await self._visible("u"), set())


if __name__ == "__main__":
    unittest.main()
