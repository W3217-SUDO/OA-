"""运行包边界、哈希及构建新鲜度的独立回归。"""

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[2] / "scripts/runtime_package.py"
SPEC = importlib.util.spec_from_file_location("runtime_package", SCRIPT)
runtime_package = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runtime_package)


class RuntimePackageTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="oa-test-runtime-package-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.repository = self.root / "source"
        self.frontend = self.repository / "apps/admin-web"
        self.api = self.repository / "apps/api-server"
        (self.api / "app").mkdir(parents=True)
        (self.frontend / "src").mkdir(parents=True)
        (self.frontend / "dist").mkdir()
        (self.frontend / "scripts").mkdir()
        (self.frontend / "scripts/build-production.mjs").write_text("// 构建入口\n", encoding="utf-8")
        (self.api / "app/main.py").write_text("app = None\n", encoding="utf-8")
        (self.api / "requirements.txt").write_text("fastapi==0.116.1\n", encoding="utf-8")
        (self.api / "requirements.lock").write_text("fastapi==0.136.3\n", encoding="utf-8")
        for relative in runtime_package.API_RESOURCE_FILES:
            path = self.api / "app" / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("{}\n", encoding="utf-8")
        (self.frontend / "package.json").write_text('{"version":"1.2.3"}', encoding="utf-8")
        (self.frontend / "src/main.ts").write_text("export const value = 1;\n", encoding="utf-8")
        (self.frontend / "dist/index.html").write_text("<html></html>", encoding="utf-8")
        self.output = self.root / "runtime"
        self.mark_build()
        self.commit = patch.object(runtime_package.subprocess, "check_output", return_value="abc123\n")
        self.commit.start()
        self.addCleanup(self.commit.stop)

    def mark_build(self):
        info = {"format":1, "version":"1.2.3", "source_commit":"abc123",
                "source_files":runtime_package.frontend_inputs(self.frontend)}
        (self.frontend / "dist/build-info.json").write_text(json.dumps(info), encoding="utf-8")

    def test_runtime_allowlist_and_digest_roundtrip(self):
        tests = self.api / "tests"
        tests.mkdir()
        (tests / "example_test.py").write_text("raise RuntimeError\n", encoding="utf-8")
        manifest = runtime_package.build(self.repository, self.output)
        self.assertEqual(manifest, runtime_package.verify(self.output))
        self.assertFalse((self.output / "api/tests").exists())
        self.assertEqual(manifest["files"]["api/app/main.py"], runtime_package.digest(self.api / "app/main.py"))

    def test_stale_source_build_is_rejected_before_output(self):
        (self.frontend / "src/main.ts").write_text("export const value = 2;\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "产物与当前源码不一致"):
            runtime_package.build(self.repository, self.output)
        self.assertFalse(self.output.exists())

    def test_source_testing_file_is_rejected(self):
        (self.api / "app/test_debug.py").write_text("pass\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "测试或临时文件"):
            runtime_package.build(self.repository, self.output)
        self.assertFalse(self.output.exists())

    def test_tampered_file_and_extra_secret_are_rejected(self):
        runtime_package.build(self.repository, self.output)
        main = self.output / "api/app/main.py"
        original = main.read_bytes()
        main.write_text("changed\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "哈希不一致"):
            runtime_package.verify(self.output)
        main.write_bytes(original)
        (self.output / "api/.env").write_text("SECRET_KEY=private\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "凭据路径"):
            runtime_package.verify(self.output)

    def test_required_resource_is_rejected_even_with_forged_manifest(self):
        runtime_package.build(self.repository, self.output)
        relative = "api/app/legacy_schema_manifest.json"
        (self.output / relative).unlink()
        manifest = json.loads((self.output / "runtime-manifest.json").read_text(encoding="utf-8"))
        del manifest["files"][relative]
        (self.output / "runtime-manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "缺少必需"):
            runtime_package.verify(self.output)

    def test_existing_and_source_nested_outputs_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "源码目录之外"):
            runtime_package.build(self.repository, self.repository / "runtime")
        self.output.mkdir()
        with self.assertRaises(FileExistsError):
            runtime_package.build(self.repository, self.output)


if __name__ == "__main__":
    unittest.main()
