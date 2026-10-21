"""原生插件技能完整快照、启停与资源执行边界。"""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException

from app.harness_agent import native_plugin_skills as native
from app.harness_agent.bundles import read_resource
from app.harness_agent.skills import WorkspaceTools


class NativePluginSkillsTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="oa-plugin-skill-test-")
        self.root = Path(self.temporary.name)
        self.home = self.root / "revision"
        self.skill = self.home / "profiles/sdk/node_modules/@isolated/plugin/skills/archify"
        (self.skill / "bin").mkdir(parents=True)
        (self.skill / "SKILL.md").write_text("---\nname: archify\ndescription: 隔离技能\n---\n执行 doctor。", encoding="utf-8")
        (self.skill / "bin/archify.mjs").write_text("console.log('isolated');", encoding="utf-8")
        self.active = patch("app.harness_agent.plugins.current", return_value=("isolated-revision", self.home))
        self.packages = patch.object(native, "installed_packages", return_value=[{"name": "@isolated/plugin", "enabled": True, "error": ""}])
        self.store = patch("app.harness_agent.bundles.storage_root", return_value=self.root / "snapshots")
        for context in (self.active, self.packages, self.store):
            context.start()
            self.addCleanup(context.stop)
        native._load.cache_clear()

    def tearDown(self):
        native._load.cache_clear()
        self.temporary.cleanup()

    def test_installed_skill_contains_the_complete_verified_script(self):
        skills = native.definitions()
        self.assertEqual(len(skills), 1)
        self.assertEqual(skills[0].name, "archify")
        self.assertEqual(read_resource(skills[0].bundle, "bin/archify.mjs"), b"console.log('isolated');")
        self.assertEqual(native.definitions()[0].bundle, skills[0].bundle)

    async def test_native_skill_uses_the_existing_script_executor(self):
        tools = WorkspaceTools(AsyncMock(), {"username": "isolated-account"}, None)
        with patch("app.harness_agent.skills.definitions", AsyncMock(return_value=[])), \
             patch("app.harness_agent.script_runtime.run_script", AsyncMock(return_value={"isError": False})) as execute:
            result = await tools.execute("harness_run_skill_script", {"name": "archify", "path": "bin/archify.mjs", "args": ["doctor"]})
        self.assertFalse(result["isError"])
        self.assertEqual(execute.call_args.args[0].name, "archify")
        self.assertEqual(execute.call_args.args[1:], ("bin/archify.mjs", ["doctor"]))

    async def test_disabled_plugins_are_unavailable_even_after_the_skill_was_loaded(self):
        native.definitions()
        tools = WorkspaceTools(AsyncMock(), {"username": "isolated-account"}, None)
        with patch.object(native, "installed_packages", return_value=[{"name": "@isolated/plugin", "enabled": False, "error": ""}]), \
             patch("app.harness_agent.skills.definitions", AsyncMock(return_value=[])), \
             patch("app.harness_agent.script_runtime.run_script", AsyncMock()) as execute:
            with self.assertRaises(HTTPException) as failure:
                await tools.execute("harness_run_skill_script", {"name": "archify", "path": "bin/archify.mjs", "args": ["doctor"]})
        self.assertEqual(failure.exception.status_code, 404)
        execute.assert_not_awaited()

    def test_malformed_skill_metadata_and_missing_resources_fail_explicitly(self):
        (self.skill / "SKILL.md").write_text("missing frontmatter", encoding="utf-8")
        with self.assertRaises(HTTPException) as failure:
            native.definitions()
        self.assertEqual(failure.exception.status_code, 409)


if __name__ == "__main__":
    unittest.main()
