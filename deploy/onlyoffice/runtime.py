"""管理隔离 Office 组件，不读取业务附件或操作 OA 数据库。"""

import argparse
import json
import os
from pathlib import Path
import re
import secrets
import socket
import subprocess
import time
from urllib.error import URLError
from urllib.parse import urlsplit
from urllib.request import urlopen

from nginx_config import activate as activate_nginx
from github_image import DEB_SHA256, PACKAGE_VERSION

ROOT = Path(__file__).resolve().parent


def read_environment(path: Path) -> dict[str, str]:
    if path.is_symlink() or path.stat().st_uid != 0 or path.stat().st_mode & 0o077:
        raise RuntimeError("环境文件必须为非符号链接且权限不宽于 0600")
    values = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        key, separator, value = line.partition("=")
        if not separator or not re.fullmatch(r"[A-Z][A-Z0-9_]*", key) or key in values:
            raise RuntimeError("环境文件含有无效或重复配置项")
        values[key] = value
    return values


def validate(values: dict[str, str]) -> tuple[str, int]:
    required = read_keys()
    for key in required:
        if not values.get(key):
            raise RuntimeError(f"缺少部署配置：{key}")
    if set(values) != set(required):
        raise RuntimeError("部署配置含有模板以外的配置项")
    if any(not re.fullmatch(r"sha256:[0-9a-f]{64}", values[key]) for key in ("ONLYOFFICE_IMAGE", "ONLYOFFICE_BASE_IMAGE")):
        raise RuntimeError("必须固定隔离构建镜像与已核验依赖底座的实际 ImageID")
    if values["ONLYOFFICE_PACKAGE_VERSION"] != PACKAGE_VERSION or values["ONLYOFFICE_GITHUB_DEB_SHA256"] != DEB_SHA256:
        raise RuntimeError("必须使用已核验的 GitHub 官方社区版 9.4 Debian 包")
    public = urlsplit(values["ONLYOFFICE_DOCUMENT_SERVER_URL"])
    callback = urlsplit(values["ONLYOFFICE_CALLBACK_BASE_URL"])
    service = urlsplit(values["ONLYOFFICE_SERVICE_URL"])
    if public.scheme != "https" or public.path != "/office" or public.port not in (None, 443):
        raise RuntimeError("编辑器必须使用同域 HTTPS /office")
    if callback.scheme != "https" or callback.netloc != public.netloc or callback.path != "/api/v1":
        raise RuntimeError("回调必须使用同域 HTTPS /api/v1")
    if service.scheme != "http" or service.hostname != "127.0.0.1" or service.path or not service.port:
        raise RuntimeError("内部编辑器必须使用专属 IPv4 回环地址")
    if not public.hostname or not re.fullmatch(r"[A-Za-z0-9.-]+", public.hostname):
        raise RuntimeError("公网域名无效")
    for url in (public, callback, service):
        if url.username or url.password or url.query or url.fragment:
            raise RuntimeError("编辑器地址不能包含认证信息、查询参数或片段")
    if not 1024 <= service.port <= 65535:
        raise RuntimeError("内部服务端口必须是非特权端口")
    if not values["ONLYOFFICE_DOCUMENT_TOKEN_SECONDS"].isdigit() or not 60 <= int(values["ONLYOFFICE_DOCUMENT_TOKEN_SECONDS"]) <= 900:
        raise RuntimeError("文档访问令牌有效期必须在 60 至 900 秒之间")
    if not re.fullmatch(r"[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)*/", values["ONLYOFFICE_OSS_WRITE_PREFIX"]):
        raise RuntimeError("Office 新版本前缀无效")
    for key in required:
        if key.endswith(("_DIR", "_FILE", "_CONFIG", "_INCLUDE")):
            if not re.fullmatch(r"/[A-Za-z0-9_./-]+", values[key]):
                raise RuntimeError(f"配置必须是可安全引用的绝对路径：{key}")
    if not re.fullmatch(r"[0-9a-f]{64}", values["ONLYOFFICE_NGINX_CONFIG_SHA256"]):
        raise RuntimeError("必须提供已核验的 Nginx 配置 SHA256")
    return public.hostname, service.port


def read_keys() -> list[str]:
    return [line.partition("=")[0] for line in (ROOT / "deployment.env.example").read_text(encoding="utf-8").splitlines() if line and not line.startswith("#")]


def write_private(path: Path, values: dict[str, str]) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
        stream.write("".join(f"{key}={value}\n" for key, value in values.items()))


