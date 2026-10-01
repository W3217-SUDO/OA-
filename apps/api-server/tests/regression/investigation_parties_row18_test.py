"""Row 18 regression: investigation clues keep repeatable detailed parties."""
import unittest
from uuid import uuid4

import httpx
from fastapi import status
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database import Base, get_db
from app.main import app
from app.models import BusinessRecord, RolePermission, User, WorkflowEvent
from app.security import current_identity


API = settings.api_prefix
IDENTITY = {"username": "row18-admin", "role": "admin", "display_name": "行18管理员", "department": "上海分所"}


class InvestigationPartiesRow18Test(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with self.sessions() as db:
            db.add_all([
                User(username=IDENTITY["username"], display_name=IDENTITY["display_name"], department=IDENTITY["department"], role="admin", password_hash="test", is_active=True),
                RolePermission(role="admin", display_name="行18管理员", data_scope="全所数据", menu_keys=["investigation"], field_keys=[]),
            ])
            await db.commit()
        async def override_db():
            async with self.sessions() as db:
                yield db
        app.dependency_overrides[get_db] = override_db
        app.dependency_overrides[current_identity] = lambda: IDENTITY
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://row18.test")

    async def asyncTearDown(self):
        await self.client.aclose()
        app.dependency_overrides.clear()
        await self.engine.dispose()

    async def test_repeatable_party_details_and_empty_cleanup(self):
        serial = f"ROW18-{uuid4().hex[:10]}"
        async with self.sessions() as db:
            record = BusinessRecord(module="clue", serial_no=serial, title="行18线索", customer="测试客户", status="草稿", owner=IDENTITY["username"], department=IDENTITY["department"], data={})
            db.add(record)
            await db.commit()
            record_id = record.id
        parties = [
            {"nature": "企业", "name": "甲公司", "confirmation_method": "工商信息", "identity_no": "91310000ROW18", "legal_representative": "甲法定代表人", "province": "上海市", "city": "上海市", "district": "浦东新区", "address": "甲公司工商地址"},
            {"nature": "个人", "name": "乙某", "confirmation_method": "现场确认", "identity_no": "310101199001010011", "province": "浙江省", "city": "杭州市", "district": "西湖区", "address": "乙某联系地址"},
        ]
        try:
            saved = await self.client.post(f"{API}/investigations/{record_id}/parties", json={"indictees": parties, "producers": []})
            self.assertEqual(saved.status_code, status.HTTP_200_OK, saved.text)
            self.assertEqual(saved.json()["indictees"], parties)
            listed = await self.client.get(f"{API}/investigations/{record_id}/parties")
            self.assertEqual(listed.status_code, status.HTTP_200_OK, listed.text)
            self.assertEqual(listed.json()["indictees"], parties)
            async with self.sessions() as db:
                current = await db.get(BusinessRecord, record_id)
                self.assertEqual(current.data["indictee"], "甲公司")
            cleared = await self.client.post(f"{API}/investigations/{record_id}/parties", json={"indictees": [], "producers": []})
            self.assertEqual(cleared.status_code, status.HTTP_200_OK, cleared.text)
            async with self.sessions() as db:
                current = await db.get(BusinessRecord, record_id)
                self.assertEqual(current.data["indictees"], [])
                self.assertEqual(current.data["indictee"], "")
        finally:
            async with self.sessions() as db:
                await db.execute(delete(WorkflowEvent).where(WorkflowEvent.record_id == record_id))
                await db.execute(delete(BusinessRecord).where(BusinessRecord.id == record_id))
                await db.commit()


if __name__ == "__main__":
    unittest.main()
