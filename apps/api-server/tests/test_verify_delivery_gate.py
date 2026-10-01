"""交付检查的源码提交号与运行端口解析失败路径。"""

import asyncio
import shutil
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPOSITORY_ROOT / "scripts" / "verify-delivery.ps1"
POWERSHELL = shutil.which("pwsh") or shutil.which("powershell.exe")


@unittest.skipUnless(POWERSHELL, "需要 PowerShell 执行交付门禁函数")
class VerifyDeliveryGateTests(unittest.TestCase):
    def run_script(self, statement: str) -> subprocess.CompletedProcess[bytes]:
        quoted = str(SCRIPT).replace("'", "''")
        command = f". '{quoted}'; {statement}"
        return subprocess.run(
            [POWERSHELL, "-NoProfile", "-Command", command],
            cwd=REPOSITORY_ROOT, capture_output=True, timeout=30, check=False,
        )

    def test_source_commit_requires_full_lowercase_sha(self) -> None:
        valid = self.run_script("Assert-FullSourceCommit -Commit ('a' * 40); 'VALID'")
        self.assertEqual(valid.returncode, 0, valid.stderr.decode("utf-8", errors="strict"))
        self.assertIn("VALID", valid.stdout.decode("utf-8", errors="strict"))
        for candidate in ("abc123", "A" * 40):
            with self.subTest(candidate=candidate):
                rejected = self.run_script(f"Assert-FullSourceCommit -Commit '{candidate}'")
                self.assertNotEqual(rejected.returncode, 0)

    def test_web_health_uses_published_runtime_port(self) -> None:
        success = self.run_script(
            "$web = [pscustomobject]@{Publishers = @([pscustomobject]@{TargetPort=80; Protocol='tcp'; PublishedPort=15192})}; "
            "Get-WebHealthEndpoint -WebService $web"
        )
        self.assertEqual(success.returncode, 0, success.stderr.decode("utf-8", errors="strict"))
        self.assertIn("http://127.0.0.1:15192/health", success.stdout.decode("utf-8", errors="strict"))
        rejected = self.run_script("$web = [pscustomobject]@{Publishers = @()}; Get-WebHealthEndpoint -WebService $web")
        self.assertNotEqual(rejected.returncode, 0)


class DeliveryLifecycleSafetyTests(unittest.TestCase):
    def test_actual_lifecycle_guard_rejects_unsafe_production_settings(self) -> None:
        from app.core import lifecycle
        from fastapi import FastAPI

        async def check() -> None:
            with patch.object(lifecycle.settings, "app_env", "production"):
                for secret, password, expected in (
                    ("weak", "StrongPassword123!", "SECRET_KEY"),
                    ("s" * 64, "weak", "INITIAL_ADMIN_PASSWORD"),
                ):
                    with (
                        patch.object(lifecycle.settings, "secret_key", secret),
                        patch.object(lifecycle.settings, "initial_admin_password", password),
                        self.assertRaisesRegex(RuntimeError, expected),
                    ):
                        async with lifecycle.lifespan(FastAPI()):
                            pass
                marker = RuntimeError("安全检查已通过，阻止进入数据库迁移")
                with (
                    patch.object(lifecycle.settings, "secret_key", "s" * 64),
                    patch.object(lifecycle.settings, "initial_admin_password", "StrongPassword123!"),
                    patch.object(lifecycle, "engine") as guarded_engine,
                ):
                    guarded_engine.begin.side_effect = marker
                    with self.assertRaises(RuntimeError) as raised:
                        async with lifecycle.lifespan(FastAPI()):
                            pass
                    self.assertIs(raised.exception, marker)

        asyncio.run(check())
