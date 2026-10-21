"""用户页面授权：前端总会带上基础页面“控制台”，后端不能因此拒绝保存。"""
import unittest

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.api_schemas.identity import UserPermissionOverrideUpdate
from app.core.user_permission_overrides import update_user_permission_overrides
from app.database import Base
from app.models import User


class UserPagePermissionBasePagesTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool,
        )
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with self.sessions() as db:
            db.add(User(username="u1", display_name="员工", role="user", role_ids=["user"], password_hash="x"))
            await db.commit()
            self.user_id = (await db.scalar(User.__table__.select().where(User.username == "u1").with_only_columns(User.id)))

    async def asyncTearDown(self):
        await self.engine.dispose()

    async def _save(self, menu_keys):
        async with self.sessions() as db:
            user = await update_user_permission_overrides(
                self.user_id, UserPermissionOverrideUpdate(menu_keys=menu_keys), db,
                actor="admin", authorization_source="test")
            await db.commit()
            return list((user.profile or {}).get("permission_overrides", {}).get("menu_keys", []))

    async def test_dashboard_base_page_is_accepted_with_other_pages(self):
        saved = await self._save(["dashboard", "user-center", "party-company", "party-company-civil"])
        self.assertIn("party-company-civil", saved)
        self.assertIn("user-center", saved)

    async def test_unknown_menu_keys_are_still_rejected(self):
        from fastapi import HTTPException
        with self.assertRaises(HTTPException) as caught:
            await self._save(["dashboard", "user-center", "no-such-page"])
        self.assertIn("no-such-page", str(caught.exception.detail))
        self.assertNotIn("dashboard", str(caught.exception.detail))


if __name__ == "__main__":
    unittest.main()
