"""用真实 Docker 构建验证 API 源码的缓存排除规则。"""

import json
import os
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile
import unittest
from uuid import uuid4


DOCKERIGNORE = Path(__file__).resolve().parents[2] / "apps/api-server/.dockerignore"


def docker_command(docker: str, *arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [docker, *arguments], capture_output=True, text=True, encoding="utf-8", check=False, timeout=60,
    )


class ApiDockerContextTest(unittest.TestCase):
    def test_recursive_caches_are_absent_from_copied_app_layer(self):
        docker = shutil.which("docker")
        if docker is None:
            if os.name == "nt":
                self.skipTest("Windows 本机未安装 Docker，Linux CI 必须运行真实镜像检查")
            self.fail("Linux 质量门禁要求 Docker CLI")
        available = docker_command(docker, "info", "--format", "{{.ServerVersion}}")
        if available.returncode or not available.stdout.strip():
            if os.name == "nt":
                self.skipTest("Windows 本机 Docker 守护进程不可用，Linux CI 必须运行真实镜像检查")
            self.fail(f"Linux 质量门禁要求 Docker 守护进程：{available.stderr}")

        marker = uuid4().hex
        tag = f"oa-dockerignore-probe:{marker}"
        label = "oa.dockerignore.probe"
        with tempfile.TemporaryDirectory(prefix="oa-test-api-docker-context-") as temporary:
            scope = Path(temporary)
            context = scope / "context"
            context.mkdir()
            shutil.copyfile(DOCKERIGNORE, context / ".dockerignore")
            (context / "Dockerfile").write_text("FROM scratch\nCOPY app /app\n", encoding="utf-8")
            retained = ("app/keep.py", "app/nested/keep.py")
            excluded = (
                "app/__pycache__/first.cpython-312.pyc",
                "app/nested/__pycache__/second.cpython-312.pyc",
                "app/nested/generated.pyc",
                "app/nested/generated.pyo",
                "app/nested/generated.pyd",
                "app/nested/.pytest_cache/cache.json",
                "app/nested/.mypy_cache/cache.json",
            )
            for relative in (*retained, *excluded):
                target = context / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(relative, encoding="utf-8")

            image_created = False
            try:
                build = docker_command(
                    docker, "build", "--no-cache", "--tag", tag,
                    "--label", f"{label}={marker}", str(context),
                )
                self.assertEqual(build.returncode, 0, build.stdout + build.stderr)
                image_created = True
                archive_path = scope / "image.tar"
                saved = docker_command(docker, "save", "--output", str(archive_path), tag)
                self.assertEqual(saved.returncode, 0, saved.stdout + saved.stderr)

                copied_files: set[str] = set()
                copied_paths: set[str] = set()
                with tarfile.open(archive_path, "r:*") as image:
                    manifest_file = image.extractfile("manifest.json")
                    self.assertIsNotNone(manifest_file)
                    manifest = json.load(manifest_file)
                    self.assertEqual(len(manifest), 1)
                    for layer_name in manifest[0]["Layers"]:
                        layer_file = image.extractfile(layer_name)
                        self.assertIsNotNone(layer_file)
                        with tarfile.open(fileobj=layer_file, mode="r|*") as layer:
                            for member in layer:
                                name = member.name.removeprefix("./").strip("/")
                                copied_paths.add(name)
                                if member.isfile():
                                    copied_files.add(name)
                self.assertTrue(set(retained).issubset(copied_files), copied_files)
                self.assertTrue(set(excluded).isdisjoint(copied_files), copied_files)
                self.assertTrue({
                    "app/__pycache__", "app/nested/__pycache__",
                    "app/nested/.pytest_cache", "app/nested/.mypy_cache",
                }.isdisjoint(copied_paths), copied_paths)
            finally:
                image = docker_command(docker, "image", "inspect", "--format", f"{{{{ index .Config.Labels \"{label}\" }}}}", tag)
                if image.returncode == 0:
                    self.assertEqual(image.stdout.strip(), marker, "拒绝清理非本测试创建的镜像")
                    removed = docker_command(docker, "image", "rm", "--force", tag)
                    self.assertEqual(removed.returncode, 0, removed.stdout + removed.stderr)
                elif image_created:
                    self.fail(f"无法核实或清理本测试创建的镜像：{image.stderr}")


if __name__ == "__main__":
    unittest.main()
