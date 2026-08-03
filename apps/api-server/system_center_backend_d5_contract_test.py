"""可执行的系统中心后端契约测试。

测试只使用隔离内存 SQLite 与 FastAPI 依赖覆盖，不打开 legal_platform.db，
也不会创建持久化业务数据。
"""

import unittest

import httpx
from fastapi import status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database import Base, get_db
from app.main import SYSTEM_ACTION_DEFINITIONS, app
from app.models import BusinessRecord, RolePermission, SystemConfig, SystemMenu, SystemParameter, WorkflowEvent
from app.security import current_identity


ADMIN = {"username": "contract-admin", "role": "admin", "display_name": "契约管理员", "department": "系统"}
USER = {"username": "contract-user", "role": "user", "display_name": "契约用户", "department": "业务"}
API = settings.api_prefix


def flatten_tree(nodes):
    """Yield every M/A node, including recursively nested menu descendants."""
    for node in nodes:
        yield node
        yield from flatten_tree(node.get("children") or [])


class SystemCenterBackendD5Contract(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
        tables = [
            SystemParameter.__table__, SystemConfig.__table__, SystemMenu.__table__,
            RolePermission.__table__, BusinessRecord.__table__, WorkflowEvent.__table__,
        ]
        async with self.engine.begin() as conn:
            await conn.run_sync(lambda sync_conn: Base.metadata.create_all(sync_conn, tables=tables))

        async with self.sessions() as db:
            db.add_all([
                SystemParameter(category="case_phase", code="ROOT", name="根阶段", extra={"parent_code": ""}, created_by="seed", updated_by="seed"),
                SystemParameter(category="case_phase", code="CHILD", name="子阶段", extra={"parent_code": "ROOT"}, created_by="seed", updated_by="seed"),
                SystemParameter(category="cause", code="C-001", name="合同纠纷", extra={"parent_code": ""}, created_by="seed", updated_by="seed"),
                SystemParameter(category="cause", code="C-002", name="合同解除", extra={"parent_code": "C-001"}, created_by="seed", updated_by="seed"),
                SystemConfig(
                    key="customer_share_policy", label="客户共享", group="业务",
                    value={"all_days": 100, "filed_days": 100, "premium_days": 100, "standard_days": 100, "basic_days": 100, "shared_days": 100},
                    description="客户共享天数",
                ),
                SystemConfig(
                    key="company_profile", label="公司资料", group="公司",
                    value={"name": "测试公司"}, description="公司基础资料",
                ),
                SystemMenu(key="system", parent_key="", label="系统中心", description="系统入口"),
                SystemMenu(key="system-parameters", parent_key="system", label="系统参数", description="参数维护"),
                SystemMenu(key="system-management", parent_key="system", label="系统管理", description="管理入口"),
                SystemMenu(key="system-management-cache", parent_key="system-management", label="缓存管理", description="缓存维护"),
                SystemMenu(key="system-management-menu", parent_key="system-management", label="菜单管理", description="菜单维护"),
                SystemMenu(key="system-management-config", parent_key="system-management", label="系统配置", description="配置维护"),
                RolePermission(role="user", display_name="普通用户", data_scope="本人及共享数据", menu_keys=["user-center"], field_keys=[]),
                RolePermission(role="manager", display_name="部门负责人", data_scope="本部门数据", menu_keys=["user-center"], field_keys=[]),
                RolePermission(role="auditor", display_name="审批人员", data_scope="授权审批数据", menu_keys=["user-center"], field_keys=[]),
            ])
            await db.commit()

        async def override_db():
            async with self.sessions() as db:
                yield db

        app.dependency_overrides[get_db] = override_db
        app.dependency_overrides[current_identity] = lambda: ADMIN
        from app import main as main_module
        main_module.SYSTEM_PARAMETER_CACHE.clear()
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://system-center.test")

    async def asyncTearDown(self):
        await self.client.aclose()
        app.dependency_overrides.clear()
        await self.engine.dispose()

    async def test_system_lists_support_paging_keyword_and_legacy_shapes(self):
        paged_parameter = await self.client.get(
            f"{API}/system/parameters",
            params={"category": "case_phase", "page": 1, "page_size": 1, "keyword": "阶段"},
        )
        self.assertEqual(paged_parameter.status_code, status.HTTP_200_OK)
        body = paged_parameter.json()
        self.assertEqual((body["total"], body["page"], body["page_size"]), (2, 1, 1))
        self.assertEqual(len(body["items"]), 1)

        legacy_parameter = await self.client.get(f"{API}/system/parameters", params={"category": "case_phase"})
        self.assertEqual(legacy_parameter.status_code, status.HTTP_200_OK)
        self.assertEqual(len(legacy_parameter.json()["items"]), 2)
        self.assertIn("categories", legacy_parameter.json())
        self.assertNotIn("page", legacy_parameter.json())

        for path in ("/system/menus", "/system/configs", "/system/caches"):
            paged = await self.client.get(f"{API}{path}", params={"page": 1, "page_size": 1, "keyword": "系统"})
            self.assertEqual(paged.status_code, status.HTTP_200_OK, path)
            paged_body = paged.json()
            self.assertEqual((paged_body["page"], paged_body["page_size"]), (1, 1), path)
            self.assertIn("total", paged_body, path)
            self.assertLessEqual(len(paged_body["items"]), 1, path)
            legacy = await self.client.get(f"{API}{path}")
            self.assertEqual(legacy.status_code, status.HTTP_200_OK, path)
            self.assertIn("items", legacy.json(), path)
            if path == "/system/menus":
                self.assertIn("total", legacy.json())
                self.assertNotIn("page", legacy.json())
            elif path == "/system/configs":
                self.assertNotIn("page", legacy.json())
                self.assertNotIn("total", legacy.json())
            else:
                self.assertEqual(len(legacy.json()["items"]), 8)
                self.assertEqual(legacy.json()["total"], 8)
                self.assertEqual(legacy.json()["page"], 1)
                self.assertEqual(legacy.json()["page_size"], 15)
                self.assertEqual(legacy.json()["pages"], 1)
                self.assertIn("total", legacy.json())

    async def test_role_list_supports_legacy_and_paged_keyword_shapes(self):
        legacy = await self.client.get(f"{API}/system/role-permissions")
        self.assertEqual(legacy.status_code, status.HTTP_200_OK)
        self.assertEqual(len(legacy.json()["items"]), 3)
        self.assertNotIn("page", legacy.json())

        paged = await self.client.get(
            f"{API}/system/role-permissions",
            params={"page": 1, "page_size": 1, "keyword": "负责人"},
        )
        self.assertEqual(paged.status_code, status.HTTP_200_OK)
        self.assertEqual((paged.json()["total"], paged.json()["page"], paged.json()["page_size"], paged.json()["pages"]), (1, 1, 1, 1))
        self.assertEqual([item["role"] for item in paged.json()["items"]], ["manager"])

        invalid = await self.client.get(f"{API}/system/role-permissions", params={"page_size": 201})
        self.assertEqual(invalid.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)

    async def test_role_and_audit_reads_keep_admin_boundary(self):
        app.dependency_overrides[current_identity] = lambda: USER
        role_response = await self.client.get(f"{API}/system/role-permissions")
        audit_response = await self.client.get(f"{API}/audit/events")
        self.assertEqual(role_response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(audit_response.status_code, status.HTTP_403_FORBIDDEN)
        app.dependency_overrides[current_identity] = lambda: ADMIN

    async def test_parameter_parent_missing_self_and_ancestor_cycle_are_422(self):
        for category in ("fee_type", "case_phase", "cause"):
            missing = await self.client.post(
                f"{API}/system/parameters",
                json={"category": category, "code": f"{category}-MISSING", "name": "缺失父级", "extra": {"parent_code": "NOPE"}},
            )
            self.assertEqual(missing.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY, category)

            self_ref = await self.client.post(
                f"{API}/system/parameters",
                json={"category": category, "code": f"{category}-SELF", "name": "自引用", "extra": {"parent_code": f"{category}-SELF"}},
            )
            self.assertEqual(self_ref.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY, category)

        async with self.sessions() as db:
            root = await db.scalar(select(SystemParameter).where(SystemParameter.category == "cause", SystemParameter.code == "C-001"))
            child = await db.scalar(select(SystemParameter).where(SystemParameter.category == "cause", SystemParameter.code == "C-002"))
            root_id, child_id = root.id, child.id
        cycle = await self.client.patch(f"{API}/system/parameters/{root_id}", json={"extra": {"parent_code": "C-002"}})
        self.assertEqual(cycle.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)
        self.assertNotEqual(root_id, child_id)

    async def test_cause_autocomplete_returns_real_utf8_id_code_name_nodes(self):
        response = await self.client.get(f"{API}/system/parameters/cause/autocomplete", params={"keyword": "合同"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        items = response.json()["items"]
        self.assertEqual([item["code"] for item in items], ["C-001", "C-002"])
        self.assertTrue(all(set(item) == {"id", "code", "name"} and isinstance(item["id"], int) for item in items))
        self.assertEqual([item["name"] for item in items], ["合同纠纷", "合同解除"])

    async def test_permission_tree_recursively_contains_declared_menu_and_action_nodes(self):
        self.assertGreater(len(SYSTEM_ACTION_DEFINITIONS), 6)
        response = await self.client.get(f"{API}/system/role-permissions")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        nodes = list(flatten_tree(response.json()["permission_tree"]))
        self.assertTrue(nodes)
        self.assertTrue(all(node["node_type"] in {"M", "A"} for node in nodes))
        self.assertTrue(all(node["node_code"] and "state" in node and "checked" in node["state"] for node in nodes))
        self.assertTrue(all("node_original_id" in node for node in nodes))
        menu_nodes = [node for node in nodes if node["node_type"] == "M"]
        action_nodes = [node for node in nodes if node["node_type"] == "A"]
        self.assertTrue(menu_nodes)
        self.assertTrue(action_nodes)
        declared = {item["code"] for item in SYSTEM_ACTION_DEFINITIONS if item["menu_key"] in {node["node_code"] for node in menu_nodes}}
        self.assertEqual({node["node_code"] for node in action_nodes}, declared)
        self.assertTrue(all(node["children"] == [] for node in action_nodes))
        action_key = action_nodes[0]["node_code"]

        update = await self.client.patch(
            f"{API}/system/role-permissions/user",
            json={"data_scope": "本人及共享数据", "menu_keys": ["user-center"], "field_keys": [], "action_keys": [action_key]},
        )
        self.assertEqual(update.status_code, status.HTTP_200_OK)
        self.assertEqual(update.json()["action_keys"], [action_key])
        async with self.sessions() as db:
            stored = await db.scalar(select(RolePermission).where(RolePermission.role == "user"))
            self.assertIn(f"@action:{action_key}", stored.menu_keys)
        refreshed = await self.client.get(f"{API}/system/role-permissions")
        self.assertEqual(refreshed.status_code, status.HTTP_200_OK)
        refreshed_actions = [node for node in flatten_tree(refreshed.json()["permission_tree"]) if node["node_type"] == "A"]
        self.assertTrue(any(node["node_code"] == action_key and node["state"]["checked"] for node in refreshed_actions))
        self.assertTrue(all(node["state"]["checked"] == (node["node_code"] == action_key) for node in refreshed_actions))

    async def test_all_system_writes_emit_persisted_audit_events(self):
        created = await self.client.post(
            f"{API}/system/parameters",
            json={"category": "cause", "code": "AUD-1", "name": "审计案由", "extra": {"parent_code": ""}},
        )
        self.assertEqual(created.status_code, status.HTTP_201_CREATED)

        menu = await self.client.post(
            f"{API}/system/menus",
            json={"label": "审计菜单", "description": "待删除测试菜单", "parent_key": "system"},
        )
        self.assertEqual(menu.status_code, status.HTTP_201_CREATED)
        menu_id = menu.json()["id"]
        menu_key = menu.json()["key"]
        updated_menu = await self.client.patch(f"{API}/system/menus/{menu_id}", json={"label": "审计菜单已更新"})
        self.assertEqual(updated_menu.status_code, status.HTTP_200_OK)
        deleted_menu = await self.client.delete(f"{API}/system/menus/{menu_id}")
        self.assertEqual(deleted_menu.status_code, status.HTTP_204_NO_CONTENT)
        self.assertTrue(menu_key.startswith("legacy-menu-"))

        config = await self.client.patch(
            f"{API}/system/configs/customer_share_policy",
            json={"value": {"all_days": 100, "filed_days": 100, "premium_days": 100, "standard_days": 100, "basic_days": 100, "shared_days": 100}},
        )
        self.assertEqual(config.status_code, status.HTTP_200_OK)
        cache = await self.client.post(f"{API}/system/caches/system-parameters/clear")
        self.assertEqual(cache.status_code, status.HTTP_200_OK)

        action_code = SYSTEM_ACTION_DEFINITIONS[0]["code"]
        role = await self.client.patch(
            f"{API}/system/role-permissions/user",
            json={"data_scope": "本人及共享数据", "menu_keys": ["user-center"], "field_keys": [], "action_keys": [action_code]},
        )
        self.assertEqual(role.status_code, status.HTTP_200_OK)

        events = await self.client.get(f"{API}/audit/events", params={"module": "system_audit", "page_size": 100})
        self.assertEqual(events.status_code, status.HTTP_200_OK)
        self.assertEqual(events.json()["pages"], 1)
        actions = {item["action"] for item in events.json()["items"]}
        self.assertTrue({"创建系统参数", "创建系统菜单", "更新系统菜单", "删除系统菜单", "更新系统配置", "清理系统缓存", "更新角色权限"} <= actions)


if __name__ == "__main__":
    unittest.main()
