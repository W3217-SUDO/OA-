"""当事人中心读独立的 parties 表：范围、类型筛选、分页与迁移幂等。"""
import unittest

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.areas.crm.router import list_parties
from app.core.party_table_migration import upgrade_party_table
from app.database import Base
from app.models import Party, User

ADMIN = {"username": "admin", "role": "admin", "_page_menu_capability": True}


def party(pid, serial, name, kind="申请人", status="T", owner="admin", **data):
    return Party(id=pid, serial_no=serial, name=name, party_type=kind, status=status, owner=owner,
                 department="上海分所", description="", data={"customer_type": kind, **data})


class PartyListScopeTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool,
        )
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with self.sessions() as db:
            db.add_all([
                User(username="admin", display_name="管理者", role="admin", role_ids=["admin"], password_hash="x"),
                User(username="u1", display_name="员工甲", role="user", role_ids=["user"], password_hash="x"),
                party(1, "CODEX-P1", "张三", owner="u1"),
                party(2, "CODEX-P2", "李四", kind="未设置", customer_managers=["u1"]),
                party(3, "CODEX-P3", "王五", owner="admin"),
                party(4, "CODEX-P4", "已删当事人", status="已回收", owner="u1"),
                party(5, "CODEX-P5", "公海当事人", status="公海"),
            ])
            await db.commit()

    async def asyncTearDown(self):
        await self.engine.dispose()

    async def _list(self, identity=ADMIN, **params):
        async with self.sessions() as db:
            args = dict(scope="company", name="", party_type="", manager="", page=1, page_size=15, identity=identity, db=db)
            args.update(params)
            return await list_parties(**args)

    async def test_company_scope_excludes_recycled_and_public_rows(self):
        result = await self._list()
        self.assertEqual({row["serial_no"] for row in result["items"]}, {"CODEX-P1", "CODEX-P2", "CODEX-P3"})
        self.assertEqual(result["total"], 3)

    async def test_type_and_name_filters_and_paging(self):
        self.assertEqual([r["serial_no"] for r in (await self._list(party_type="未设置"))["items"]], ["CODEX-P2"])
        self.assertEqual([r["title"] for r in (await self._list(name="张"))["items"]], ["张三"])
        page = await self._list(page=2, page_size=2)
        self.assertEqual((page["total"], len(page["items"])), (3, 1))

    async def test_mine_scope_uses_owner_or_managers_and_recycle_scope_only_deleted(self):
        user = {"username": "u1", "role": "user", "_page_menu_capability": True}
        mine = await self._list(identity=user, scope="mine")
        self.assertEqual({r["serial_no"] for r in mine["items"]}, {"CODEX-P1", "CODEX-P2"})
        recycle = await self._list(identity=user, scope="recycle")
        self.assertEqual([r["serial_no"] for r in recycle["items"]], ["CODEX-P4"])

    async def test_row_shape_matches_customer_list_rows(self):
        row = (await self._list(name="CODEX-P1"))["items"][0]
        self.assertEqual((row["id"], row["module"], row["data"]["customer_type"]), (1, "customer", "申请人"))
        self.assertIn("contract_count", row["data"])

    async def test_upgrade_is_idempotent(self):
        async with self.engine.begin() as connection:
            await connection.run_sync(upgrade_party_table)
            await connection.run_sync(upgrade_party_table)


if __name__ == "__main__":
    unittest.main()
