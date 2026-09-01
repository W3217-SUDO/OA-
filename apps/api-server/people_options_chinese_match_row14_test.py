"""9.1 row 14: shared people options use complete active HR names."""
from __future__ import annotations
import unittest
import httpx
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool
from app.database import Base, get_db
from app.main import _task_display_dicts, app
from app.models import BusinessRecord, User
from app.security import current_identity

class PeopleOptionsChineseMatchRow14Test(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine=create_async_engine("sqlite+aiosqlite:///:memory:",connect_args={"check_same_thread":False},poolclass=StaticPool)
        self.sessions=async_sessionmaker(self.engine,expire_on_commit=False,class_=AsyncSession)
        async with self.engine.begin() as connection: await connection.run_sync(Base.metadata.create_all)
        async with self.sessions() as db:
            db.add_all([
                User(username="fanwenlin",display_name="Fwl",department="调查部",role="user",password_hash="x",is_active=True),
                User(username="fanlingling",display_name="范玲玲",department="调查部",role="user",password_hash="x",is_active=True),
                BusinessRecord(module="hr",serial_no="HR-R14-1",title="范文林",customer="",status="在职",owner="fanwenlin",department="调查部",data={"username":"fanwenlin"}),
                BusinessRecord(module="hr",serial_no="HR-R14-2",title="范玲玲",customer="",status="在职",owner="fanlingling",department="调查部",data={"username":"fanlingling"}),
            ]); await db.commit()
        self.previous=dict(app.dependency_overrides); app.dependency_overrides[get_db]=self.override_db; app.dependency_overrides[current_identity]=lambda:{"username":"fanwenlin","role":"user"}
        self.client=httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url="http://row14.test")
    async def override_db(self):
        async with self.sessions() as db: yield db
    async def asyncTearDown(self):
        await self.client.aclose(); app.dependency_overrides.clear(); app.dependency_overrides.update(self.previous); await self.engine.dispose()
    async def test_all_matching_active_hr_names_are_searchable(self):
        response=await self.client.get("/api/v1/people/options"); self.assertEqual(response.status_code,200,response.text)
        matches=[item for item in response.json()["items"] if "范" in item["search_text"]]
        self.assertEqual({item["label"] for item in matches},{"范文林","范玲玲"})
        fanwenlin = next(item for item in matches if item["username"]=="fanwenlin")
        self.assertEqual(fanwenlin["label"],"范文林")
        self.assertIn("Fwl", fanwenlin["search_text"])
        self.assertIn("fanwenlin", fanwenlin["search_text"])
        async with self.sessions() as db:
            task = BusinessRecord(module="task", serial_no="RW-R14-1", title="调查子任务", customer="", status="待接收", owner="fanwenlin", department="调查部", data={})
            db.add(task); await db.commit(); await db.refresh(task)
            rendered = (await _task_display_dicts([task], db))[0]
        self.assertEqual(rendered["owner_display_name"], "范文林")
if __name__=="__main__": unittest.main()
