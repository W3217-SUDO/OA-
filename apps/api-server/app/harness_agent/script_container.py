"""DSH 通过专属容器运行已安装技能，不继承 OA 文件、凭据或内网访问能力。"""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path, PurePosixPath
import re
import signal
import subprocess
import tempfile
from uuid import uuid4

from fastapi import HTTPException

from .script_network import LABEL, check_firewall

_RUNNERS = {".py": "/usr/bin/python3", ".js": "/usr/bin/node", ".mjs": "/usr/bin/node",
            ".cjs": "/usr/bin/node", ".sh": "/bin/bash"}
_OUTPUT_LIMIT = 64000
_TIMEOUT = 45


def _read(command):
    result = subprocess.run(command, check=False, capture_output=True, text=True, timeout=5,
                            env={"PATH": "/usr/sbin:/usr/bin:/sbin:/bin", "LANG": "C.UTF-8", "DOCKER_CONFIG": "/dev/null"})
    if result.returncode:
        raise ValueError("隔离运行环境检查失败：" + Path(command[0]).name)
    return result.stdout


def verify_runtime(image, network):
    try:
        image_value = json.loads(_read(["docker", "image", "inspect", image]))[0]
        if (image_value.get("Os") != "linux" or image_value.get("Config", {}).get("Labels", {}).get(LABEL) != "1"):
            raise ValueError("必须使用带固定摘要的专属 Linux 技能运行镜像")
        value = json.loads(_read(["docker", "network", "inspect", network]))[0]
        check_firewall(network, value, _read)
    except (OSError, subprocess.TimeoutExpired, ValueError, KeyError, IndexError) as exc:
        raise HTTPException(503, "技能运行依赖未就绪：" + str(exc)) from None


def relative_path(value):
    if not isinstance(value, str) or len(value) > 500:
        raise HTTPException(422, "技能脚本路径无效")
    path = PurePosixPath(value)
    if (not path.parts or path.is_absolute() or ".." in path.parts or "\\" in value or ":" in value
            or any(ord(char) < 32 for char in value)):
        raise HTTPException(422, "技能脚本只能使用包内相对路径")
    return path


def _container_command(image, network, package, script, arguments, name):
    runner = _RUNNERS[script.suffix]
    return ["docker", "create", "--pull=never", "--name", name, "--network", network, "--dns", "1.1.1.1",
            "--log-driver", "none",
            "--read-only", "--user", "65534:65534", "--cap-drop=ALL", "--security-opt=no-new-privileges",
            "--sysctl", "net.ipv6.conf.all.disable_ipv6=1",
            "--memory=512m", "--memory-swap=512m", "--pids-limit=64", "--cpus=1", "--ulimit", "nofile=128:128",
            "--ulimit", "fsize=8388608:8388608", "--mount", "type=bind,src=" + str(package) + ",dst=/skill,readonly",
            "--tmpfs", "/work:rw,noexec,nosuid,nodev,size=64m,mode=1777",
            "--tmpfs", "/tmp:rw,noexec,nosuid,nodev,size=16m,mode=1777", "--workdir", "/work",
            "--env", "HOME=/work", "--env", "TMPDIR=/tmp", "--env", "LANG=C.UTF-8",
            "--env", "PATH=/usr/bin:/bin", "--entrypoint", runner, image,
            *(["-B"] if script.suffix == ".py" else []), "/skill/" + str(script), *arguments]


