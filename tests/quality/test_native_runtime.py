"""隔离验证原生运行包激活、启动命令与 API/静态资源健康。"""

import hashlib
import json
import os
import re
import sys
import tempfile
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
sys.path.insert(0, str(SCRIPTS))

import native_runtime
import runtime_package


class NativeRuntimeTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="oa-test-native-runtime-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.package, self.manifest = self.make_package("old", "a" * 40)

    def make_package(self, name: str, commit: str) -> tuple[Path, dict]:
        package = self.root / name
        files = {
            "api/app/main.py": b"app = None\n",
            "api/requirements.txt": b"fastapi==0.136.3\n",
            "api/requirements.lock": b"fastapi==0.136.3\n",
            "web/index.html": b'<html><script src="/assets/app.js"></script></html>',
            "web/assets/app.js": b"window.app = true;\n",
            "web/build-info.json": json.dumps({"version": "1.2.3", "source_commit": commit}).encode(),
        }
        for resource in runtime_package.API_RESOURCE_FILES:
            files[f"api/app/{resource}"] = b"{}\n"
        for relative, content in files.items():
            path = package / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
        manifest = {
            "format": 1,
            "version": "1.2.3",
            "source_commit": commit,
            "files": {relative: hashlib.sha256(content).hexdigest() for relative, content in files.items()},
        }
        (package / "runtime-manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        return package, manifest

    def service(self, responses: dict[str, bytes]) -> tuple[ThreadingHTTPServer, list[str]]:
        paths = []

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                paths.append(self.path)
                payload = responses.get(self.path)
                self.send_response(200 if payload is not None else 404)
                self.end_headers()
                if payload is not None:
                    self.wfile.write(payload)

            def log_message(self, *_args):
                pass

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(thread.join)
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        return server, paths

    def test_verified_package_rejects_checkout_and_tampering(self):
        self.assertEqual(native_runtime.checked_package(self.package)[1], self.manifest)
        (self.package / "web/assets/app.js").write_bytes(b"tampered")
        with self.assertRaisesRegex(ValueError, "哈希不一致"):
            native_runtime.checked_package(self.package)
        (self.package / "web/assets/app.js").write_bytes(b"window.app = true;\n")
        (self.root / ".git").mkdir()
        with self.assertRaisesRegex(RuntimeError, "Git checkout"):
            native_runtime.checked_package(self.package)

    def test_health_checks_api_proxy_and_exact_static_bytes(self):
        api, api_paths = self.service({"/health": b'{"status":"ok"}'})
        web_responses = {"/health": b'{"status":"ok"}'}
        for relative in ("index.html", "assets/app.js", "build-info.json"):
            web_responses[f"/{relative}"] = (self.package / "web" / relative).read_bytes()
        web, web_paths = self.service(web_responses)
        values = {"OA_NATIVE_API_HOST": "127.0.0.1", "OA_NATIVE_API_PORT": str(api.server_port),
                  "OA_NATIVE_WEB_HOST": "127.0.0.1", "OA_NATIVE_WEB_PORT": str(web.server_port)}
        with patch.dict(os.environ, values):
            self.assertEqual(native_runtime.health(self.package, self.manifest)["assets"], 1)
            self.assertEqual(api_paths, ["/health"])
            self.assertEqual(set(web_paths), set(web_responses))
            web_responses["/assets/app.js"] = b"wrong version"
            with self.assertRaisesRegex(RuntimeError, "运行包不一致"):
                native_runtime.health(self.package, self.manifest)

    def test_activation_restarts_verified_package_and_rolls_back_failure(self):
        candidate, candidate_manifest = self.make_package("candidate", "b" * 40)
        current = self.root / "current"
        current.symlink_to(self.package, target_is_directory=True)
        def switch_link(link: Path, package: Path) -> None:
            link.unlink()
            link.symlink_to(package, target_is_directory=True)

        with patch.dict(os.environ, {"OA_NATIVE_RUNTIME_CURRENT": str(current)}), patch.object(
            native_runtime, "atomic_link", side_effect=switch_link
        ), patch.object(
            native_runtime, "services"
        ) as services, patch.object(
            native_runtime, "await_health", return_value={"status": "passed"}
        ) as await_health:
            self.assertEqual(native_runtime.activate(candidate, current, candidate_manifest["source_commit"]),
                             {"status": "passed"})
            self.assertEqual(current.resolve(), candidate.resolve())
            services.assert_called_once_with("restart")
            await_health.assert_called_once_with(candidate.resolve(), candidate_manifest)
        with patch.dict(os.environ, {"OA_NATIVE_RUNTIME_CURRENT": str(current)}), patch.object(
            native_runtime, "atomic_link", side_effect=switch_link
        ), patch.object(
            native_runtime, "services"
        ) as services, patch.object(
            native_runtime, "await_health", side_effect=RuntimeError("健康检查失败")
        ):
            with self.assertRaisesRegex(RuntimeError, "已恢复旧版本"):
                native_runtime.activate(self.package, current, self.manifest["source_commit"])
            self.assertEqual(current.resolve(), candidate.resolve())
            self.assertEqual([call.args for call in services.call_args_list], [("restart",), ("restart",)])
        with patch.dict(os.environ, {"OA_NATIVE_RUNTIME_CURRENT": str(current)}), patch.object(
            native_runtime, "services"
        ) as services:
            with self.assertRaisesRegex(RuntimeError, "预期发布提交"):
                native_runtime.activate(self.package, current, "c" * 40)
            services.assert_not_called()

    def test_activation_rejects_configuration_mismatch(self):
        candidate, manifest = self.make_package("candidate", "b" * 40)
        current = self.root / "current"
        with (
            patch.dict(os.environ, {"OA_NATIVE_RUNTIME_CURRENT": str(self.root / "different")}),
            self.assertRaisesRegex(RuntimeError, "服务配置"),
        ):
            native_runtime.activate(candidate, current, manifest["source_commit"])
        self.assertFalse(current.exists())

    def test_environment_file_uses_strict_shared_values(self):
        config = self.root / "native-runtime.env"
        config.write_text("# 测试配置\nOA_NATIVE_RUNTIME_CURRENT=/srv/sunhold/current\nOA_NATIVE_API_PORT=8001\n", encoding="utf-8")
        config.chmod(0o600)
        with patch.dict(os.environ, {}):
            native_runtime.load_environment_file(config)
            self.assertEqual(os.environ["OA_NATIVE_API_PORT"], "8001")
        config.write_text("OA_NATIVE_API_PORT=\"8001\"\n", encoding="utf-8")
        with self.assertRaisesRegex(RuntimeError, "格式无效"):
            native_runtime.load_environment_file(config)

    @unittest.skipIf(os.name == "nt", "Windows 不支持覆盖现有目录符号链接；原子替换须在 Linux CI 验证")
    def test_atomic_link_replaces_existing_link(self):
        candidate, _ = self.make_package("candidate", "b" * 40)
        current = self.root / "current"
        current.symlink_to(self.package, target_is_directory=True)
        native_runtime.atomic_link(current, candidate)
        self.assertEqual(current.resolve(), candidate.resolve())
        self.assertEqual(list(self.root.glob("current.next-*")), [])

    def test_api_and_web_launch_use_package_without_reload(self):
        current = self.root / "current"
        current.symlink_to(self.package, target_is_directory=True)
        upload = self.root / "uploads"
        upload.mkdir()
        state = self.root / "web-state"
        state.mkdir()
        nginx = self.root / "nginx"
        nginx.write_bytes(b"test executable placeholder")
        mime = self.root / "mime.types"
        mime.write_text("types {}\n", encoding="utf-8")
        values = {
            "OA_NATIVE_RUNTIME_CURRENT": str(current), "APP_ENV": "production",
            "DATABASE_URL": "postgresql+asyncpg://test@localhost/test", "SECRET_KEY": "test-only",
            "INITIAL_ADMIN_PASSWORD": "test-only", "UPLOAD_ROOT": str(upload),
            "OA_NATIVE_PYTHON": sys.executable, "OA_NATIVE_API_HOST": "127.0.0.1",
            "OA_NATIVE_API_PORT": "19001", "OA_NATIVE_WEB_HOST": "127.0.0.1",
            "OA_NATIVE_WEB_PORT": "19002", "OA_NATIVE_WEB_STATE_DIR": str(state),
            "OA_NATIVE_NGINX": str(nginx), "OA_NATIVE_MIME_TYPES": str(mime),
        }
        with patch.dict(os.environ, values), patch.object(native_runtime.os, "chdir") as chdir, patch.object(
            native_runtime.os, "execve", side_effect=RuntimeError("命令已截获")
        ) as execute:
            with self.assertRaisesRegex(RuntimeError, "命令已截获"):
                native_runtime.start_api()
            command = execute.call_args.args[1]
            self.assertNotIn("--reload", command)
            self.assertEqual(command[2:4], ["uvicorn", "app.main:app"])
            self.assertEqual(execute.call_args.args[2]["PYTHONPATH"], str(self.package.resolve() / "api"))
            chdir.assert_called_once_with(self.package.resolve() / "api")
        with patch.dict(os.environ, values), patch.object(
            native_runtime.subprocess, "run"
        ) as nginx_check, patch.object(native_runtime.os, "execve", side_effect=RuntimeError("命令已截获")) as execute:
            with self.assertRaisesRegex(RuntimeError, "命令已截获"):
                native_runtime.start_web()
            nginx_check.assert_called_once()
            self.assertEqual(nginx_check.call_args.args[0][1], "-t")
            self.assertIn("daemon off;", execute.call_args.args[1])
            config = (state / "nginx.conf").read_text(encoding="utf-8")
            self.assertIn(str((self.package.resolve() / "web").as_posix()), config)
            self.assertIn("location /api/", config)
            self.assertIn("location = /health", config)
            import_location = re.search(
                r"location = /api/v1/finance/incoming-payments/import \{([^}]*)\}", config, re.DOTALL
            )
            self.assertIsNotNone(import_location)
            self.assertEqual(config.count("location = /api/v1/finance/incoming-payments/import"), 1)
            for directive in (
                "client_max_body_size 101m;", "client_body_timeout 600s;",
                "proxy_connect_timeout 5s;", "proxy_read_timeout 600s;", "proxy_send_timeout 600s;",
                "proxy_pass http://127.0.0.1:19001;",
            ):
                self.assertIn(directive, import_location.group(1))
            api_location = re.search(r"location /api/ \{([^}]*)\}", config, re.DOTALL)
            self.assertIsNotNone(api_location)
            self.assertIn("proxy_read_timeout 120s;", api_location.group(1))
            self.assertIn("proxy_send_timeout 120s;", api_location.group(1))
            self.assertIn("client_max_body_size 21m;", config)
            self.assertTrue((state / "client-body").is_dir())
            self.assertTrue((state / "proxy").is_dir())


if __name__ == "__main__":
    unittest.main()
