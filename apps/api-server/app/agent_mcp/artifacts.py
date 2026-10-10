"""独立于业务附件的私有工具结果缓存，不保存登录凭据。"""

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import time
from uuid import uuid4

from fastapi import HTTPException
from starlette.concurrency import run_in_threadpool

from app.agent_mcp.auth import authenticated_identity
from app.agent_mcp.config import mcp_settings
from app.config import settings
from app.core.constants import UPLOAD_ROOT


_RESOURCE_ID = re.compile(r"^[0-9a-f]{32}$")
_ROOT_MARKER = ".oa-mcp-export-root"


def _root() -> Path:
    configured = mcp_settings.agent_mcp_export_root.strip()
    root = Path(configured).expanduser() if configured else Path(UPLOAD_ROOT).resolve().parent / "private-mcp-exports"
    if root.is_symlink():
        raise OSError("MCP 私有结果目录不能是符号链接")
    return root.resolve()


def _write_private(path: Path, content: bytes) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0)
    if os.name == "posix":
        flags |= os.O_NOFOLLOW
    descriptor = os.open(path, flags, 0o600)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            if os.name == "posix":
                os.fchmod(handle.fileno(), 0o600)
            handle.write(content)
    except Exception:
        path.unlink(missing_ok=True)
        raise


def _ensure_private_root(root: Path) -> None:
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    marker = root / _ROOT_MARKER
    if not marker.exists():
        if any(path.name != _ROOT_MARKER for path in root.iterdir()) and not marker.exists():
            raise OSError("MCP 结果目录非空且没有模块归属标记，不能修改共享目录权限")
        try:
            _write_private(marker, b"")
        except FileExistsError:
            # 并发 worker 只能竞争同一模块的空归属标记，其他创建错误仍向上报告。
            pass
    if marker.is_symlink() or not marker.is_file() or marker.stat().st_size != 0:
        raise OSError("MCP 私有结果目录归属标记无效")
    if os.name == "posix":
        if root.stat().st_uid != os.geteuid() or marker.stat().st_uid != os.geteuid():
            raise OSError("MCP 私有结果目录不属于当前服务账号")
        # 仅修正已确认的模块自有目录和标记，不递归更改其他目录或文件。
        root.chmod(0o700)
        marker.chmod(0o600)


def _write(metadata: dict, content: bytes | None) -> None:
    root = _root()
    _ensure_private_root(root)
    artifact_id = metadata["id"]
    encoded_metadata = json.dumps(metadata, ensure_ascii=False, allow_nan=False).encode("utf-8")
    staging = root / (artifact_id + ".json.part")
    content_created = False
    staging_created = False
    try:
        if content is not None:
            _write_private(root / (artifact_id + ".bin"), content)
            content_created = True
        _write_private(staging, encoded_metadata)
        staging_created = True
        staging.rename(root / (artifact_id + ".json"))
    except Exception:
        if staging_created:
            staging.unlink(missing_ok=True)
        if content_created:
            (root / (artifact_id + ".bin")).unlink(missing_ok=True)
        raise
    # 只清理由本模块生成、已过期且形状有效的缓存，不触碰业务文件。
    for path in root.glob("*.json"):
        if not _RESOURCE_ID.fullmatch(path.stem):
            continue
        try:
            with path.open(encoding="utf-8") as handle:
                item = json.load(handle)
        except FileNotFoundError:
            continue
        if item["id"] == path.stem and item["expires"] <= time.time():
            (root / (path.stem + ".bin")).unlink(missing_ok=True)
            path.unlink(missing_ok=True)


def _list(username: str) -> list[dict]:
    root = _root()
    if not root.exists():
        return []
    _ensure_private_root(root)
    resources = []
    for path in root.glob("*.json"):
        if not _RESOURCE_ID.fullmatch(path.stem):
            continue
        try:
            with path.open(encoding="utf-8") as handle:
                metadata = json.load(handle)
        except FileNotFoundError:
            continue
        if metadata["id"] == path.stem and metadata["owner"] == username and metadata["expires"] > time.time():
            resources.append(resource_metadata(metadata))
    return resources


async def list_resources() -> list[dict]:
    identity = await authenticated_identity()
    return await run_in_threadpool(_list, identity["username"])


