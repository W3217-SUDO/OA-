"""本人个人生成文件的精确对象删除及可恢复墓碑，不级联版本或会话。"""

import asyncio
import base64
from datetime import datetime, timezone
from email.utils import formatdate
import hashlib
import hmac
from pathlib import PurePosixPath
import re
from types import SimpleNamespace
from urllib.parse import quote

from fastapi import HTTPException
import httpx
from sqlalchemy import select, update

from app.config import settings
from app.core.generated_file_records import (
    FILE_MODULE, SPACE_MODULE, actual_user, generated_storage_config, generated_storage_endpoint,
)
from app.core.oss_attachments import _endpoint_host, _load_credentials, oss_attachment_location
from app.data_models.documents import FileAttachment
from app.data_models.records import BusinessRecord


DELETE_STATUSES = frozenset({"deleting", "delete_failed", "delete_uncertain"})


def _now():
    return datetime.now(timezone.utc).isoformat()


class BlobDeleteFailure(HTTPException):
    def __init__(self, detail, *, uncertain, evidence=None):
        super().__init__(502, detail)
        self.uncertain = uncertain
        self.evidence = evidence or {}


async def _locked_file(db, file_id):
    record = await db.scalar(select(BusinessRecord).where(
        BusinessRecord.module == FILE_MODULE, BusinessRecord.serial_no == "AIGF-" + file_id,
    ).with_for_update().execution_options(populate_existing=True))
    if record is None:
        raise HTTPException(404, "生成文件不存在")
    return record


def _owner(record, user, expected_sha256):
    data = record.data or {}
    if data.get("owner_user_id") != user.id or record.owner != user.username:
        raise HTTPException(403, "只能删除本人个人生成文件，管理员不能代删他人文件")
    if data.get("case_id") is not None:
        raise HTTPException(409, "案件生成文件须通过原案件生命周期管理，不能从个人文件夹删除")
    if data.get("source_kind") == "personal_identity":
        raise HTTPException(409, "系统维护的个人身份文件不能删除")
    if data.get("sha256") != expected_sha256:
        raise HTTPException(409, "文件 SHA256 已变化，请刷新后重新确认")


async def _binding(db, record, user):
    data = record.data
    attachment = await db.scalar(select(FileAttachment).where(
        FileAttachment.id == data.get("attachment_id"),
    ).with_for_update().execution_options(populate_existing=True))
    if (attachment is None or attachment.record_id != record.id or attachment.category != "个人AI空间"
            or attachment.path != data.get("path") or attachment.stored_name != data.get("stored_name")
            or attachment.stored_name != data.get("file_id") or attachment.uploader != user.username
            or attachment.original_name != data.get("name") or attachment.size != data.get("size")):
        raise HTTPException(409, "生成文件附件归属或精确版本映射不一致，未删除对象")
    space = await db.scalar(select(BusinessRecord).where(
        BusinessRecord.id == data.get("space_id"), BusinessRecord.module == SPACE_MODULE,
    ))
    bucket, prefix = generated_storage_config()
    endpoint = generated_storage_endpoint()
    mapped = space.data if space is not None else {}
    folder = mapped.get("folder")
    location = oss_attachment_location(attachment)
    if (space is None or space.owner != user.username or mapped.get("owner_user_id") != user.id
            or mapped.get("bucket") != bucket or mapped.get("endpoint") != endpoint
            or data.get("endpoint") != endpoint or not isinstance(folder, str)
            or not folder.startswith(prefix + "/personal/") or not folder.endswith(f"--u{user.id}")
            or "\\" in folder or any(part in {"", ".", ".."} for part in folder.split("/"))
            or not re.fullmatch(r"[a-f0-9]{32}", str(data.get("file_id") or ""))
            or not re.fullmatch(r"[a-f0-9]{64}", str(data.get("sha256") or ""))
            or not isinstance(data.get("name"), str) or "\\" in data["name"]
            or PurePosixPath(data["name"]).name != data["name"]
            or location != (bucket, f"{folder}/{data['file_id']}/{data['sha256']}/{data['name']}")):
        raise HTTPException(409, "个人生成文件对象路径与持久空间映射不一致，未删除对象")
    other_attachment = await db.scalar(select(FileAttachment.id).where(
        FileAttachment.path == attachment.path, FileAttachment.id != attachment.id,
    ).limit(1))
    other_file = await db.scalar(select(BusinessRecord.id).where(
        BusinessRecord.module == FILE_MODULE, BusinessRecord.id != record.id,
        BusinessRecord.data["path"].as_string() == attachment.path,
    ).limit(1))
    if other_attachment is not None or other_file is not None:
        raise HTTPException(409, "对象仍有其他附件或生成版本引用，不能删除")
    return attachment, location


