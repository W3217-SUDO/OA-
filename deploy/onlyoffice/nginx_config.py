"""只在已核验的 HTTPS 入口插入独立 Office 配置。"""

import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone


def atomic_write(path: Path, content: bytes, mode: int) -> None:
    descriptor, temporary = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(content)
            os.fchmod(stream.fileno(), mode)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def activate(config: dict[str, str], host: str, locations: Path) -> None:
    target = Path(config["ONLYOFFICE_NGINX_CONFIG"]).resolve(strict=True)
    original_mode = target.stat().st_mode & 0o777
    original = target.read_bytes()
    if hashlib.sha256(original).hexdigest() != config["ONLYOFFICE_NGINX_CONFIG_SHA256"]:
        raise RuntimeError("Nginx 入口已变化，必须重新核验，不能覆盖")
    lines = original.decode("utf-8").splitlines(keepends=True)
    anchor = config["ONLYOFFICE_NGINX_INSERT_AFTER"]
    if not anchor.startswith("listen ") or " ssl" not in anchor:
        raise RuntimeError("插入锚点必须是已核验的 TLS listen 指令")
    positions = [index for index, line in enumerate(lines) if line.strip() == anchor]
    if len(positions) != 1:
        raise RuntimeError("TLS 插入锚点必须唯一")
    position = positions[0]
    following = []
    for line in lines[position + 1:]:
        if line.strip().startswith(("location ", "server {", "}")):
            break
        following.append(line.strip())
    if f"server_name {host};" not in following:
        raise RuntimeError("TLS 锚点未对应指定的 OA 域名")
    include = f"    include {locations};\n"
    if any(line.strip() == include.strip() for line in lines):
        raise RuntimeError("Office include 已存在，不能重复激活")
    http_include = Path(config["ONLYOFFICE_NGINX_HTTP_INCLUDE"])
    if http_include.exists():
        raise RuntimeError("WebSocket map 目标已存在，不能覆盖")
    map_content = b"map $http_upgrade $sunhold_office_connection {\n    default upgrade;\n    '' close;\n}\n"
    backup_dir = Path(config["ONLYOFFICE_RUNTIME_DIR"]) / "backups"
    backup_dir.mkdir(mode=0o700, exist_ok=True)
    backup = backup_dir / f"nginx.{datetime.now(timezone.utc):%Y%m%dT%H%M%S%fZ}.conf"
    shutil.copy2(target, backup)
    os.chmod(backup, 0o600)
    lines.insert(position + 1, include)
    map_written = False
    target_written = False
    try:
        atomic_write(http_include, map_content, 0o644)
        map_written = True
        atomic_write(target, "".join(lines).encode("utf-8"), original_mode)
        target_written = True
        subprocess.run(["nginx", "-t"], check=True)
        subprocess.run(["systemctl", "reload", "nginx.service"], check=True)
    except BaseException:
        if target_written:
            atomic_write(target, original, original_mode)
        if map_written:
            http_include.unlink()
        subprocess.run(["nginx", "-t"], check=True)
        subprocess.run(["systemctl", "reload", "nginx.service"], check=True)
        raise