def _load(resource_id: str, username: str) -> dict:
    if not _RESOURCE_ID.fullmatch(resource_id):
        raise HTTPException(404, "工具资源不存在")
    root = _root()
    if not root.exists():
        raise HTTPException(404, "工具资源不存在或已过期")
    _ensure_private_root(root)
    path = root / (resource_id + ".json")
    try:
        with path.open(encoding="utf-8") as handle:
            metadata = json.load(handle)
    except FileNotFoundError as exc:
        raise HTTPException(404, "工具资源不存在或已过期") from exc
    if metadata["id"] != resource_id or metadata["owner"] != username:
        raise HTTPException(404, "工具资源不存在或不属于当前账号")
    if metadata["expires"] <= time.time():
        (root / (resource_id + ".bin")).unlink(missing_ok=True)
        path.unlink(missing_ok=True)
        raise HTTPException(410, "工具结果已过期，请重新发起查询")
    return metadata


def resource_metadata(metadata: dict) -> dict:
    kind = metadata["kind"]
    identifier = metadata["id"]
    return {
        "type": "resource_link", "uri": f"oa-mcp-{kind}://{identifier}",
        "artifact_id" if kind == "artifact" else "resource_id": identifier,
        "name": metadata["name"], "mimeType": metadata["mime_type"],
        "size": metadata.get("size"), "sha256": metadata.get("sha256"),
        "download_url": settings.api_prefix + f"/agent-tools/{'artifacts' if kind == 'artifact' else 'resources'}/{identifier}",
        "expires_at": datetime.fromtimestamp(metadata["expires"], timezone.utc).isoformat(),
        "authentication_required": True,
    }


async def cache_result(name: str, mime_type: str, content: bytes) -> dict:
    identity = await authenticated_identity()
    metadata = {
        "id": uuid4().hex, "kind": "artifact", "owner": identity["username"], "name": name,
        "mime_type": mime_type, "size": len(content), "sha256": hashlib.sha256(content).hexdigest(),
        "expires": time.time() + mcp_settings.agent_mcp_export_ttl_seconds,
    }
    await run_in_threadpool(_write, metadata, content)
    return resource_metadata(metadata)


async def cache_source(spec, params: dict, case_origin: int | None, *, name: str, mime_type: str) -> dict:
    if spec.is_write or spec.method != "GET":
        raise HTTPException(409, "写接口的跳转结果不能通过再次调用原接口下载")
    from app.agent_mcp.service import descriptor_fingerprint

    identity = await authenticated_identity()
    metadata = {
        "id": uuid4().hex, "kind": "source", "owner": identity["username"], "name": name,
        "mime_type": mime_type, "tool_name": spec.name, "params": params, "case_origin": case_origin,
        "descriptor_fingerprint": descriptor_fingerprint(spec),
        "expires": time.time() + mcp_settings.agent_mcp_export_ttl_seconds,
    }
    await run_in_threadpool(_write, metadata, None)
    return resource_metadata(metadata)


async def read_resource(resource_id: str, *, expected_kind: str | None = None) -> tuple[dict, bytes]:
    identity = await authenticated_identity()
    metadata = await run_in_threadpool(_load, resource_id, identity["username"])
    if expected_kind is not None and metadata["kind"] != expected_kind:
        raise HTTPException(404, "工具资源类型不匹配")
    if metadata["kind"] == "source":
        from app.agent_mcp.auth import get_auth_context
        from app.agent_mcp.catalog import get_catalog
        from app.agent_mcp.service import descriptor_fingerprint
        from app.agent_mcp.transport import read_source

        spec = get_catalog(get_auth_context().application).get(metadata["tool_name"])
        if spec.is_write or spec.method != "GET" or descriptor_fingerprint(spec) != metadata["descriptor_fingerprint"]:
            raise HTTPException(409, "下载接口定义已变化，请重新发起查询")
        content = await read_source(spec, metadata["params"], case_origin=metadata["case_origin"])
    else:
        content = await run_in_threadpool((_root() / (resource_id + ".bin")).read_bytes)
        if len(content) != metadata["size"] or hashlib.sha256(content).hexdigest() != metadata["sha256"]:
            raise HTTPException(409, "工具结果缓存校验失败")
    return metadata, content
