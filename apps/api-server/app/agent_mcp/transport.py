"""通过真实挂载路由执行 OA 请求，不直接调用业务处理函数。"""

from email.message import Message
from email.utils import collapse_rfc2231_value
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


_ATTACHMENT_DOWNLOAD = "/attachments/{attachment_id}/download"
_PDF_PREVIEW_PAGE = "/attachments/{attachment_id}/pdf-preview/pages/{page_number}.png"
_SOURCE_READS = {
    (_ATTACHMENT_DOWNLOAD, "download_attachment"),
    (_PDF_PREVIEW_PAGE, "render_pdf_preview_page"),
    ("/feedback/{feedback_id}/screenshot", "feedback_screenshot"),
    ("/feedback/{feedback_id}/events/{event_id}/screenshot", "feedback_event_screenshot"),
    ("/cases/{case_id}/fee-headers/{header_id}/items/{item_id}/bill/attachment", "get_ipr_fee_bill_attachment"),
}


def _is_source_read(spec) -> bool:
    return (
        not spec.is_write and spec.method == "GET"
        and (spec.path.removeprefix(settings.api_prefix), spec._route.endpoint.__name__) in _SOURCE_READS
    )


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
    if case_origin is not None and spec.path in {settings.api_prefix + _ATTACHMENT_DOWNLOAD, settings.api_prefix + _PDF_PREVIEW_PAGE}:
        supplied_case = query.get("case_id")
        if supplied_case is not None and supplied_case != case_origin:
            raise HTTPException(422, "附件下载的案件编号与可信案件上下文不一致")
        # 案件关联附件每次读取都保留原接口的案件权限链，模型不能替换来源案件。
        query["case_id"] = case_origin
    return query


def _response_name(spec, response) -> str:
    disposition = Message()
    disposition["content-disposition"] = response.headers.get("content-disposition", "")
    filenames = [value for key, value in disposition.get_params(header="content-disposition", unquote=True) or [] if key == "filename"]
    # 同时存在 ASCII 名称与 filename* 时，以接口给出的扩展真实名称为准。
    extended = [value for value in filenames if isinstance(value, tuple)]
    if len(extended) > 1:
        raise HTTPException(502, "原接口返回了多个真实文件名，不能确定导出文件")
    try:
        value = collapse_rfc2231_value(extended[0], errors="strict") if extended else disposition.get_filename()
    except (UnicodeError, LookupError) as exc:
        raise HTTPException(502, "原接口真实文件名编码无效") from exc
    if not value:
        raise HTTPException(502, "原接口未返回真实文件名，不能猜测导出格式")
    from app.core.generated_file_storage import safe_original_name

    return safe_original_name(value)


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
    if not _is_source_read(spec):
        raise HTTPException(409, "此下载跳转没有已核实的受信资源读取通道")
    path = render_path(spec, params)
    _require_route(spec, path)
    async with _client() as client:
        response = await client.get(path, params=_query_pairs(_authorized_query(spec, params, case_origin)))
    # 每次引用读取都重新执行原授权路由，不将预览或原件变为长期生成副本。
    if spec.path == settings.api_prefix + _ATTACHMENT_DOWNLOAD:
        _, content, _ = await _trusted_attachment_bytes(params["path"]["attachment_id"], response)
        return content
    _raise_response_error(response)
    if not response.is_success:
        raise HTTPException(409, "源读取未返回受信字节，不跟随或暴露跳转地址")
    return response.content


async def execute_original(
    spec, params: dict, *, case_origin: int | None = None,
    conversation_id: str | None = None, source_request_id: str | None = None,
):
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
    if _is_source_read(spec):
        if spec.path == settings.api_prefix + _ATTACHMENT_DOWNLOAD:
            async with SessionLocal() as db:
                attachment = await db.get(FileAttachment, params["path"]["attachment_id"])
                if attachment is None:
                    raise HTTPException(404, "下载附件不存在")
                name, mime_type = attachment.original_name, attachment.content_type
        else:
            if not response.is_success:
                raise HTTPException(409, "源读取未返回受信字节，不跟随或暴露跳转地址")
            name = _response_name(spec, response)
            mime_type = response.headers.get("content-type", "application/octet-stream").split(";")[0]
        try:
            return await cache_source(spec, params, case_origin, name=name, mime_type=mime_type)
        except OSError as exc:
            raise HTTPException(503, "原接口已授权源读取，但私有源引用保存失败") from exc
    if response.is_redirect:
        raise HTTPException(409, "接口返回跳转，但不存在已核实的安全结果通道；不会跟随或暴露签名地址")
    if response.status_code == 204 or not response.content:
        return {"status_code": response.status_code}
    content_type = response.headers.get("content-type", "application/octet-stream").lower()
    if "attachment" not in response.headers.get("content-disposition", "").lower() and "json" in content_type:
        return safe_result(response.json(), context.bearer)
    # 原业务接口只执行一次；生成字节交给统一 OSS 服务，失败不得重放原写接口。
    try:
        return await cache_result(
            _response_name(spec, response), content_type.split(";")[0], response.content,
            conversation_id=conversation_id, source_request_id=source_request_id,
            source_kind="mcp_generated" if spec.is_write else "mcp_export",
        )
    except OSError as exc:
        raise HTTPException(503, "原接口已返回结果，但私有工具结果缓存失败；写操作请人工核对实际结果，禁止自动重试") from exc
