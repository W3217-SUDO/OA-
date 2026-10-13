"""持久生成文件与受控源引用；历史私有缓存只读，不保存登录凭据。"""

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import time
from types import SimpleNamespace
from uuid import uuid4

from fastapi import HTTPException
from starlette.concurrency import run_in_threadpool
from sqlalchemy import select

from app.agent_mcp.auth import authenticated_identity
from app.agent_mcp.config import mcp_settings
from app.config import settings
from app.core.constants import UPLOAD_ROOT
from app.core.generated_file_records import FILE_MODULE, generated_file_item, require_generated_record_access
from app.core.generated_file_storage import read_generated_bytes, save_generated_file
from app.database import SessionLocal
from app.models import BusinessRecord, FileAttachment


_RESOURCE_ID = re.compile(r"^[0-9a-f]{32}$")
_ROOT_MARKER = ".oa-mcp-export-root"


def _root() -> Path:
    configured = mcp_settings.agent_mcp_export_root.strip()
    root = Path(configured).expanduser() if configured else Path(UPLOAD_ROOT).resolve().parent / "private-mcp-exports"
    if root.is_symlink():
        raise OSError("MCP 私有结果目录不能是符号链接")
    return root.resolve()


def _source_root() -> Path:
    if mcp_settings.agent_mcp_export_root.strip():
        return _root()
    root = Path(UPLOAD_ROOT).resolve() / "private-mcp-sources"
    if root.is_symlink():
        raise OSError("MCP 私有源引用目录不能是符号链接")
    return root.resolve()


def _cache_roots() -> tuple[Path, ...]:
    # 仅识别明确的源引用目录与历史缓存目录，不搜索其他共享目录。
    return tuple(dict.fromkeys((_source_root(), _root())))


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


def _validate_private_root(root: Path, *, require_private: bool = True) -> None:
    marker = root / _ROOT_MARKER
    if root.is_symlink() or marker.is_symlink() or not marker.is_file() or marker.stat().st_size != 0:
        raise OSError("MCP 私有结果目录归属标记无效")
    if os.name == "posix":
        if root.stat().st_uid != os.geteuid() or marker.stat().st_uid != os.geteuid():
            raise OSError("MCP 私有结果目录不属于当前服务账号")
        if require_private and (root.stat().st_mode & 0o077 or marker.stat().st_mode & 0o077):
            raise OSError("MCP 私有结果目录或标记权限不安全，拒绝读取")


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
    _validate_private_root(root, require_private=False)
    if os.name == "posix":
        # 仅修正已确认的模块自有目录和标记，不递归更改其他目录或文件。
        root.chmod(0o700)
        marker.chmod(0o600)


def _write(metadata: dict) -> None:
    root = _source_root()
    _ensure_private_root(root)
    artifact_id = metadata["id"]
    encoded_metadata = json.dumps(metadata, ensure_ascii=False, allow_nan=False).encode("utf-8")
    staging = root / (artifact_id + ".json.part")
    staging_created = False
    try:
        _write_private(staging, encoded_metadata)
        staging_created = True
        staging.rename(root / (artifact_id + ".json"))
    except Exception:
        if staging_created:
            staging.unlink(missing_ok=True)
        raise


def _list(username: str) -> list[dict]:
    resources = []
    seen = set()
    for root in _cache_roots():
        if not root.exists():
            continue
        _validate_private_root(root)
        for path in root.glob("*.json"):
            if not _RESOURCE_ID.fullmatch(path.stem):
                continue
            if path.is_symlink():
                raise OSError("MCP 私有资源元数据不能是符号链接")
            try:
                with path.open(encoding="utf-8") as handle:
                    metadata = json.load(handle)
            except FileNotFoundError:
                continue
            if metadata["id"] in seen:
                raise HTTPException(409, "MCP 历史资源标识重复，请人工核对")
            seen.add(metadata["id"])
            if metadata["id"] == path.stem and metadata["owner"] == username and metadata["expires"] > time.time():
                resources.append(resource_metadata(metadata))
    return resources


async def list_resources() -> list[dict]:
    identity = await authenticated_identity()
    resources = await run_in_threadpool(_list, identity["username"])
    async with SessionLocal() as db:
        records = (await db.scalars(select(BusinessRecord).where(
            BusinessRecord.module == FILE_MODULE, BusinessRecord.owner == identity["username"],
            BusinessRecord.status == "available",
            BusinessRecord.data["source_kind"].as_string().in_(["mcp_export", "mcp_generated"]),
        ).order_by(BusinessRecord.id.desc()))).all()
        for record in records:
            try:
                await require_generated_record_access(record, identity, db)
            except HTTPException as exc:
                if exc.status_code not in {403, 404}:
                    raise
                continue
            resources.append(resource_metadata(_generated_metadata(generated_file_item(record))))
    return resources


