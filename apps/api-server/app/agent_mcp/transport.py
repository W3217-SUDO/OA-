"""通过真实挂载路由执行 OA 请求，不直接调用业务处理函数。"""

from email.message import Message
import json
from urllib.parse import unquote

from fastapi import HTTPException
from fastapi.routing import APIRoute
import httpx
from starlette.routing import Match

from app.agent_mcp.artifacts import cache_result, cache_source
from app.agent_mcp.auth import get_auth_context
from app.agent_mcp.config import oa_base_url
from app.agent_mcp.safety import render_path, safe_result
from app.config import settings
from app.database import SessionLocal
from app.models import FileAttachment


def _require_route(spec, path: str) -> None:
    application = get_auth_context().application
    scope = {"type": "http", "path": unquote(path), "root_path": "", "method": spec.method}
    for route in application.routes:
        match, _ = route.matches(scope)
        if match == Match.FULL:
            if isinstance(route, APIRoute) and route.path == spec.path and spec.method in route.methods:
                return
            break
    raise HTTPException(422, "参数解析后的目标不再是选定的 OA 业务接口")


def _query_pairs(values: dict) -> list[tuple[str, str]]:
    pairs = []
    for key, value in values.items():
        if value is None:
            continue
        for item in value if isinstance(value, list) else [value]:
            pairs.append((key, str(item).lower() if isinstance(item, bool) else str(item)))
    return pairs


def _authorized_query(spec, params: dict, case_origin: int | None) -> dict:
    query = dict(params["query"])
    if case_origin is not None and spec.path == settings.api_prefix + "/attachments/{attachment_id}/download":
        supplied_case = query.get("case_id")
        if supplied_case is not None and supplied_case != case_origin:
            raise HTTPException(422, "附件下载的案件编号与可信案件上下文不一致")
        # 案件关联附件每次读取都保留原接口的案件权限链，模型不能替换来源案件。
        query["case_id"] = case_origin
    return query


def _response_name(spec, response) -> str:
    disposition = Message()
    disposition["content-disposition"] = response.headers.get("content-disposition", "")
    return disposition.get_filename() or spec.name


def _raise_response_error(response) -> None:
    if response.status_code < 400:
        return
    context = get_auth_context()
    content_type = response.headers.get("content-type", "")
    detail = response.json() if "json" in content_type else {"detail": response.text[:2000]}
    raise HTTPException(response.status_code, safe_result(detail, context.bearer))


async def _trusted_attachment_bytes(attachment_id: int, response):
    _raise_response_error(response)
    async with SessionLocal() as db:
        attachment = await db.get(FileAttachment, attachment_id)
        if attachment is None:
            raise HTTPException(404, "复用的附件不存在")
        filename = attachment.original_name
        content_type = attachment.content_type
        if response.status_code in {302, 307}:
            from app.core.oss_attachments import oss_attachment_location, oss_attachment_signed_url

            # 不跟随 Location，只从已通过原下载鉴权的附件存储元数据构造受信 OSS 请求。
            if oss_attachment_location(attachment) is None:
                raise HTTPException(409, "附件下载跳转没有可用的受信文件复用通道")
            signed_url = oss_attachment_signed_url(attachment)
            try:
                async with httpx.AsyncClient(follow_redirects=False, timeout=60) as storage_client:
                    storage_response = await storage_client.get(signed_url)
            except httpx.HTTPError as exc:
                raise HTTPException(502, "受信附件对象存储读取失败") from exc
            if not storage_response.is_success:
                raise HTTPException(502, f"受信附件对象存储拒绝读取（HTTP {storage_response.status_code}）")
            content = storage_response.content
        elif response.is_success:
            content = response.content
        else:
            raise HTTPException(409, "附件下载没有可用的安全文件复用通道")
        if len(content) != attachment.size:
            raise HTTPException(409, "复用附件大小与存储元数据不一致")
    return filename, content, content_type


async def _attachment_file(client, attachment_id: int, case_id: int | None):
    response = await client.get(
        settings.api_prefix + f"/attachments/{attachment_id}/download",
        params={"case_id": case_id} if case_id is not None else {},
    )
    return await _trusted_attachment_bytes(attachment_id, response)


def _client():
    context = get_auth_context()
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=context.application, raise_app_exceptions=False),
        base_url=oa_base_url(), headers={"Authorization": f"Bearer {context.bearer}"},
        follow_redirects=False, timeout=120,
    )


async def read_source(spec, params: dict, *, case_origin: int | None) -> bytes:
    if spec.is_write or spec.method != "GET" or spec.path != settings.api_prefix + "/attachments/{attachment_id}/download":
        raise HTTPException(409, "此下载跳转没有已核实的受信资源读取通道")
    path = render_path(spec, params)
    _require_route(spec, path)
    async with _client() as client:
        response = await client.get(path, params=_query_pairs(_authorized_query(spec, params, case_origin)))
    # 每次资源读取先执行原附件下载权限，再读取该已授权附件的实际存储对象。
    _, content, _ = await _trusted_attachment_bytes(params["path"]["attachment_id"], response)
    return content


async def execute_original(spec, params: dict, *, case_origin: int | None = None):
    context = get_auth_context()
    path = render_path(spec, params)
    _require_route(spec, path)
    async with _client() as client:
        options = {"params": _query_pairs(_authorized_query(spec, params, case_origin))}
        if spec.request_media_type == "multipart/form-data":
            files = []
            for field, values in params["files"].items():
                for attachment_id in values if isinstance(values, list) else [values]:
                    files.append((field, await _attachment_file(client, attachment_id, case_origin)))
            data = {}
            for key, value in (params["body"] or {}).items():
                if value is not None:
                    data[key] = json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, bool)) else value
            options.update(data=data, files=files)
        elif spec.request_media_type == "application/x-www-form-urlencoded":
            options["data"] = params["body"] or {}
        elif params["body"] is not None:
            options["json"] = params["body"]
        response = await client.request(spec.method, path, **options)
    _raise_response_error(response)
    if response.is_redirect:
        if spec.is_write or spec.method != "GET" or spec.path != settings.api_prefix + "/attachments/{attachment_id}/download":
            raise HTTPException(409, "接口返回跳转，但不存在已核实的安全结果通道；不会跟随或暴露签名地址")
        async with SessionLocal() as db:
            attachment = await db.get(FileAttachment, params["path"]["attachment_id"])
            if attachment is None:
                raise HTTPException(404, "下载附件不存在")
            return await cache_source(spec, params, case_origin, name=attachment.original_name, mime_type=attachment.content_type)
    if response.status_code == 204 or not response.content:
        return {"status_code": response.status_code}
    content_type = response.headers.get("content-type", "application/octet-stream").lower()
    if "attachment" not in response.headers.get("content-disposition", "").lower() and "json" in content_type:
        return safe_result(response.json(), context.bearer)
    # 查询导出和写操作生成的字节只缓存一次；读取结果不能重放原写接口。
    try:
        return await cache_result(_response_name(spec, response), content_type.split(";")[0], response.content)
    except OSError as exc:
        raise HTTPException(503, "原接口已返回结果，但私有工具结果缓存失败；写操作请人工核对实际结果，禁止自动重试") from exc