def _headers(method, bucket, key, credentials):
    access_key, secret = credentials
    date = formatdate(usegmt=True)
    signing = f"{method}\n\n\n{date}\n/{bucket}/{key}"
    signature = base64.b64encode(hmac.new(secret.encode(), signing.encode(), hashlib.sha1).digest()).decode("ascii")
    return {"Date": date, "Authorization": f"OSS {access_key}:{signature}"}


async def delete_personal_blob(plan):
    """只删除当前对象，不传 versionId；404 才确认当前对象不可读取。"""
    bucket, key = plan["bucket"], plan["key"]
    scheme, host = _endpoint_host(plan["endpoint"])
    credentials = _load_credentials(settings.ai_oss_credentials_file)
    url = f"{scheme}://{bucket}.{host}/{quote(key, safe='/~')}"
    attempted = False
    evidence = {}
    try:
        async with httpx.AsyncClient(timeout=60, follow_redirects=False, trust_env=False) as client:
            # 删除前按原记录核验正文，避免仅凭 204 或同名对象推断删除了正确版本。
            async with client.stream("GET", url, headers=_headers("GET", bucket, key, credentials)) as response:
                if response.status_code == 404:
                    return {"blob_status": "absent", "checked_at": _now(), "historical_versions_purged": False}
                if response.status_code != 200:
                    raise BlobDeleteFailure(f"OSS 删除前读取失败（HTTP {response.status_code}），未确认删除", uncertain=False)
                size = 0
                digest = hashlib.sha256()
                async for chunk in response.aiter_bytes():
                    size += len(chunk)
                    if size > plan["size"]:
                        raise BlobDeleteFailure("OSS 对象大小与删除计划不一致，未删除", uncertain=False)
                    digest.update(chunk)
                if size != plan["size"] or digest.hexdigest() != plan["sha256"]:
                    raise BlobDeleteFailure("OSS 对象 SHA256 与删除计划不一致，未删除", uncertain=False)
            attempted = True
            response = await client.delete(url, headers=_headers("DELETE", bucket, key, credentials))
            if response.status_code != 204:
                raise BlobDeleteFailure(
                    f"OSS 当前对象删除被拒绝或失败（HTTP {response.status_code}），请核对删除权限及存储保留策略",
                    uncertain=response.status_code not in {400, 401, 403, 405},
                )
            evidence = {"delete_marker": response.headers.get("x-oss-delete-marker") == "true",
                        "oss_version_id": response.headers.get("x-oss-version-id"), "historical_versions_purged": False}
            checked = await client.head(url, headers=_headers("HEAD", bucket, key, credentials))
            if checked.status_code != 404:
                raise BlobDeleteFailure(f"OSS 删除后当前对象未确认不可读（HTTP {checked.status_code}），请显式核对或重试", uncertain=True, evidence=evidence)
            return {**evidence, "blob_status": "absent", "checked_at": _now()}
    except httpx.HTTPError as exc:
        raise BlobDeleteFailure("OSS 删除请求或核对网络失败，当前对象状态未确认", uncertain=attempted, evidence=evidence) from exc


async def _delete_failure(db, record_id, operation_id, error):
    await db.rollback()
    record = await db.scalar(select(BusinessRecord).where(
        BusinessRecord.id == record_id, BusinessRecord.module == FILE_MODULE,
    ).with_for_update().execution_options(populate_existing=True))
    if record is None or (record.data.get("delete_plan") or {}).get("operation_id") != operation_id:
        raise HTTPException(503, "删除结果无法核对，原对象计划需人工检查") from error
    if record.status == "deleted" and record.data["delete_plan"].get("blob_status") == "absent":
        return "deleted"
    status = "delete_failed" if isinstance(error, BlobDeleteFailure) and not error.uncertain else "delete_uncertain"
    reason = str(error.detail) if isinstance(error, HTTPException) else "删除处理被中断或提交未确认，请显式核对原计划"
    record.status = status
    record.data = {**record.data, "error": reason, "delete_plan": {
        **record.data["delete_plan"], **(error.evidence if isinstance(error, BlobDeleteFailure) else {}),
        "last_error": reason, "last_checked_at": _now(),
    }}
    await db.commit()
    return status


