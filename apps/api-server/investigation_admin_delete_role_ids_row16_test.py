"""9.1 row 16: legacy investigation deletion belongs to publisher/admin."""
from __future__ import annotations
import unittest
import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession,async_sessionmaker,create_async_engine
from sqlalchemy.pool import StaticPool
from app.database import Base,get_db
from app.main import app
from app.models import BusinessRecord,User
from app.security import current_identity

class InvestigationAdminDeleteRoleIdsRow16Test(unittest.IsolatedAsyncioTestCase):
 async def asyncSetUp(self):
  self.identity={"username":"row16-admin","role":"user","role_ids":["user","admin"],"department":"调查部"}
  self.engine=create_async_engine("sqlite+aiosqlite:///:memory:",connect_args={"check_same_thread":False},poolclass=StaticPool);self.sessions=async_sessionmaker(self.engine,expire_on_commit=False,class_=AsyncSession)
  async with self.engine.begin() as c: await c.run_sync(Base.metadata.create_all)
  async with self.sessions() as db:
   db.add_all([User(username="row16-admin",display_name="管理员",department="调查部",role="user",role_ids=["user","admin"],password_hash="x",is_active=True),User(username="row16-user",display_name="普通用户",department="调查部",role="user",role_ids=["user"],password_hash="x",is_active=True)])
   item=BusinessRecord(module="investigation",serial_no="CODEX-901-R16",title="无效调查任务",customer="客户",status="待分配",owner="row16-user",department="调查部",data={"contract_id":999999,"publisher":"someone-else"});db.add(item);await db.commit();self.record_id=item.id
  self.previous=dict(app.dependency_overrides);app.dependency_overrides[get_db]=self.override_db;app.dependency_overrides[current_identity]=lambda:self.identity;self.client=httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url="http://row16.test")
 async def override_db(self):
  async with self.sessions() as db: yield db
 async def asyncTearDown(self):
  await self.client.aclose();app.dependency_overrides.clear();app.dependency_overrides.update(self.previous);await self.engine.dispose()
 async def test_secondary_admin_role_can_delete_pending_investigation(self):
  response=await self.client.post("/api/v1/investigations/batch-delete",json={"record_ids":[self.record_id]});self.assertEqual(response.status_code,200,response.text);self.assertEqual(response.json()["deleted"],1);self.assertEqual(response.json()["errors"],[])
  async with self.sessions() as db:self.assertIsNone(await db.scalar(select(BusinessRecord).where(BusinessRecord.id==self.record_id)))
 async def test_non_admin_is_rejected(self):
  async with self.sessions() as db:
   item=BusinessRecord(module="investigation",serial_no="CODEX-901-R16-B",title="非发布人不可删",customer="客户",status="待分配",owner="row16-user",department="调查部",data={"publisher":"someone-else"});db.add(item);await db.commit();record_id=item.id
  self.identity={"username":"row16-user","role":"user","role_ids":["user"],"department":"调查部"}
  response=await self.client.post("/api/v1/investigations/batch-delete",json={"record_ids":[record_id]});self.assertEqual(response.json()["deleted"],0);self.assertIn("本人发布",response.json()["errors"][0]["error"])
 async def test_non_admin_publisher_can_delete_from_my_published_tasks(self):
  async with self.sessions() as db:
   item=BusinessRecord(module="investigation",serial_no="CODEX-901-R16-C",title="发布人可删",customer="客户",status="待分配",owner="row16-admin",department="调查部",data={"publisher":"row16-user"});db.add(item);await db.commit();record_id=item.id
  self.identity={"username":"row16-user","role":"user","role_ids":["user"],"department":"调查部"}
  response=await self.client.post("/api/v1/investigations/batch-delete",json={"record_ids":[record_id]});self.assertEqual(response.status_code,200,response.text);self.assertEqual(response.json()["deleted"],1);self.assertEqual(response.json()["errors"],[])
 async def test_legacy_missing_publisher_falls_back_to_owner(self):
  async with self.sessions() as db:
   item=BusinessRecord(module="investigation",serial_no="CODEX-901-R16-D",title="迁移记录发布人回退",customer="客户",status="待分配",owner="row16-user",department="调查部",data={});db.add(item);await db.commit();record_id=item.id
  self.identity={"username":"row16-user","role":"user","role_ids":["user"],"department":"调查部"}
  response=await self.client.post("/api/v1/investigations/batch-delete",json={"record_ids":[record_id]});self.assertEqual(response.status_code,200,response.text);self.assertEqual(response.json()["deleted"],1)
if __name__=="__main__":unittest.main()
