import os
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"

import unittest
import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database import Base, get_db
from app.main import app
from app.models import BusinessRecord, RolePermission, SystemParameter, User, WorkflowEvent
from app.security import current_identity


class CustomerRecycleReleaseTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.identity = {"username": "CODEX-owner", "role": "user"}
        async with self.sessions() as db:
            for name, role, department in (("owner", "user", "CODEX-A"), ("manager", "manager", "CODEX-A"), ("admin", "admin", "CODEX-B"), ("outsider", "user", "CODEX-B")):
                db.add(User(username=f"CODEX-{name}", display_name=name, role=role,
                            department=department, password_hash="test-only", is_active=True))
            db.add(RolePermission(role="user", display_name="CODEX-user", data_scope="本人及共享数据",
                                  menu_keys=["customer-recycle", "customer-mine", "customer-public"], field_keys=["*"]))
            db.add(RolePermission(role="manager", display_name="CODEX-manager", data_scope="本部门数据",
                                  menu_keys=["customer-dept-recycle", "customer-public"], field_keys=["*"]))
            db.add(SystemParameter(category="customer_type", code="customer", name="客户", is_active=True))
            customer = BusinessRecord(module="customer", serial_no="CODEX-RECYCLE-RELEASE", title="CODEX recycle release",
                                      customer="CODEX recycle release", status="已回收", owner="CODEX-owner", department="CODEX-A",
                                      data={"customer_type": "客户", "customer_managers": ["CODEX-owner"],
                                            "status_before_recycle": "潜在", "shared_with": [], "is_shared": "否"})
            db.add(customer)
            await db.commit()
            self.customer_id = customer.id
        async def override_db():
            async with self.sessions() as db:
                yield db
        self.overrides = dict(app.dependency_overrides)
        app.dependency_overrides[get_db] = override_db
        app.dependency_overrides[current_identity] = lambda: self.identity
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://recycle-release.test")

    async def asyncTearDown(self):
        await self.client.aclose()
        app.dependency_overrides.clear()
        app.dependency_overrides.update(self.overrides)
        await self.engine.dispose()

    async def action(self, action):
        return await self.client.post(f"{settings.api_prefix}/customers/{self.customer_id}/{action}", json={"comment": "CODEX flow"})

    async def ids(self, scope):
        response = await self.client.get(f"{settings.api_prefix}/customers", params={"scope": scope, "customer_type": "客户"})
        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        self.assertEqual(payload["total"], len(payload["items"]))
        return [item["id"] for item in payload["items"]]

    async def snapshot(self):
        async with self.sessions() as db:
            row = await db.get(BusinessRecord, self.customer_id)
            events = list(await db.scalars(select(WorkflowEvent).where(WorkflowEvent.record_id == row.id).order_by(WorkflowEvent.id)))
            return (row.status, row.owner, row.department, dict(row.data),
                    [(event.action, event.from_status, event.to_status, event.operator) for event in events])

    async def release_flow(self, name, role, scope):
        self.identity = {"username": f"CODEX-{name}", "role": role}
        self.assertEqual(await self.ids(scope), [self.customer_id])
        response = await self.action("release")
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json().get("status"), "公海", response.text)
        released = await self.snapshot()
        self.assertEqual(released[:2], ("公海", "公海"))
        self.assertEqual(released[3]["shared_with"], [])
        self.assertEqual(released[3]["is_shared"], "否")
        self.assertEqual(released[4], [("释放公海", "已回收", "公海", f"CODEX-{name}")])
        self.assertEqual(await self.ids(scope), [])
        self.assertEqual(await self.ids("public"), [self.customer_id])
        # release 拒绝：公海客户不能再次释放，所有角色均返回业务失败（HTTP 200 + IsSuccess=false）
        release_rejected = await self.action("release")
        self.assertEqual(release_rejected.status_code, 200, release_rejected.text)
        self.assertFalse(release_rejected.json()["IsSuccess"])
        self.assertEqual(await self.snapshot(), released)
        # restore 拒绝：非 admin 身份对公海客户无修改权限（403）；admin 身份则返回业务失败（状态不是已回收）
        restore_rejected = await self.action("restore")
        if role == "admin":
            self.assertEqual(restore_rejected.status_code, 200, restore_rejected.text)
            self.assertFalse(restore_rejected.json()["IsSuccess"])
        else:
            self.assertEqual(restore_rejected.status_code, 403, restore_rejected.text)
        self.assertEqual(await self.snapshot(), released)
        self.identity = {"username": "CODEX-outsider", "role": "user"}
        claimed = await self.action("claim")
        self.assertEqual(claimed.status_code, 200, claimed.text)
        self.assertEqual(claimed.json()["status"], "潜在")
        saved = await self.snapshot()
        self.assertEqual(saved[:3], ("潜在", "CODEX-outsider", "CODEX-B"))
        self.assertEqual(saved[3]["customer_managers"], ["CODEX-outsider"])
        self.assertEqual(saved[4][-1], ("领取客户", "公海", "潜在", "CODEX-outsider"))
        self.assertEqual(await self.ids("public"), [])
        self.assertEqual(await self.ids("mine"), [self.customer_id])

    async def test_personal_recycle_release_and_claim(self):
        await self.release_flow("owner", "user", "recycle")

    async def test_department_recycle_release_and_claim(self):
        await self.release_flow("manager", "manager", "department_recycle")

    async def test_company_recycle_release_and_claim(self):
        await self.release_flow("admin", "admin", "company_recycle")

    async def test_invisible_customer_release_does_not_mutate(self):
        before = await self.snapshot()
        self.identity = {"username": "CODEX-outsider", "role": "user"}
        response = await self.action("release")
        self.assertEqual(response.status_code, 404, response.text)
        self.assertEqual(await self.snapshot(), before)

    async def test_restore_preserves_previous_status_and_owner(self):
        response = await self.action("restore")
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["status"], "潜在")
        restored = await self.snapshot()
        self.assertEqual(restored[:3], ("潜在", "CODEX-owner", "CODEX-A"))
        self.assertEqual(await self.ids("recycle"), [])
        self.assertEqual(await self.ids("mine"), [self.customer_id])

    async def test_page_menu_capability_owner_flow(self):
        """带 _page_menu_capability 的普通 user 走菜单能力路径，绕过 _require_record_owner_or_manager。"""
        self.identity = {"username": "CODEX-owner", "role": "user", "_page_menu_capability": True}
        # 个人回收站客户 restore 成功（菜单能力放行权限检查）
        self.assertEqual(await self.ids("recycle"), [self.customer_id])
        restore_resp = await self.action("restore")
        self.assertEqual(restore_resp.status_code, 200, restore_resp.text)
        self.assertEqual(restore_resp.json()["status"], "潜在")
        restored = await self.snapshot()
        self.assertEqual(restored[:3], ("潜在", "CODEX-owner", "CODEX-A"))
        self.assertEqual(await self.ids("recycle"), [])
        self.assertEqual(await self.ids("mine"), [self.customer_id])
        # 潜在客户 recycle 成功（菜单能力放行权限检查）
        recycle_resp = await self.action("recycle")
        self.assertEqual(recycle_resp.status_code, 200, recycle_resp.text)
        self.assertEqual(recycle_resp.json()["status"], "已回收")
        recycled = await self.snapshot()
        self.assertEqual(recycled[:2], ("已回收", "CODEX-owner"))
        self.assertEqual(await self.ids("recycle"), [self.customer_id])
        # 个人回收站客户 release 成功
        release_resp = await self.action("release")
        self.assertEqual(release_resp.status_code, 200, release_resp.text)
        self.assertEqual(release_resp.json()["status"], "公海")
        released = await self.snapshot()
        self.assertEqual(released[:2], ("公海", "公海"))
        self.assertEqual(await self.ids("public"), [self.customer_id])
        # 关键断言：带 _page_menu_capability 的非 admin 对公海客户 restore
        # 菜单能力直接放行 _require_record_owner_or_manager，走到业务逻辑层
        # 因状态不是"已回收"，返回 HTTP 200 + IsSuccess=false（而不是 403）
        restore_rejected = await self.action("restore")
        self.assertEqual(restore_rejected.status_code, 200, restore_rejected.text)
        self.assertFalse(restore_rejected.json()["IsSuccess"])
        self.assertEqual(await self.snapshot(), released)


if __name__ == "__main__":
    unittest.main()