def _load(resource_id: str, username: str) -> tuple[dict, Path]:
    if not _RESOURCE_ID.fullmatch(resource_id):
        raise HTTPException(404, "工具资源不存在")
    matches = []
    for root in _cache_roots():
        if not root.exists():
            continue
        _validate_private_root(root)
        path = root / (resource_id + ".json")
        if path.is_symlink():
            raise OSError("MCP 私有资源元数据不能是符号链接")
        if path.is_file():
            matches.append((root, path))
    if not matches:
        raise HTTPException(404, "工具资源不存在或已过期")
    if len(matches) != 1:
        raise HTTPException(409, "MCP 历史资源标识重复，请人工核对")
    root, path = matches[0]
    try:
        with path.open(encoding="utf-8") as handle:
            metadata = json.load(handle)
    except FileNotFoundError as exc:
        raise HTTPException(404, "工具资源不存在或已过期") from exc
    if metadata["id"] != resource_id or metadata["owner"] != username:
        raise HTTPException(404, "工具资源不存在或不属于当前账号")
    if metadata["expires"] <= time.time():
        raise HTTPException(410, "工具结果已过期，请重新发起查询")
    return metadata, root


def resource_metadata(metadata: dict) -> dict:
    kind = metadata["kind"]
    identifier = metadata["id"]
    result = {
        "type": "resource_link", "uri": f"oa-mcp-{kind}://{identifier}",
        "artifact_id" if kind == "artifact" else "resource_id": identifier,
        "name": metadata["name"], "mimeType": metadata["mime_type"],
        "size": metadata.get("size"), "sha256": metadata.get("sha256"),
        "download_url": settings.api_prefix + f"/agent-tools/{'artifacts' if kind == 'artifact' else 'resources'}/{identifier}",
        "authentication_required": True,
    }
    if metadata.get("persistent"):
        result.update(file_id=identifier, attachment_id=metadata["attachment_id"], persistent=True, storage_backend="oss")
    else:
        result["expires_at"] = datetime.fromtimestamp(metadata["expires"], timezone.utc).isoformat()
    return result


def _generated_metadata(item: dict) -> dict:
    return {
        "id": item["id"], "kind": "artifact", "name": item["name"], "mime_type": item["content_type"],
        "size": item["size"], "sha256": item["sha256"], "attachment_id": item["attachment_id"], "persistent": True,
    }


async def cache_result(
    name: str, mime_type: str, content: bytes, *, conversation_id: str | None = None,
    source_request_id: str | None = None, source_kind: str = "mcp_export",
) -> dict:
    async with SessionLocal() as db:
        identity = await authenticated_identity(db)
        result = await save_generated_file(
            db, identity, name=name, content=content, content_type=mime_type, source_kind=source_kind,
            conversation_id=conversation_id, source_request_id=source_request_id,
        )
    return resource_metadata(_generated_metadata(result["file"]))


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
    await run_in_threadpool(_write, metadata)
    return resource_metadata(metadata)


async def read_resource(resource_id: str, *, expected_kind: str | None = None) -> tuple[dict, bytes]:
    if not _RESOURCE_ID.fullmatch(resource_id):
        raise HTTPException(404, "工具资源不存在")
    identity = await authenticated_identity()
    async with SessionLocal() as db:
        record = await db.scalar(select(BusinessRecord).where(
            BusinessRecord.module == FILE_MODULE, BusinessRecord.serial_no == "AIGF-" + resource_id,
        ))
        if record is not None:
            if record.owner != identity["username"] or expected_kind not in {None, "artifact"}:
                raise HTTPException(404, "工具资源不存在或不属于当前账号")
            await require_generated_record_access(record, identity, db)
            if record.status != "available":
                raise HTTPException(409, {"file_id": resource_id, "status": record.status, "detail": "生成文件尚未完成持久保存"})
            metadata = _generated_metadata(generated_file_item(record))
            if await db.get(FileAttachment, metadata["attachment_id"]) is None:
                raise HTTPException(404, "生成文件附件已不存在")
            endpoint = record.data.get("endpoint")
            if not isinstance(endpoint, str) or not endpoint.strip():
                raise HTTPException(409, "生成文件缺少持久 OSS endpoint，不能猜测历史存储端点")
            source = SimpleNamespace(
                path=record.data["path"], original_name=metadata["name"],
                stored_name=record.data["stored_name"], oss_endpoint=endpoint,
            )
            content = await read_generated_bytes(source)
            if len(content) != metadata["size"] or hashlib.sha256(content).hexdigest() != metadata["sha256"]:
                raise HTTPException(409, "生成文件大小或 SHA256 与持久记录不一致")
            return metadata, content
    metadata, root = await run_in_threadpool(_load, resource_id, identity["username"])
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
        path = root / (resource_id + ".bin")
        if path.is_symlink():
            raise OSError("MCP 私有结果文件不能是符号链接")
        content = await run_in_threadpool(path.read_bytes)
        if len(content) != metadata["size"] or hashlib.sha256(content).hexdigest() != metadata["sha256"]:
            raise HTTPException(409, "工具结果缓存校验失败")
    return metadata, content