def prepare(config: dict[str, str], port: int) -> Path:
    private = Path(config["ONLYOFFICE_PRIVATE_DIR"])
    private.mkdir(mode=0o700, parents=True, exist_ok=True)
    if private.is_symlink() or private.stat().st_uid != 0 or private.stat().st_mode & 0o077:
        raise RuntimeError("私密配置目录必须由 root 持有且权限不宽于 0700")
    app_env = private / "onlyoffice-api.env"
    expected = {key: config[key] for key in ("ONLYOFFICE_DOCUMENT_SERVER_URL", "ONLYOFFICE_SERVICE_URL", "ONLYOFFICE_CALLBACK_BASE_URL", "ONLYOFFICE_DOCUMENT_TOKEN_SECONDS", "ONLYOFFICE_OSS_WRITE_PREFIX")}
    if app_env.exists():
        app_values = read_environment(app_env)
        if any(app_values.get(key) != value for key, value in expected.items()):
            raise RuntimeError("已有 Office API 配置与本次部署不一致")
        secret = app_values.get("ONLYOFFICE_JWT_SECRET", "")
        if not re.fullmatch(r"[0-9a-f]{128}", secret):
            raise RuntimeError("已有 JWT 密钥不符合持久随机密钥要求")
    else:
        secret = secrets.token_hex(64)
        write_private(app_env, {**expected, "ONLYOFFICE_JWT_SECRET": secret})
    container_env = private / "onlyoffice-container.env"
    container_values = {"JWT_ENABLED": "true", "JWT_SECRET": secret, "JWT_HEADER": "Authorization", "JWT_IN_BODY": "false", "WOPI_ENABLED": "false", "EXAMPLE_ENABLED": "false", "ADMINPANEL_ENABLED": "false", "ALLOW_PRIVATE_IP_ADDRESS": "false", "ALLOW_META_IP_ADDRESS": "false", "USE_UNAUTHORIZED_STORAGE": "false", "PLUGINS_ENABLED": "false"}
    if container_env.exists():
        if read_environment(container_env) != container_values:
            raise RuntimeError("已有容器安全配置与本次部署不一致")
    else:
        write_private(container_env, container_values)
    runtime = Path(config["ONLYOFFICE_RUNTIME_DIR"])
    runtime.mkdir(mode=0o700, parents=True, exist_ok=True)
    for name in ("data", "cache", "logs", "backups"):
        (runtime / name).mkdir(mode=0o700, exist_ok=True)
    locations = runtime / "office.locations.conf"
    content = (ROOT / "nginx.location.conf.template").read_text(encoding="utf-8").replace("@@PORT@@", str(port))
    if locations.exists():
        if locations.read_text(encoding="utf-8") != content:
            raise RuntimeError("已有 Office location 配置不同，不能覆盖")
    else:
        with locations.open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(content)
        os.chmod(locations, 0o644)
    return locations


def start(config: dict[str, str], env_file: Path, port: int) -> None:
    with socket.socket() as check:
        check.bind(("127.0.0.1", port))
    prepare(config, port)
    environment = {**os.environ, **config, "ONLYOFFICE_PORT": str(port), "ONLYOFFICE_CONTAINER_ENV": str(Path(config["ONLYOFFICE_PRIVATE_DIR"]) / "onlyoffice-container.env")}
    compose = ["docker", "compose", "--env-file", str(env_file), "-f", str(ROOT / "compose.yml")]
    subprocess.run([*compose, "config", "--quiet"], env=environment, check=True)
    inspection = subprocess.run(["docker", "image", "inspect", config["ONLYOFFICE_IMAGE"], "--format", "{{.Id}}\n{{json .Config.Labels}}"], capture_output=True, text=True, check=True).stdout.splitlines()
    expected = {"org.sunhold.onlyoffice.github-deb.sha256": config["ONLYOFFICE_GITHUB_DEB_SHA256"], "org.sunhold.onlyoffice.package-version": config["ONLYOFFICE_PACKAGE_VERSION"], "org.sunhold.onlyoffice.base-image": config["ONLYOFFICE_BASE_IMAGE"]}
    labels = json.loads(inspection[1])
    if inspection[0] != config["ONLYOFFICE_IMAGE"] or any(labels.get(key) != value for key, value in expected.items()):
        raise RuntimeError("实际镜像与 GitHub 包、版本或依赖底座的来源链不一致，禁止启动")
    subprocess.run([*compose, "up", "-d", "--no-build", "--pull", "never"], env=environment, check=True)
    deadline = time.monotonic() + 180
    error = ""
    while time.monotonic() < deadline:
        try:
            with urlopen(f"{config['ONLYOFFICE_SERVICE_URL']}/healthcheck", timeout=5) as response:
                if response.status == 200 and response.read().strip() == b"true":
                    break
        except (URLError, TimeoutError, ConnectionError) as exc:
            error = str(exc)
        time.sleep(3)
    else:
        subprocess.run([*compose, "stop", "documentserver"], env=environment, check=True)
        raise RuntimeError(f"Office 健康检查失败：{error}")
    try:
        subprocess.run([*compose, "exec", "-T", "documentserver", "bash", "/usr/local/bin/sunhold-onlyoffice-entrypoint.sh", "verify"], env=environment, check=True)
    except BaseException:
        subprocess.run([*compose, "stop", "documentserver"], env=environment, check=True)
        raise
    print("ONLYOFFICE_RUNTIME_STARTED: JWT enabled; loopback only; OA and Nginx unchanged")