async def execute(files, path, arguments, image, network):
    script = relative_path(path)
    if script.suffix not in _RUNNERS:
        raise HTTPException(422, "仅支持技能包中的 Node、Python 或 Bash 脚本")
    if not isinstance(arguments, list) or len(arguments) > 32 or any(
        not isinstance(item, str) or len(item) > 2000 or "\0" in item for item in arguments
    ):
        raise HTTPException(422, "技能脚本参数必须为有限的字符串数组")
    if str(script) not in files:
        raise HTTPException(404, "技能包未包含指定脚本")
    await asyncio.to_thread(verify_runtime, image, network)

    with tempfile.TemporaryDirectory(prefix="oa-skill-execution-") as temporary:
        package = Path(temporary) / "skill"
        package.mkdir(mode=0o755)
        for name, data in files.items():
            relative = relative_path(name)
            target = package.joinpath(*relative.parts)
            target.parent.mkdir(parents=True, exist_ok=True, mode=0o755)
            target.write_bytes(data)
            target.chmod(0o444)
        # 服务 UMask 为 0077；容器只挂载此无凭据副本，需要为其非 root 身份开放目录遍历。
        package.chmod(0o755)
        for directory in package.rglob("*"):
            if directory.is_dir():
                directory.chmod(0o755)
        name = "oa-skill-" + uuid4().hex
        identifier, process, readers = None, None, []
        try:
            creator = asyncio.create_task(asyncio.to_thread(_read, _container_command(image, network, package, script, arguments, name)))
            try:
                identifier = (await asyncio.shield(creator)).strip()
            except asyncio.CancelledError:
                # 创建命令在线程中继续完成；等它结束后再按本轮名称清理，避免取消竞态泄漏容器。
                await asyncio.gather(creator, return_exceptions=True)
                raise
            if not re.fullmatch(r"[a-f0-9]{64}", identifier):
                raise HTTPException(503, "技能容器标识无效，未开始执行")
            process = await asyncio.create_subprocess_exec("docker", "start", "--attach", identifier,
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
                env={"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8", "DOCKER_CONFIG": "/dev/null"}, start_new_session=True)
            size = 0

            async def capture(stream):
                nonlocal size
                content = bytearray()
                while chunk := await stream.read(4096):
                    size += len(chunk)
                    if size > _OUTPUT_LIMIT:
                        raise HTTPException(413, "技能脚本输出超过 64000 字节，执行已终止")
                    content.extend(chunk)
                return content.decode("utf-8", errors="replace")

            async with asyncio.timeout(_TIMEOUT):
                readers = [asyncio.create_task(capture(process.stdout)), asyncio.create_task(capture(process.stderr))]
                stdout, stderr = await asyncio.gather(*readers)
                await process.wait()
            state = json.loads(await asyncio.to_thread(_read, ["docker", "inspect", "--format", "{{json .State}}", identifier]))
            code = state["ExitCode"]
            failed = bool(code or state.get("OOMKilled") or state.get("Error") or process.returncode)
            return {"script": str(script), "exit_code": code,
                    "stdout": stdout, "stderr": stderr, "isError": failed,
                    "message": "脚本执行失败，未确认操作成功" if failed else "脚本执行完成",
                    "network": "public-http-only", "files_persisted": False}
        except TimeoutError as exc:
            raise HTTPException(504, "技能脚本执行超过 45 秒，执行已终止") from exc
        except (OSError, subprocess.TimeoutExpired, ValueError, KeyError) as exc:
            raise HTTPException(503, "技能隔离运行失败：" + type(exc).__name__) from None
        finally:
            try:
                remaining = (await asyncio.to_thread(_read, ["docker", "ps", "--all", "--filter", "name=^/" + name + "$", "--format", "{{.ID}}"])).strip()
                if remaining:
                    await asyncio.to_thread(_read, ["docker", "rm", "--force", name])
                    if (await asyncio.to_thread(_read, ["docker", "ps", "--all", "--filter", "name=^/" + name + "$", "--format", "{{.ID}}"])).strip():
                        raise ValueError("临时容器仍然存在")
            except (OSError, subprocess.TimeoutExpired, ValueError) as exc:
                raise HTTPException(503, "技能临时容器清理失败，需要管理员处理：" + name) from exc
            finally:
                if process is not None:
                    if process.returncode is None:
                        try:
                            os.killpg(process.pid, signal.SIGKILL)
                        except ProcessLookupError:
                            pass
                    await process.wait()
                for reader in readers:
                    reader.cancel()
                await asyncio.gather(*readers, return_exceptions=True)
