"""501631：办离职/停用前，名下负责的未结束任务必须先转交；离职人员未结束任务清单，管理员按人批量转交。"""
import unittest

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database import Base, get_db
from app.main import app
from app.models import BusinessRecord, User, WorkflowEvent
from app.security import current_identity

API = settings.api_prefix
ADMIN = {"username": "admin", "role": "admin", "role_ids": ["admin"], "display_name": "管理者", "department": "上海分所"}
MANAGER = {"username": "boss", "role": "manager", "role_ids": ["manager"], "_actual_role_ids": ["manager"], "display_name": "部长", "department": "上海分所"}


def task(serial, owner, status="处理中", **data):
    return BusinessRecord(module="task", serial_no=serial, title=serial, status=status, owner=owner, department="上海分所",
                          data={"initiator": data.pop("initiator", "admin"), "collaborators": data.pop("collaborators", []), **data})


class DepartureOpenTasksTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with self.sessions() as db:
            for username, name, active in (("admin", "管理者", True), ("boss", "部长", True), ("leaver", "张三", True), ("gone", "李四", False),
                                           ("newbie", "王五", True), ("other", "赵六", True)):
                db.add(User(username=username, display_name=name, department="上海分所", password_hash="x", role="admin" if username == "admin" else "user", is_active=active))
            db.add(BusinessRecord(module="hr", serial_no="E1", title="张三", status="在职", owner="leaver", department="上海分所", data={"username": "leaver"}))
            db.add(BusinessRecord(module="hr", serial_no="E2", title="李四", status="离职", owner="gone", department="上海分所", data={"username": "gone"}))
            rows = [
                task("T-OWN", "leaver"), task("T-OWN-DONE", "leaver", status="已完成"), task("T-INIT", "other", initiator="leaver"),
                task("T-COLLAB", "other", collaborators=["leaver", "other2"]), task("T-NONE", "other"),
                task("G-1", "gone", collaborators=["gone"]), task("G-2", "gone", status="待接收"), task("G-INIT", "other", initiator="gone"),
                task("G-CANCEL", "gone", status="已取消"), task("NOACC", "ghost"),
                # 501631（tgn 11-06）：老系统调查任务不是案件任务，不算未结束、不列入离职清单、不挡离职
                task("INV-L", "leaver", source_table="Legal_Investigation_Task", migration_source="hz"),
                task("INV-G", "gone", source_table="Legal_Investigation_Task", migration_source="hz"),
                task("INV-X", "fanyl", source_table="Legal_Investigation_Task", migration_source="hz"),
            ]
            db.add_all(rows); await db.commit()
            self.ids = {row.serial_no: row.id for row in rows}
        app.dependency_overrides[get_db] = self._db
        self.identity = ADMIN
        app.dependency_overrides[current_identity] = lambda: self.identity
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://departure.test")

    async def _db(self):
        async with self.sessions() as db:
            yield db

    async def asyncTearDown(self):
        await self.client.aclose(); app.dependency_overrides.clear(); await self.engine.dispose()

    async def employee_id(self, serial):
        async with self.sessions() as db:
            return (await db.scalar(select(BusinessRecord).where(BusinessRecord.module == "hr", BusinessRecord.serial_no == serial))).id

    async def test_legacy_investigation_tasks_not_counted(self):
        listing = (await self.client.get(f"{API}/hr/departure-tasks", params={"username": "leaver"})).json()
        self.assertNotIn("INV-L", [item["serial_no"] for item in listing["items"]])
        departed = (await self.client.get(f"{API}/hr/departure-tasks")).json()
        serials = {item["serial_no"] for group in departed["people"] for item in group["items"]}
        self.assertFalse(serials & {"INV-L", "INV-G", "INV-X"}, departed)
        self.assertNotIn("fanyl", [group["username"] for group in departed["people"]])
        moved = await self.client.post(f"{API}/hr/departure-tasks/handover", json={"from_username": "gone", "recipient": "newbie", "task_ids": [self.ids["INV-G"]]})
        self.assertNotEqual(moved.json().get("updated"), 1, moved.text)

    async def test_person_list_and_departure_blocked_until_handed_over(self):
        listing = (await self.client.get(f"{API}/hr/departure-tasks", params={"username": "leaver"})).json()
        self.assertEqual([(item["serial_no"], item["roles"]) for item in listing["items"]],
                         [("T-OWN", ["负责人"]), ("T-INIT", ["发起人"]), ("T-COLLAB", ["协作人"])], "负责人在前，已完成的不算")
        self.assertEqual(listing["owner_count"], 1)

        employee_id = await self.employee_id("E1")
        body = {"to_status": "离职", "effective_date": "2026-11-05", "reason": "个人原因", "handover_to": "", "comment": ""}
        blocked = await self.client.post(f"{API}/hr/{employee_id}/transition", json=body)
        self.assertEqual(blocked.status_code, 409, blocked.text)
        self.assertIn("还负责 1 条未结束任务", blocked.json()["detail"])

        moved = await self.client.post(f"{API}/hr/departure-tasks/handover", json={
            "from_username": "leaver", "recipient": "newbie", "task_ids": [self.ids["T-OWN"], self.ids["T-INIT"], self.ids["T-COLLAB"]]})
        self.assertEqual(moved.json(), {"updated": 3, "owner_changed": 1, "recipient": "newbie"}, moved.text)
        async with self.sessions() as db:
            own = await db.get(BusinessRecord, self.ids["T-OWN"])
            self.assertEqual((own.owner, own.status, own.data["handoff_from"]), ("newbie", "待接收", "leaver"))
            self.assertEqual((await db.get(BusinessRecord, self.ids["T-INIT"])).data["initiator"], "newbie")
            collab = await db.get(BusinessRecord, self.ids["T-COLLAB"])
            self.assertEqual((collab.owner, collab.status, collab.data["collaborators"]), ("other", "处理中", ["newbie", "other2"]))
            events = (await db.scalars(select(WorkflowEvent).where(WorkflowEvent.action == "离职任务转交"))).all()
            self.assertEqual(len(events), 3)

        done = await self.client.post(f"{API}/hr/{employee_id}/transition", json=body)
        self.assertEqual(done.status_code, 200, done.text)
        self.assertEqual(done.json()["status"], "离职")

    async def test_initiator_only_does_not_block(self):
        async with self.sessions() as db:
            own = await db.get(BusinessRecord, self.ids["T-OWN"]); own.status = "已完成"; await db.commit()
        employee_id = await self.employee_id("E1")
        response = await self.client.post(f"{API}/hr/{employee_id}/transition", json={
            "to_status": "停用", "effective_date": "2026-11-05", "reason": "停用测试", "handover_to": "", "comment": ""})
        self.assertEqual(response.status_code, 200, response.text)

    async def test_system_user_deactivate_blocked(self):
        async with self.sessions() as db:
            user = await db.scalar(select(User).where(User.username == "other"))
        response = await self.client.patch(f"{API}/system/users/{user.id}", json={"is_active": False})
        self.assertEqual(response.status_code, 409, response.text)
        self.assertIn("未结束任务", response.json()["detail"])
        async with self.sessions() as db:
            self.assertTrue((await db.get(User, user.id)).is_active, "被拦住时账号不停用")

    async def test_departed_list_admin_only(self):
        data = (await self.client.get(f"{API}/hr/departure-tasks")).json()
        people = {group["username"]: group for group in data["people"]}
        self.assertEqual(set(people), {"gone", "ghost"}, "在职的不列；没账号的负责人也列")
        self.assertEqual(sorted(item["serial_no"] for item in people["gone"]["items"]), ["G-1", "G-2", "G-INIT"])
        self.assertEqual(people["gone"]["owner_count"], 2)
        self.assertTrue(people["ghost"]["no_account"])
        self.assertEqual(data["owner_total"], 3)

        self.identity = MANAGER
        self.assertEqual((await self.client.get(f"{API}/hr/departure-tasks")).status_code, 403)

        self.identity = ADMIN
        bad = await self.client.post(f"{API}/hr/departure-tasks/handover", json={"from_username": "gone", "recipient": "gone", "task_ids": [self.ids["G-1"]]})
        self.assertEqual(bad.status_code, 422)
        closed = await self.client.post(f"{API}/hr/departure-tasks/handover", json={"from_username": "gone", "recipient": "newbie", "task_ids": [self.ids["G-CANCEL"]]})
        self.assertEqual(closed.status_code, 409)
        ok = await self.client.post(f"{API}/hr/departure-tasks/handover", json={"from_username": "gone", "recipient": "newbie", "task_ids": [self.ids["G-1"], self.ids["G-2"]]})
        self.assertEqual(ok.status_code, 200, ok.text)
        async with self.sessions() as db:
            g1 = await db.get(BusinessRecord, self.ids["G-1"])
            self.assertEqual((g1.owner, g1.data["collaborators"]), ("newbie", []), "接收人成了负责人就不再当协作人")
        left = {group["username"]: group for group in (await self.client.get(f"{API}/hr/departure-tasks")).json()["people"]}
        self.assertEqual([item["serial_no"] for item in left["gone"]["items"]], ["G-INIT"])


if __name__ == "__main__":
    unittest.main()
