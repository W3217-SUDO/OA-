import hashlib
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import httpx
from fastapi import FastAPI, HTTPException
from sqlalchemy.exc import IntegrityError

from app.global_agent_skills import (
    GLOBAL_SKILL_CONFIG_KEY, add_global_skill, global_skill_store, require_global_admin, save_global_skills,
)
from app.skill_definitions import skill_definition
from app.user_agent_skills import custom_skill_public, normalize_custom_skill, parse_uploaded_skill

ADMIN = {"username": "admin", "role": "admin"}
USER = {"username": "user", "role": "user"}
PAYLOAD = {"name": "真实技能", "description": "安全任务偏好", "instruction": "只读取当前账号有权访问的数据。", "quick_prompts": ["概要"]}
GLOBAL_ID = "global-" + "a" * 32


def record():
    return normalize_custom_skill(PAYLOAD, skill_id=GLOBAL_ID)


class GlobalSkillTest(unittest.IsolatedAsyncioTestCase):
    async def test_global_reads_are_authenticated_and_disabled_definitions_stay_admin_only(self):
        from app.areas.agent_admin.skills import list_global_skills, global_definition, router
        app = FastAPI()
        app.include_router(router)
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://isolated") as client:
            for url in ("/api/v1/agent/global-skills", "/api/v1/agent/skills/personal",
                        "/api/v1/agent/global-skills/" + GLOBAL_ID + "/definition/download"):
                self.assertEqual((await client.get(url)).status_code, 401)
        enabled, disabled = record(), {**record(), "id": "global-" + "b" * 32, "enabled": False}
        with patch("app.global_agent_skills.global_skill_store", AsyncMock(return_value=(None, [enabled, disabled]))), \
                patch("app.areas.agent_admin.skills.global_skill_store", AsyncMock(return_value=(None, [enabled, disabled]))):
            ordinary = await list_global_skills(USER, object())
            self.assertEqual([entry["id"] for entry in ordinary["items"]], [GLOBAL_ID])
            self.assertFalse(ordinary["can_manage"])
            admin = await list_global_skills(ADMIN, object())
            self.assertEqual(len(admin["items"]), 2)
            self.assertTrue(admin["can_manage"])
            with self.assertRaises(HTTPException) as failure:
                await global_definition(disabled["id"], USER, object())
            self.assertEqual(failure.exception.status_code, 404)
            self.assertEqual((await global_definition(disabled["id"], ADMIN, object()))["scope"], "global")

    async def test_changed_global_github_preview_does_not_touch_storage(self):
        from app.areas.agent_admin.skills import install_global_github, GitHubSkillInstallInput
        with patch("app.github_agent_skills.preview_github_skill", AsyncMock(return_value={"sha256": "a" * 64})), \
                patch("app.areas.agent_admin.skills.add_global_skill", AsyncMock()) as save:
            with self.assertRaises(HTTPException) as changed:
                await install_global_github(GitHubSkillInstallInput(url="https://github.com/a/b", sha256="b" * 64), ADMIN, object())
            self.assertEqual(changed.exception.status_code, 409)
            save.assert_not_awaited()

    async def test_generic_config_read_filters_only_skill_namespaces_for_menu_authorized_non_admin(self):
        from app.areas.system.router import list_system_configs
        from app.user_agent_skills import user_skill_config_key

        def config(key):
            return SimpleNamespace(key=key, label=key, group="智能体", value={"instruction": "private"},
                description="", updated_by="admin", updated_at=None)

        configs = [config("company_profile"), config(GLOBAL_SKILL_CONFIG_KEY),
                   config(user_skill_config_key("user")), config(user_skill_config_key("other"))]
        db = SimpleNamespace(scalars=AsyncMock(side_effect=lambda query: SimpleNamespace(all=lambda: configs if "system_configs" in str(query) else [])))
        limited = {**USER, "role": "admin", "_page_menu_capability": True, "_actual_role_ids": ["user"]}
        result = await list_system_configs(page=None, page_size=None, identity=limited, db=db)
        self.assertEqual([item["key"] for item in result["items"]], ["company_profile"])
        result = await list_system_configs(page=None, page_size=None, identity=ADMIN, db=db)
        self.assertEqual(len(result["items"]), 4, "实际管理员保留所有配置字段读取权")

    async def test_all_global_write_routes_require_actual_admin_before_storage_or_network(self):
        from app.areas.agent_admin.skills import router
        from app.database import get_db
        from app.security import current_identity

        app = FastAPI()
        app.include_router(router)
        identity = {**USER, "role": "admin", "_page_menu_capability": True, "_actual_role_ids": ["user"]}
        app.dependency_overrides[current_identity] = lambda: identity
        app.dependency_overrides[get_db] = lambda: object()
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://isolated") as client:
            requests = [
                ("POST", "/api/v1/agent/global-skills", {"json": PAYLOAD}),
                ("PATCH", "/api/v1/agent/global-skills/" + GLOBAL_ID, {"json": {"enabled": False}}),
                ("DELETE", "/api/v1/agent/global-skills/" + GLOBAL_ID, {}),
                ("POST", "/api/v1/agent/global-skills/upload", {"files": {"file": ("SKILL.md", b"test")}}),
                ("POST", "/api/v1/agent/global-skills/github/preview", {"json": {"url": "https://github.com/a/b"}}),
                ("POST", "/api/v1/agent/global-skills/github/install", {"json": {"url": "https://github.com/a/b", "sha256": "a" * 64}}),
            ]
            for method, url, options in requests:
                with self.subTest(url=url):
                    response = await client.request(method, url, **options)
                    self.assertEqual(response.status_code, 403)

    async def test_store_rejects_personal_invalid_and_duplicate_global_ids(self):
        db = SimpleNamespace(scalar=AsyncMock())
        for records in ([{**record(), "id": "custom-other"}], [{**record(), "id": "global-bad"}], [record(), record()]):
            db.scalar.return_value = SimpleNamespace(value={"schema_version": 1, "scope": "global", "skills": records})
            with self.assertRaises(HTTPException) as caught:
                await global_skill_store(db)
            self.assertEqual(caught.exception.status_code, 409)

    async def test_first_creation_collision_rolls_back_instead_of_overwriting(self):
        db = SimpleNamespace(add=lambda item: None, commit=AsyncMock(side_effect=IntegrityError("unique", {}, Exception())), rollback=AsyncMock())
        with patch("app.core.system._system_audit", AsyncMock()):
            with self.assertRaises(HTTPException) as caught:
                await save_global_skills(None, [record()], ADMIN, db)
        self.assertEqual(caught.exception.status_code, 409)
        db.rollback.assert_awaited_once()

    async def test_global_install_idempotency_never_overwrites_edited_or_changed_content(self):
        source = "https://github.com/a/b/blob/main/SKILL.md"
        existing = {**record(), "source": source, "sha256": "a" * 64}
        with patch("app.global_agent_skills.global_skill_store", AsyncMock(return_value=(object(), [existing]))), \
                patch("app.global_agent_skills.save_global_skills", AsyncMock()) as save:
            same = await add_global_skill(PAYLOAD, ADMIN, object(), source=source, digest="a" * 64)
            self.assertEqual(same["id"], GLOBAL_ID)
            existing["instruction"] += " 本地修改。"
            with self.assertRaises(HTTPException):
                await add_global_skill(PAYLOAD, ADMIN, object(), source=source, digest="a" * 64)
            with self.assertRaises(HTTPException):
                await add_global_skill(PAYLOAD, ADMIN, object(), source=source, digest="b" * 64)
            save.assert_not_awaited()

    async def test_admin_crud_global_id_and_personal_records_are_not_modified(self):
        from app.areas.agent_admin.skills import GlobalSkillInput, GlobalSkillUpdate, create_global_skill, update_global_skill, delete_global_skill
        stored = []

        async def save(item, records, identity, db):
            stored[:] = records

        with patch("app.global_agent_skills.global_skill_store", AsyncMock(return_value=(object(), []))), \
                patch("app.global_agent_skills.save_global_skills", side_effect=save):
            result = await create_global_skill(GlobalSkillInput(**PAYLOAD), ADMIN, object())
        self.assertTrue(result["id"].startswith("global-"))
        self.assertEqual(result["scope"], "global")
        with patch("app.areas.agent_admin.skills.global_skill_store", AsyncMock(return_value=(object(), stored))), \
                patch("app.areas.agent_admin.skills.save_global_skills", side_effect=save):
            updated = await update_global_skill(result["id"], GlobalSkillUpdate(enabled=False), ADMIN, object())
            self.assertFalse(updated["enabled"])
            await delete_global_skill(result["id"], ADMIN, object())
            self.assertEqual(stored, [])

    async def test_runtime_merges_only_enabled_global_and_current_personal_and_enforces_selection(self):
        from app.core.permissions import _agent_skill_catalog_for_identity, _agent_skill_for_identity
        shared, personal = record(), normalize_custom_skill(PAYLOAD)
        with patch("app.global_agent_skills.global_skill_store", AsyncMock(return_value=(None, [shared]))), \
                patch("app.system_agent_skills.active_system_skills", AsyncMock(return_value=[])), \
                patch("app.core.documents._user_agent_skill_store", AsyncMock(return_value=(None, [personal]))):
            catalog = await _agent_skill_catalog_for_identity(USER, object())
            self.assertIn(GLOBAL_ID, {item["id"] for item in catalog})
            self.assertIn(personal["id"], {item["id"] for item in catalog})
            selected = await _agent_skill_for_identity(GLOBAL_ID, USER, object())
            self.assertIn("不得覆盖系统权限", selected.instruction)
            shared["enabled"] = False
            with self.assertRaises(HTTPException) as disabled:
                await _agent_skill_for_identity(GLOBAL_ID, ADMIN, object())
            self.assertEqual(disabled.exception.status_code, 409)
            catalog = await _agent_skill_catalog_for_identity(USER, object())
            self.assertNotIn(GLOBAL_ID, {item["id"] for item in catalog})
        with patch("app.core.documents._user_agent_skill_store", AsyncMock(return_value=(None, []))):
            with self.assertRaises(HTTPException) as missing:
                await _agent_skill_for_identity(personal["id"], {"username": "other"}, object())
            self.assertEqual(missing.exception.status_code, 404)

    async def test_personal_definition_does_not_fall_through_to_global_or_other_users(self):
        from app.areas.agent_admin.skills import personal_definition, personal_skills
        personal = normalize_custom_skill(PAYLOAD)
        with patch("app.core.documents._user_agent_skill_store", AsyncMock(return_value=(None, [personal]))):
            own = await personal_skills(USER, object())
            self.assertEqual([item["id"] for item in own["items"]], [personal["id"]])
            with self.assertRaises(HTTPException):
                await personal_definition(GLOBAL_ID, USER, object())
        with patch("app.core.documents._user_agent_skill_store", AsyncMock(return_value=(None, []))):
            with self.assertRaises(HTTPException):
                await personal_definition(personal["id"], {"username": "other"}, object())


