"""从已校验的白名单运行包启动原生服务并原子激活版本。"""

from __future__ import annotations

import argparse
import hashlib
import ipaddress
import json
import math
import os
import re
import secrets
import subprocess
import time
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import URLError
from urllib.parse import urlsplit
from urllib.request import urlopen

from runtime_package import verify


class AssetReferences(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.paths: set[str] = set()

    def handle_starttag(self, tag, attributes) -> None:
        values = dict(attributes)
        reference = values.get("src") if tag == "script" else values.get("href") if tag == "link" else None
        if reference:
            path = urlsplit(reference).path
            if path.startswith("/assets/"):
                self.paths.add(path)


def required_environment(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"原生运行缺少环境变量 {name}")
    return value


def load_environment_file(path: Path) -> None:
    source = absolute_path(str(path), "环境配置文件")
    if not source.is_file():
        raise RuntimeError("原生运行环境配置文件不存在")
    if os.name == "posix" and source.stat().st_mode & 0o077:
        raise RuntimeError("原生运行环境配置文件必须仅由所有者读取")
    for number, line in enumerate(source.read_text(encoding="utf-8").splitlines(), 1):
        if not line or line.startswith("#"):
            continue
        name, separator, value = line.partition("=")
        if (
            not separator or not re.fullmatch(r"[A-Z][A-Z0-9_]*", name)
            or value != value.strip() or value.startswith(("'", '"')) or "\\" in value
        ):
            raise RuntimeError(f"原生运行环境配置文件第 {number} 行格式无效")
        os.environ[name] = value


def absolute_path(value: str, name: str) -> Path:
    path = Path(value).expanduser()
    if not path.is_absolute():
        raise RuntimeError(f"{name} 必须是绝对路径")
    return path


def checked_package(path: Path) -> tuple[Path, dict]:
    package = path.resolve(strict=True)
    if in_checkout(package):
        raise RuntimeError("原生运行包不能位于 Git checkout 内")
    manifest = verify(package)
    if not re.fullmatch(r"[0-9a-f]{40}", str(manifest.get("source_commit", ""))):
        raise RuntimeError("运行包提交号无效")
    return package, manifest


def in_checkout(path: Path) -> bool:
    return any((parent / ".git").exists() for parent in (path, *path.parents))


def current_package() -> tuple[Path, dict]:
    current = absolute_path(required_environment("OA_NATIVE_RUNTIME_CURRENT"), "OA_NATIVE_RUNTIME_CURRENT")
    if not current.is_symlink():
        raise RuntimeError("当前原生运行入口必须是已激活的符号链接")
    parent = current.parent.resolve(strict=True)
    if in_checkout(parent):
        raise RuntimeError("当前原生运行入口不能位于 Git checkout 内")
    package, manifest = checked_package(current)
    if parent == package or parent.is_relative_to(package):
        raise RuntimeError("当前原生运行入口不能位于运行包内")
    return package, manifest


def loopback(name: str) -> str:
    value = os.environ.get(name, "127.0.0.1").strip()
    if not ipaddress.ip_address(value).is_loopback:
        raise RuntimeError(f"{name} 必须绑定回环地址")
    return value


def port(name: str) -> int:
    value = int(required_environment(name))
    if not 1 <= value <= 65535:
        raise RuntimeError(f"{name} 必须在 1 到 65535 之间")
    return value


def base_url(host: str, selected_port: int) -> str:
    return f"http://[{host}]:{selected_port}" if ":" in host else f"http://{host}:{selected_port}"


def read_url(url: str) -> bytes:
    with urlopen(url, timeout=5) as response:
        if response.status != 200:
            raise RuntimeError(f"原生服务返回 HTTP {response.status}：{url}")
        return response.read()


def checked_static(package: Path, manifest: dict, web: str, relative: str) -> bytes:
    content = read_url(f"{web}/{relative}")
    expected = manifest["files"].get(f"web/{relative}")
    local = package / "web" / relative
    if (
        expected is None or not local.is_file()
        or hashlib.sha256(local.read_bytes()).hexdigest() != expected
        or hashlib.sha256(content).hexdigest() != expected
    ):
        raise RuntimeError(f"原生 Web 资源与已校验运行包不一致：{relative}")
    return content


def health(package: Path, manifest: dict) -> dict:
    api = base_url(loopback("OA_NATIVE_API_HOST"), port("OA_NATIVE_API_PORT"))
    web = base_url(loopback("OA_NATIVE_WEB_HOST"), port("OA_NATIVE_WEB_PORT"))
    api_health = json.loads(read_url(f"{api}/health"))
    web_health = json.loads(read_url(f"{web}/health"))
    if api_health.get("status") != "ok" or web_health.get("status") != "ok":
        raise RuntimeError("原生 API 或 Web 代理健康状态不正确")
    index = checked_static(package, manifest, web, "index.html").decode("utf-8")
    parser = AssetReferences()
    parser.feed(index)
    if not parser.paths:
        raise RuntimeError("原生 Web 页面没有正式构建资源")
    for asset in parser.paths:
        if ".." in asset.split("/"):
            raise RuntimeError(f"原生 Web 资源路径无效：{asset}")
        if not checked_static(package, manifest, web, asset.lstrip("/")):
            raise RuntimeError(f"原生 Web 资源为空：{asset}")
    info = json.loads(checked_static(package, manifest, web, "build-info.json"))
    if info.get("source_commit") != manifest["source_commit"] or info.get("version") != manifest["version"]:
        raise RuntimeError("原生 Web 构建标记与运行包不一致")
    return {"status": "passed", "source_commit": manifest["source_commit"], "assets": len(parser.paths)}


def await_health(package: Path, manifest: dict) -> dict:
    timeout = float(os.environ.get("OA_NATIVE_HEALTH_TIMEOUT", "30"))
    if not math.isfinite(timeout) or timeout <= 0:
        raise RuntimeError("OA_NATIVE_HEALTH_TIMEOUT 必须是正数")
    deadline = time.monotonic() + timeout
    while True:
        try:
            return health(package, manifest)
        except (URLError, TimeoutError, ConnectionError):
            if time.monotonic() >= deadline:
                raise RuntimeError("原生服务健康检查超时") from None
            time.sleep(0.25)


def atomic_link(current: Path, package: Path) -> None:
    staged = current.with_name(f"{current.name}.next-{secrets.token_hex(8)}")
    try:
        staged.symlink_to(package, target_is_directory=True)
        os.replace(staged, current)
    finally:
        staged.unlink(missing_ok=True)


def services(action: str) -> None:
    controller = required_environment("OA_NATIVE_SYSTEMCTL")
    api_service = required_environment("OA_NATIVE_API_SERVICE")
    web_service = required_environment("OA_NATIVE_WEB_SERVICE")
    subprocess.run([controller, action, api_service, web_service], check=True)


def activate(package_path: Path, current_path: Path, expected_commit: str) -> dict:
    package, manifest = checked_package(package_path)
    current = absolute_path(str(current_path), "当前版本链接")
    if not current.parent.is_dir() or (current.exists() and not current.is_symlink()):
        raise RuntimeError("当前版本入口的父目录不存在，或入口不是符号链接")
    parent = current.parent.resolve(strict=True)
    if in_checkout(parent):
        raise RuntimeError("当前版本入口不能位于 Git checkout 内")
    configured = absolute_path(required_environment("OA_NATIVE_RUNTIME_CURRENT"), "OA_NATIVE_RUNTIME_CURRENT")
    if parent / current.name != configured.parent.resolve(strict=True) / configured.name:
        raise RuntimeError("激活入口与服务配置的当前版本入口不一致")
    if parent == package or parent.is_relative_to(package):
        raise RuntimeError("当前版本入口不能位于运行包内")
    if manifest["source_commit"] != expected_commit:
        raise RuntimeError("运行包提交号与预期发布提交不一致")
    previous = checked_package(current)[0] if current.is_symlink() else None
    atomic_link(current, package)
    try:
        services("restart")
        result = await_health(package, manifest)
    except Exception as exc:
        try:
            if previous is None:
                current.unlink(missing_ok=True)
                services("stop")
            else:
                atomic_link(current, previous)
                services("restart")
        # 恢复过程的任何失败都必须与原激活失败一起报告。
        except Exception as rollback_error:  # noqa: BLE001
            raise RuntimeError(f"新运行包激活失败：{exc}；恢复旧版本也失败：{rollback_error}") from exc
        raise RuntimeError(f"新运行包激活失败，已恢复旧版本：{exc}") from exc
    return result


def start_api() -> None:
    package, _ = current_package()
    if required_environment("APP_ENV").lower() != "production":
        raise RuntimeError("原生 API 必须在 production 环境启动")
    for key in ("DATABASE_URL", "SECRET_KEY", "INITIAL_ADMIN_PASSWORD"):
        required_environment(key)
    upload_root = absolute_path(required_environment("UPLOAD_ROOT"), "UPLOAD_ROOT")
    if upload_root.resolve().is_relative_to(package):
        raise RuntimeError("附件目录不能位于只读运行包内")
    python = absolute_path(required_environment("OA_NATIVE_PYTHON"), "OA_NATIVE_PYTHON")
    if not python.is_file():
        raise RuntimeError("OA_NATIVE_PYTHON 不存在")
    api_directory = package / "api"
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(api_directory)
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    os.chdir(api_directory)
    os.execve(str(python), [str(python), "-m", "uvicorn", "app.main:app", "--host",
                            loopback("OA_NATIVE_API_HOST"), "--port", str(port("OA_NATIVE_API_PORT"))], environment)


def nginx_path(path: Path) -> str:
    value = path.as_posix()
    if any(character in value for character in ('"', "\\", "$", "\n", "\r", ";")):
        raise RuntimeError(f"Nginx 路径含有不能安全引用的字符：{path}")
    return f'"{value}"'


def web_config(package: Path, state: Path, mime_types: Path) -> str:
    api = base_url(loopback("OA_NATIVE_API_HOST"), port("OA_NATIVE_API_PORT"))
    web_host = loopback("OA_NATIVE_WEB_HOST")
    listen = f"[{web_host}]" if ":" in web_host else web_host
    web_port = port("OA_NATIVE_WEB_PORT")
    return f"""worker_processes auto;
pid {nginx_path(state / 'nginx.pid')};
error_log stderr warn;
events {{ worker_connections 1024; }}
http {{
  include {nginx_path(mime_types)};
  default_type application/octet-stream;
  client_body_temp_path {nginx_path(state / 'client-body')};
  proxy_temp_path {nginx_path(state / 'proxy')};
  access_log syslog:server=unix:/dev/log,tag=sunhold_native_web,nohostname;
  server {{
    listen {listen}:{web_port};
    server_name _;
    root {nginx_path(package / 'web')};
    index index.html;
    client_max_body_size 21m;
    location = /health {{ proxy_pass {api}/health; }}
    location = /api/v1/finance/incoming-payments/import {{
      client_max_body_size 101m;
      client_body_timeout 600s;
      proxy_pass {api};
      proxy_http_version 1.1;
      proxy_set_header Host $host;
      proxy_set_header X-Real-IP $remote_addr;
      proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
      proxy_set_header X-Forwarded-Proto $scheme;
      proxy_connect_timeout 5s;
      proxy_read_timeout 600s;
      proxy_send_timeout 600s;
    }}
    location /api/ {{
      proxy_pass {api};
      proxy_http_version 1.1;
      proxy_set_header Host $host;
      proxy_set_header X-Real-IP $remote_addr;
      proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
      proxy_set_header X-Forwarded-Proto $scheme;
      proxy_connect_timeout 5s;
      proxy_read_timeout 120s;
      proxy_send_timeout 120s;
    }}
    location /assets/ {{ try_files $uri =404; expires 1y; add_header Cache-Control "public, immutable"; }}
    location = /index.html {{ try_files $uri =404; expires -1; add_header Cache-Control "no-store, no-cache, must-revalidate, proxy-revalidate, max-age=0" always; }}
    location / {{ try_files $uri /index.html; expires -1; add_header Cache-Control "no-store, no-cache, must-revalidate, proxy-revalidate, max-age=0" always; }}
  }}
}}
"""


def start_web() -> None:
    package, _ = current_package()
    if required_environment("APP_ENV").lower() != "production":
        raise RuntimeError("原生 Web 必须在 production 环境启动")
    state = absolute_path(required_environment("OA_NATIVE_WEB_STATE_DIR"), "OA_NATIVE_WEB_STATE_DIR")
    if not state.is_dir() or state.resolve().is_relative_to(package):
        raise RuntimeError("Web 状态目录必须已存在且位于运行包外")
    nginx = absolute_path(required_environment("OA_NATIVE_NGINX"), "OA_NATIVE_NGINX")
    mime_types = absolute_path(required_environment("OA_NATIVE_MIME_TYPES"), "OA_NATIVE_MIME_TYPES")
    if not nginx.is_file() or not mime_types.is_file():
        raise RuntimeError("Nginx 程序或 MIME 配置不存在")
    (state / "client-body").mkdir(exist_ok=True)
    (state / "proxy").mkdir(exist_ok=True)
    config = state / "nginx.conf"
    config.write_text(web_config(package, state, mime_types), encoding="utf-8")
    subprocess.run([str(nginx), "-t", "-p", str(state), "-c", str(config)], check=True)
    os.execve(str(nginx), [str(nginx), "-p", str(state), "-c", str(config), "-g", "daemon off;"], os.environ.copy())


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", type=Path)
    parser.add_argument("action", choices=("verify", "activate", "api", "web", "health"))
    parser.add_argument("--package", type=Path)
    parser.add_argument("--current", type=Path)
    parser.add_argument("--expected-commit")
    args = parser.parse_args()
    if args.env_file is not None:
        load_environment_file(args.env_file)
    if args.action == "verify":
        if args.package is None:
            parser.error("verify 需要 --package")
        _, manifest = checked_package(args.package)
        result = {"status": "passed", "source_commit": manifest["source_commit"], "files": len(manifest["files"])}
    elif args.action == "activate":
        if args.package is None or args.current is None or not args.expected_commit:
            parser.error("activate 需要 --package、--current 和 --expected-commit")
        result = activate(args.package, args.current, args.expected_commit)
    elif args.action == "api":
        start_api()
        return
    elif args.action == "web":
        start_web()
        return
    else:
        package, manifest = current_package()
        result = health(package, manifest)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
