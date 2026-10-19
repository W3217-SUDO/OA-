import unittest
from unittest.mock import AsyncMock, patch

import httpx
from fastapi import FastAPI, HTTPException
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.agent_skills import AGENT_SKILLS, GENERAL_SKILL, parse_skill_message, public_skill_catalog
from app.areas.agent_admin.system_skills import SystemSkillDeleteInput, router
from app.database import Base, get_db
from app.models import BusinessRecord, SystemConfig, WorkflowEvent
from app.security import current_identity
from app.system_agent_skills import (
    SYSTEM_SKILL_CONFIG_KEY, active_system_skills, delete_system_skill, system_skill_detail,
)

ADMIN = {"username": "admin", "role": "admin"}
USER = {"username": "employee", "role": "user", "_actual_user_id": 1}


class AgentSkillRegistryContractTest(unittest.TestCase):
    def test_official_github_office_skills_are_registered(self):
        sources = {item["source"] for item in public_skill_catalog()}
        self.assertTrue({
            "openai/skills:pdf",
            "openai/skills:jupyter-notebook",
            "openai/skills:screenshot",
            "openai/skills:speech",
            "openai/skills:transcribe",
            "openai/skills:security-best-practices",
        }.issubset(sources))
        self.assertEqual(len(public_skill_catalog()), len(AGENT_SKILLS))

    def test_skill_marker_is_parsed_and_removed_from_visible_message(self):
        skill, message = parse_skill_message("[[skill:pdf-review]]\n审阅材料")
        self.assertEqual(skill.id, "pdf-review")
        self.assertEqual(message, "审阅材料")
        selected, untouched = parse_skill_message("普通问题")
        self.assertIsNone(selected)
        self.assertEqual(untouched, "普通问题")

    def test_screenshot_skill_is_available_while_audio_skills_explain_their_boundary(self):
        catalog = {item["id"]: item for item in public_skill_catalog()}
        self.assertTrue(catalog["screenshot-evidence"]["available"])
        self.assertFalse(catalog["screenshot-evidence"]["unavailable_reason"])
        for skill_id in ("speech-output", "meeting-transcription"):
            self.assertFalse(catalog[skill_id]["available"])
            self.assertTrue(catalog[skill_id]["unavailable_reason"])


class SystemSkillLifecycleTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        async with self.engine.begin() as connection:
            await connection.run_sync(lambda sync: Base.metadata.create_all(sync, tables=[
                SystemConfig.__table__, BusinessRecord.__table__, WorkflowEvent.__table__,
            ]))
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        self.session_patch = patch("app.database.SessionLocal", self.sessions)
        self.session_patch.start()

    async def asyncTearDown(self):
        self.session_patch.stop()
        await self.engine.dispose()

    async def delete(self, skill_id):
        async with self.sessions() as db:
            detail = await system_skill_detail(skill_id, ADMIN, db)
            return await delete_system_skill(skill_id, SystemSkillDeleteInput(
                confirm=True, revision=detail["revision"], definition_sha256=detail["definition_sha256"]), ADMIN, db)

    async def test_details_are_actual_declarations_not_vendor_packages_or_local_files(self):
        async with self.sessions() as db:
            for skill in AGENT_SKILLS:
                detail = await system_skill_detail(skill.id, ADMIN, db)
                self.assertEqual(detail["instruction"], skill.instruction)
                self.assertIn(skill.instruction, detail["content"])
                self.assertEqual(detail["quick_prompts"], list(skill.quick_prompts))
                self.assertEqual(detail["source"], skill.source)
                self.assertEqual(detail["resources"], [])
                self.assertEqual(detail["content_origin"], "runtime_declaration")
                self.assertTrue(detail["can_delete"])
                self.assertEqual(detail["scope"], "system")
                self.assertNotIn("\\", detail["filename"])
                self.assertNotIn("/", detail["filename"])
                import hashlib
                self.assertEqual(detail["definition_sha256"], hashlib.sha256(detail["content"].encode()).hexdigest())

    async def test_every_system_skill_including_default_can_be_persistently_removed(self):
        for skill in AGENT_SKILLS:
            result = await self.delete(skill.id)
            self.assertEqual(result["deletion_mode"], "registry_deactivation")
            async with self.sessions() as db:
                self.assertNotIn(skill.id, {entry["id"] for entry in await active_system_skills(db)})
                with self.assertRaises(HTTPException) as removed:
                    await system_skill_detail(skill.id, ADMIN, db)
                self.assertEqual(removed.exception.status_code, 409)
        async with self.sessions() as db:
            self.assertEqual(await active_system_skills(db), [])
            self.assertEqual(await db.scalar(select(func.count()).select_from(WorkflowEvent)), len(AGENT_SKILLS))
            self.assertEqual(await db.scalar(select(func.count()).select_from(BusinessRecord)
                                            .where(BusinessRecord.module == "system_audit")), len(AGENT_SKILLS))
        self.assertEqual(len(AGENT_SKILLS), 10, "注销不修改不可变声明")

    async def test_stale_revision_or_definition_cannot_delete_another_skill(self):
        async with self.sessions() as db:
            stale = await system_skill_detail("pdf-review", ADMIN, db)
        await self.delete("general-office")
        async with self.sessions() as db:
            for revision, digest in ((stale["revision"], stale["definition_sha256"]), (1, "0" * 64)):
                with self.assertRaises(HTTPException) as changed:
                    await delete_system_skill("pdf-review", SystemSkillDeleteInput(
                        confirm=True, revision=revision, definition_sha256=digest), ADMIN, db)
                self.assertEqual(changed.exception.status_code, 409)
            self.assertIn("pdf-review", {entry["id"] for entry in await active_system_skills(db)})

    async def test_concurrent_registry_update_is_blocked_at_revision_cas(self):
        from sqlalchemy.dialects import postgresql
        await self.delete("general-office")
        async with self.sessions() as db:
            detail = await system_skill_detail("pdf-review", ADMIN, db)
            execute = db.execute

            async def race(statement):
                sql = str(statement.compile(dialect=postgresql.dialect()))
                self.assertIn("->>", sql)
                self.assertIn("INTEGER", sql)
                async with self.sessions() as other:
                    await other.execute(update(SystemConfig).where(SystemConfig.key == SYSTEM_SKILL_CONFIG_KEY).values(
                        value={"schema_version": 1, "revision": 2, "deleted_ids": ["general-office", "data-analysis"]}))
                    await other.commit()
                return await execute(statement)

            with patch.object(db, "execute", side_effect=race):
                with self.assertRaises(HTTPException) as conflict:
                    await delete_system_skill("pdf-review", SystemSkillDeleteInput(confirm=True,
                        revision=detail["revision"], definition_sha256=detail["definition_sha256"]), ADMIN, db)
                self.assertEqual(conflict.exception.status_code, 409)
        async with self.sessions() as db:
            ids = {item["id"] for item in await active_system_skills(db)}
            self.assertIn("pdf-review", ids)
            self.assertNotIn("data-analysis", ids)
            self.assertEqual(await db.scalar(select(func.count()).select_from(WorkflowEvent)), 1)

    async def test_routes_require_management_confirmation_and_are_not_model_tools(self):
        app = FastAPI()
        app.include_router(router)
        async def session():
            async with self.sessions() as db:
                yield db
        app.dependency_overrides[get_db] = session
        identity = USER
        app.dependency_overrides[current_identity] = lambda: identity
        path = "/api/v1/agent/system-skills/general-office"
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://isolated") as client:
            self.assertEqual((await client.get(path + "/definition")).status_code, 403)
            body = {"confirm": True, "revision": 0, "definition_sha256": "0" * 64}
            self.assertEqual((await client.request("DELETE", path, json=body)).status_code, 403)
            identity = ADMIN
            detail = (await client.get(path + "/definition")).json()
            body["definition_sha256"] = detail["definition_sha256"]
            self.assertEqual((await client.request("DELETE", path, json={**body, "confirm": False})).status_code, 422)
            self.assertEqual((await client.request("DELETE", path, json={"definition_sha256": body["definition_sha256"]})).status_code, 422)
            self.assertEqual((await client.request("DELETE", path, json=body)).status_code, 200)
            self.assertEqual((await client.get("/api/v1/agent/system-skills/missing/definition")).status_code, 404)
        from app.agent_mcp.semantic_metadata import exclusion_reasons
        from fastapi.routing import APIRoute
        for route in router.routes:
            if isinstance(route, APIRoute):
                self.assertTrue(exclusion_reasons(route))

    async def test_generic_config_cannot_restore_registry_and_malformed_registry_fails(self):
        from app.core.system import _validate_system_config
        with self.assertRaises(HTTPException):
            _validate_system_config(SYSTEM_SKILL_CONFIG_KEY, {"deleted_ids": []})
        async with self.sessions() as db:
            db.add(SystemConfig(key=SYSTEM_SKILL_CONFIG_KEY, label="CODEX-invalid", value={}))
            await db.commit()
            with self.assertRaises(HTTPException) as malformed:
                await active_system_skills(db)
            self.assertEqual(malformed.exception.status_code, 409)

    async def test_catalog_resolver_and_legacy_markers_reject_deleted_but_allow_plain_mode(self):
        from app.core.permissions import _agent_message_skill_for_identity, _agent_skill_catalog_for_identity, _agent_skill_for_identity
        from app.global_agent_skills import add_global_skill
        from app.user_agent_skills import normalize_custom_skill
        await self.delete("general-office")
        async with self.sessions() as db:
            shared = await add_global_skill({"name": "CODEX-shared", "description": "隔离技能", "instruction": "仅使用本轮有权限的隔离材料回答"}, ADMIN, db)
            personal = normalize_custom_skill({"name": "CODEX-private", "description": "隔离技能", "instruction": "仅使用个人有权限的隔离材料回答"})
            # 真实注册表和解析器读取同一数据库；其他技能库只替换存储边界。
            with patch("app.core.documents._user_agent_skill_store", AsyncMock(return_value=(None, [personal]))):
                catalog = await _agent_skill_catalog_for_identity(USER, db)
                ids = {item["id"] for item in catalog}
                self.assertNotIn("general-office", ids)
                self.assertIn(shared["id"], ids)
                self.assertIn(personal["id"], ids)
                self.assertEqual((await _agent_skill_for_identity(shared["id"], USER, db)).id, shared["id"])
            for value in (None, "", " "):
                self.assertIsNone(await _agent_skill_for_identity(value, USER, db))
            for selected, message in (("general-office", "问题"), (None, "[[skill:general-office]]\n问题"),
                                      ("pdf-review", "[[skill:general-office]]\n问题")):
                with self.assertRaises(HTTPException) as removed:
                    await _agent_message_skill_for_identity(selected, message, USER, db)
                self.assertEqual(removed.exception.status_code, 409)

    async def test_plain_personal_generation_keeps_base_safety_without_deleted_instruction(self):
        from app.areas.personal_agent import service
        await self.delete("general-office")
        state = {"conversation_id": "CODEX-isolated", "messages": [], "pending_actions": []}
        with patch.object(service, "prepare_materials", AsyncMock(return_value={"case": None, "readings": [], "can_save_document": False})), \
                patch.object(service, "build_context", AsyncMock(return_value={})), \
                patch.object(service, "project_workspace_context", AsyncMock(return_value={})), \
                patch.object(service, "_save_state", AsyncMock()), \
                patch.object(service, "run_memory_pipeline", return_value={"summary": "", "recalled": []}), \
                patch("app.areas.personal_agent.ai_space_service.personal_save_capability", AsyncMock(return_value={"can_save": False, "error": "隔离环境"})), \
                patch.object(service, "request_model", AsyncMock(return_value="真实隔离模型返回")) as model:
            async with self.sessions() as db:
                result = await service._generate_response(USER, db, "普通问题", AsyncMock(), state=state, skill_id=None,
                    attachment_ids=[], case_id=None, document_ids=[], response_mode="fast", on_progress=None)
            self.assertEqual(result["response"], "真实隔离模型返回")
            self.assertEqual(state["messages"][0]["skill_id"], "")
            prompt = model.await_args.args[0][0]["content"]
            self.assertNotIn(GENERAL_SKILL.instruction, prompt)
            self.assertIn("必须等用户点击前端确认", prompt)
            self.assertIn("不能共享或引用其他用户的聊天记录", prompt)

    async def test_deleted_personal_selection_is_blocked_before_state_or_model(self):
        from app.areas.personal_agent import service
        await self.delete("general-office")
        with patch.object(service.conversations, "conversation_operation") as operation, \
                patch.object(service, "request_model", AsyncMock()) as model:
            async with self.sessions() as db:
                for text, skill_id in (("问题", "general-office"), ("[[skill:general-office]]\n问题", None)):
                    with self.assertRaises(HTTPException) as removed:
                        await service.generate_response(USER, db, text, AsyncMock(), skill_id=skill_id)
                    self.assertEqual(removed.exception.status_code, 409)
            operation.assert_not_called()
            model.assert_not_awaited()

    async def test_case_runtime_blocks_deleted_selection_and_cached_override_but_plain_works(self):
        from app.case_agent import CaseAgentRuntime, build_case_model_messages
        await self.delete("general-office")
        runtime = CaseAgentRuntime(enabled=True, database_url="sqlite+aiosqlite:///:memory:")
        await runtime.start()
        try:
            runtime.api_base_url, runtime.api_key, runtime.model = "https://model.invalid", "isolated", "isolated"
            runtime._request_model = AsyncMock(return_value="普通案件回答")
            snapshot = {"case": {"id": 1}}
            for arguments in ({"message": "[[skill:general-office]]\n问题"},
                              {"message": "问题", "skill_override": GENERAL_SKILL}):
                with self.assertRaises(HTTPException) as removed:
                    await runtime.invoke(case_id=1, operator="employee", case_snapshot=snapshot, **arguments)
                self.assertEqual(removed.exception.status_code, 409)
            runtime._request_model.assert_not_awaited()
            with self.assertRaises(HTTPException):
                await runtime._case_assistant_node({"messages": [{"skill_id": "general-office"}],
                    "case_snapshot": snapshot, "skill_override": {"id": "general-office", "instruction": GENERAL_SKILL.instruction}})
            result = await runtime.invoke(case_id=1, operator="employee", message="普通问题", case_snapshot=snapshot)
            self.assertEqual(result["last_response"], "普通案件回答")
            self.assertIsNone(runtime._request_model.await_args.args[2])
            prompt = build_case_model_messages(snapshot, [], None)[0]["content"]
            self.assertNotIn(GENERAL_SKILL.instruction, prompt)
            self.assertIn("任何写操作都必须进入人工审批", prompt)
        finally:
            await runtime.stop()


if __name__ == "__main__":
    unittest.main()