class DefinitionTest(unittest.TestCase):
    def test_generic_configuration_cannot_write_global_store(self):
        from app.core.system import _validate_system_config
        with self.assertRaises(HTTPException) as caught:
            _validate_system_config(GLOBAL_SKILL_CONFIG_KEY, {"skills": []})
        self.assertEqual(caught.exception.status_code, 409)
        with self.assertRaises(HTTPException):
            require_global_admin({**USER, "_page_menu_capability": True})

    def test_download_is_saved_definition_and_roundtrips_without_claiming_original_hash(self):
        personal = normalize_custom_skill(PAYLOAD)
        definition = skill_definition(personal, "personal")
        self.assertNotIn("import_sha256", definition)
        self.assertEqual(definition["definition_sha256"], hashlib.sha256(definition["content"].encode()).hexdigest())
        uploaded = parse_uploaded_skill("SKILL.md", definition["content"].encode())
        for key in ("name", "description", "instruction", "category", "quick_prompts"):
            self.assertEqual(uploaded[key], personal[key])
        personal["sha256"] = "a" * 64
        definition = skill_definition(personal, "personal")
        self.assertEqual(definition["import_sha256"], "a" * 64)
        self.assertNotEqual(definition["definition_sha256"], definition["import_sha256"])
        personal["id"] = 'custom-unsafe"\r\nInjected: yes'
        self.assertNotIn("\r", skill_definition(personal, "personal")["filename"])
        self.assertEqual(custom_skill_public(personal)["scope"], "personal")


if __name__ == "__main__":
    unittest.main()
