"""501583（fwl 11-05）：案件列表“批量修改 → 修改案源人”。

规则同详情里单个修改（501293）：只能一人、从在职人员里选；写到详情、提成、业绩排行都读的 business_owner/source_person
（原来批量接口只写 source_lawyer，没人读，等于没改）；每个案件记一条案件日志。
"""

from __future__ import annotations

import unittest

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.core.agency_fee_ranking import source_people
from app.core.cases import _case_commission_role_person_tokens
from app.core.constants import CASE_COMMISSION_ROLES
from app.database import Base, get_db
from app.main import app
from app.models import BusinessRecord, User, WorkflowEvent
from app.security import current_identity

API = settings.api_prefix
ADMIN = {"username": "b583-admin", "role": "admin", "role_ids": ["admin"], "_actual_role_ids": ["admin"], "display_name": "管理者583", "department": "诉讼部"}
SOURCE_ROLE = next(role for role in CASE_COMMISSION_ROLES if role["key"] == "source")


class CaseBatchSourcePerson501583Test(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with self.sessions() as db:
            for username, name in ((ADMIN["username"], ADMIN["display_name"]), ("old583", "原案源人"), ("new583", "新案源人")):
                db.add(User(username=username, display_name=name, department="诉讼部", role="user", role_ids=["user"], password_hash="x", is_active=True))
            self.case_ids = []
            for no in ("B583-1", "B583-2"):
                case = BusinessRecord(module="case", serial_no=no, title=no, customer="客户583", status="文书准备", owner=ADMIN["username"], department="诉讼部", data={
                    "case_type": "民事争议", "handling_lawyers": ["管理者583"], "handling_lawyer_usernames": [ADMIN["username"]],
                    "business_owner": "原案源人", "source_person": "原案源人", "business_owner_username": "old583", "source_person_username": "old583",
                    "business_owner_usernames": ["old583"],
                })
                db.add(case)
                await db.flush()
                self.case_ids.append(case.id)
            await db.commit()
        self.previous_overrides = dict(app.dependency_overrides)
        app.dependency_overrides[get_db] = self.override_db
        app.dependency_overrides[current_identity] = lambda: ADMIN
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://b583.test")

    async def asyncTearDown(self) -> None:
        await self.client.aclose()
        app.dependency_overrides.clear()
        app.dependency_overrides.update(self.previous_overrides)
        await self.engine.dispose()

    async def override_db(self):
        async with self.sessions() as db:
            yield db

    async def test_batch_source_person_updates_fields_read_by_detail_commission_and_ranking(self):
        response = await self.client.post(f"{API}/cases/batch-update", json={"case_ids": self.case_ids, "source_lawyer": "new583"})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["updated"], 2)
        async with self.sessions() as db:
            for case_id in self.case_ids:
                case = await db.get(BusinessRecord, case_id)
                data = case.data
                self.assertEqual((data["business_owner"], data["source_person"]), ("新案源人", "新案源人"))
                self.assertEqual((data["business_owner_username"], data["source_person_username"]), ("new583", "new583"))
                self.assertEqual(_case_commission_role_person_tokens(data, SOURCE_ROLE)[:1], ["new583"], "提成按新案源人算")
                self.assertEqual(source_people(case), ["新案源人"], "业绩排行按新案源人")
            comments = list((await db.scalars(select(WorkflowEvent.comment).where(WorkflowEvent.action == "批量修改案件"))).all())
            self.assertEqual(len(comments), 2)
            self.assertTrue(all("案源人：原案源人 → 新案源人" in item for item in comments))

    async def test_source_person_must_be_one_active_staff(self):
        bad = await self.client.post(f"{API}/cases/batch-update", json={"case_ids": self.case_ids, "source_lawyer": "不存在的人"})
        self.assertEqual(bad.status_code, 422, bad.text)
        empty = await self.client.post(f"{API}/cases/batch-update", json={"case_ids": self.case_ids, "source_lawyer": " "})
        self.assertEqual(empty.status_code, 422, empty.text)
        async with self.sessions() as db:
            self.assertEqual((await db.get(BusinessRecord, self.case_ids[0])).data["business_owner"], "原案源人")


if __name__ == "__main__":
    unittest.main()