def activate(config: dict[str, str], host: str, port: int) -> None:
    with urlopen(f"{config['ONLYOFFICE_SERVICE_URL']}/healthcheck", timeout=5) as response:
        if response.status != 200 or response.read().strip() != b"true":
            raise RuntimeError("隔离 Office 服务未就绪，不能启用反向代理")
    activate_nginx(config, host, prepare(config, port))
    print("ONLYOFFICE_PROXY_ACTIVE: same-origin HTTPS; OA upstreams unchanged")


def configure_api(config: dict[str, str], port: int, unit: str) -> None:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*\.service", unit):
        raise RuntimeError("必须显式指定已核验的 API systemd 服务名")
    fragment = subprocess.run(["systemctl", "show", unit, "--property=FragmentPath", "--value"], capture_output=True, text=True, check=True).stdout.strip()
    if not fragment or Path(fragment).name != unit or not Path(fragment).is_file():
        raise RuntimeError("API 服务单元不存在或不是指定的独立服务")
    prepare(config, port)
    directory = Path("/etc/systemd/system") / f"{unit}.d"
    directory.mkdir(mode=0o755, exist_ok=True)
    if directory.is_symlink() or directory.stat().st_uid != 0 or directory.stat().st_mode & 0o022:
        raise RuntimeError("API drop-in 目录必须由 root 持有且不可被其他用户写入")
    target = directory / "99-sunhold-onlyoffice.conf"
    content = f"[Service]\nEnvironmentFile={Path(config['ONLYOFFICE_PRIVATE_DIR']) / 'onlyoffice-api.env'}\n"
    if target.is_symlink():
        raise RuntimeError("API drop-in 不能是符号链接")
    if target.exists():
        if target.stat().st_uid != 0 or target.stat().st_mode & 0o022 or target.read_text(encoding="utf-8") != content:
            raise RuntimeError("已有 Office API drop-in 不一致，不能覆盖")
    else:
        with target.open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(content)
        os.chmod(target, 0o644)
    subprocess.run(["systemctl", "daemon-reload"], check=True)
    print("ONLYOFFICE_API_DROPIN_READY: independent EnvironmentFile; API not restarted")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("validate", "prepare-host", "prepare", "start", "activate", "configure-api"))
    parser.add_argument("--env-file", required=True, type=Path)
    parser.add_argument("--api-unit")
    arguments = parser.parse_args()
    config = read_environment(arguments.env_file)
    host, port = validate(config)
    if arguments.action == "validate":
        print("ONLYOFFICE_DEPLOYMENT_CONFIG_OK")
        return
    if os.geteuid() != 0:
        raise RuntimeError("部署操作必须由 root 执行")
    if arguments.action == "prepare-host":
        subprocess.run(["bash", str(ROOT / "install-prerequisites.sh")], env={**os.environ, **config}, check=True)
    elif arguments.action == "prepare":
        prepare(config, port)
        print("ONLYOFFICE_PRIVATE_CONFIG_READY: persistent JWT; no service started")
    elif arguments.action == "configure-api":
        if not arguments.api_unit:
            raise RuntimeError("API drop-in 安装必须显式指定 --api-unit")
        configure_api(config, port, arguments.api_unit)
    elif arguments.action == "start":
        start(config, arguments.env_file, port)
    else:
        activate(config, host, port)


if __name__ == "__main__":
    main()