async def delete_space_file(file_id, expected_sha256, identity, db):
    actual = await actual_user(db, identity)
    # 回滚会使 ORM 身份对象过期，删除计划只保留本次已认证的不可变账号标识。
    user = SimpleNamespace(id=actual.id, username=actual.username)
    record = await _locked_file(db, file_id)
    _owner(record, user, expected_sha256)
    operation_id = hashlib.sha256(f"personal-ai-delete:{file_id}:{expected_sha256}".encode()).hexdigest()
    previous = record.data.get("delete_plan")
    if previous is not None and previous.get("operation_id") != operation_id:
        raise HTTPException(409, "文件存在不同的删除计划，请人工核对")
    result = {"id": file_id, "status": "deleted", "blob_status": "absent"}
    if record.status == "deleted":
        if previous is None or previous.get("blob_status") != "absent":
            raise HTTPException(409, "文件墓碑缺少已确认的删除证据，请人工核对")
        return result
    if record.status not in {"available", *DELETE_STATUSES}:
        raise HTTPException(409, "仅可删除已完成保存的个人文件或显式重试原删除计划")
    attachment, (bucket, key) = await _binding(db, record, user)
    # Personal-space deletion is intentionally a logical delete.  Keep the
    # immutable attachment/blob and any DingTalk dentry for the retention
    # cleanup job; the list query hides records with status=deleted.
    record.status = "deleted"
    record.data = {**record.data, "error": None, "deleted_at": _now(),
                   "delete_plan": {"operation_id": operation_id, "owner_user_id": user.id,
                                   "requested_by": user.username, "requested_at": _now(),
                                   "attachment_id": attachment.id, "path": record.data["path"],
                                   "endpoint": record.data["endpoint"], "bucket": bucket,
                                   "key": key, "sha256": expected_sha256, "size": record.data["size"],
                                   "blob_status": "retained", "cleanup_status": "pending"}}
    await db.commit()
    return {"id": file_id, "status": "deleted", "blob_status": "retained"}

    # The guarded physical-delete implementation below remains available for
    # the retention cleanup worker, which will use the persisted plan.
    plan = {"operation_id": operation_id, "owner_user_id": user.id, "requested_by": user.username,
            "requested_at": _now(), "attachment_id": attachment.id, "path": record.data["path"],
            "endpoint": record.data["endpoint"], "bucket": bucket, "key": key,
            "sha256": expected_sha256, "size": record.data["size"], "blob_status": "pending"}
    if previous is not None:
        for field in ("owner_user_id", "attachment_id", "path", "endpoint", "bucket", "key", "sha256", "size"):
            if previous.get(field) != plan[field]:
                raise HTTPException(409, "原删除计划与精确对象映射不一致，禁止重放")
        plan = dict(previous)
    record_id = record.id
    changed = await db.execute(update(BusinessRecord).where(
        BusinessRecord.id == record_id, BusinessRecord.module == FILE_MODULE, BusinessRecord.status == record.status,
    ).values(status="deleting", data={**record.data, "delete_plan": plan, "error": None})
        .execution_options(synchronize_session=False))
    if changed.rowcount != 1:
        await db.rollback()
        current = await _locked_file(db, file_id)
        _owner(current, user, expected_sha256)
        if (current.status == "deleted" and (current.data.get("delete_plan") or {}).get("operation_id") == operation_id
                and current.data["delete_plan"].get("blob_status") == "absent"):
            return result
        raise HTTPException(409, "文件删除状态已由其他请求改变，请刷新核对原操作")
    # 先提交对象计划；此后即使进程退出，也可按同一文件 ID 和哈希显式恢复。
    try:
        await db.commit()
    except Exception as exc:
        await db.rollback()
        raise HTTPException(503, "删除计划未确认持久化，未执行 OSS 删除；请刷新核对原计划") from exc
    try:
        record = await _locked_file(db, file_id)
        _owner(record, user, expected_sha256)
        if record.status == "deleted" and record.data["delete_plan"].get("blob_status") == "absent":
            return result
        if record.status not in DELETE_STATUSES or record.data["delete_plan"] != plan:
            raise HTTPException(409, "删除计划已变化，请刷新核对")
        attachment, _ = await _binding(db, record, user)
        # 行锁覆盖外部删除和最终提交，同一对象的读取、编辑与重试不能越过墓碑状态。
        evidence = await delete_personal_blob(plan)
        if evidence.get("blob_status") != "absent":
            raise HTTPException(502, "对象未确认不可读，未提交删除成功状态")
        await db.delete(attachment)
        record.status = "deleted"
        record.data = {**record.data, "error": None, "deleted_at": _now(), "delete_plan": {**plan, **evidence}}
        await db.commit()
    except asyncio.CancelledError as exc:
        await _delete_failure(db, record_id, operation_id, exc)
        raise
    except Exception as exc:
        status = await _delete_failure(db, record_id, operation_id, exc)
        if status == "deleted":
            return result
        raise HTTPException(exc.status_code if isinstance(exc, HTTPException) else 503, {
            "file_id": file_id, "operation_id": operation_id, "status": status,
            "detail": str(exc.detail) if isinstance(exc, HTTPException) else "删除未确认完成，原计划已保留，请显式核对或重试",
        }) from exc
    return result
