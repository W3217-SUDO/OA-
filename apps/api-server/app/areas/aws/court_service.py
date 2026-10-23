"""按法院短信送达链接下载文书并存为附件，供智能体收文；识别要素与收文技能脚本共用同一份代码。"""

import asyncio
import ipaddress
from io import BytesIO
import socket
from urllib.parse import urljoin, urlsplit

import httpx
from fastapi import APIRouter, Depends, HTTPException, UploadFile
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.datastructures import Headers

from app.agent_skill_packages.court_doc_intake.scripts import fetch_court_docs as court_api
from app.agent_skill_packages.court_doc_intake.scripts.extract_doc_fields import extract
from app.core.dependencies import current_identity, get_db, settings
from app.models import FileAttachment

router = APIRouter()

CATEGORY = "法院送达文书"
ALLOWED_EXTENSIONS = {"pdf", "doc", "docx", "jpg", "jpeg", "png", "txt", "zip", "rar"}
MAX_DOCUMENTS = 30
EXCERPT_CHARS = 3000


def _client() -> httpx.AsyncClient:
    return httpx.AsyncClient(timeout=30, trust_env=False, follow_redirects=False)


class CourtServiceFetchInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    link: str = Field(min_length=20, max_length=2000, description="法院短信里的完整送达链接（https://zxfw.court.gov.cn/...），可连同短信正文一起粘贴")


def _public_host(host: str) -> None:
    """下载地址由法院接口返回，只许解析到公网地址，防止被引向服务器内网。"""
    try:
        addresses = {item[4][0] for item in socket.getaddrinfo(host, 443, proto=socket.IPPROTO_TCP)}
    except OSError as exc:
        raise HTTPException(502, f"法院文书地址无法解析：{host}") from exc
    if not addresses or any(not ipaddress.ip_address(address.split("%", 1)[0]).is_global for address in addresses):
        raise HTTPException(502, "法院文书地址指向非公网地址，已拒绝下载")


async def _get(client: httpx.AsyncClient, url: str, limit: int) -> bytes:
    for _ in range(4):
        parts = urlsplit(url)
        if parts.scheme not in {"https", "http"} or not parts.hostname:
            raise HTTPException(502, "法院返回的文书地址无效")
        await asyncio.to_thread(_public_host, parts.hostname)
        async with client.stream("GET", url, headers={"User-Agent": court_api.USER_AGENT, "Referer": court_api.REFERER}) as response:
            if response.status_code in {301, 302, 303, 307, 308} and response.headers.get("location"):
                url = urljoin(url, response.headers["location"])
                continue
            if response.status_code != 200:
                raise HTTPException(502, f"法院文书下载失败（HTTP {response.status_code}）")
            content = bytearray()
            async for chunk in response.aiter_bytes():
                content.extend(chunk)
                if len(content) > limit:
                    raise HTTPException(413, "法院文书超过 20MB 上限")
            return bytes(content)
    raise HTTPException(502, "法院文书地址跳转次数过多")


async def _list_documents(client: httpx.AsyncClient, params: dict) -> list[dict]:
    try:
        response = await client.post(court_api.API, content=court_api.request_body(params), headers=court_api.headers())
        payload = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise HTTPException(502, "法院送达接口暂时无法访问，请稍后重试") from exc
    try:
        documents = court_api.documents_from_response(payload)
    except ValueError as exc:
        raise HTTPException(422, f"{exc}；请确认链接完整且未过期") from exc
    if not documents:
        raise HTTPException(404, "该送达链接下没有可下载的文书")
    return documents[:MAX_DOCUMENTS]


async def _reading(item: FileAttachment, username: str) -> tuple[str, str]:
    from app.agent_attachment_reader import read_attachment
    from app.core.storage import _attachment_storage_path
    path = _attachment_storage_path(item)
    if path is None:
        return "unavailable", ""
    try:
        result = await asyncio.to_thread(read_attachment, path, item.original_name,
                                         cache_scope=username, attachment_id=item.id)
    except Exception:
        return "failed", ""
    return result.status, result.text


@router.post(f"{settings.api_prefix}/documents/court-service/fetch", status_code=201)
async def fetch_court_service_documents(body: CourtServiceFetchInput, identity: dict = Depends(current_identity),
                                        db: AsyncSession = Depends(get_db)):
    """下载法院送达文书：按短信链接从人民法院在线服务取出全部文书，存为未关联附件并识别收文要素。

    返回的 attachment_id 用于“上传官方收文”的 files.file；同一文书重复送达时复用已下载的附件。
    """
    from app.areas.system.attachments import upload_attachment
    from app.core.storage import _attachment_dict
    try:
        params = court_api.parse_service_link(body.link)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    results = []
    async with _client() as client:
        documents = await _list_documents(client, params)
        for document in documents:
            extension = document["extension"] if document["extension"] in ALLOWED_EXTENSIONS else "pdf"
            filename = f"{document['name']}.{extension}"
            marker = f"法院送达:{params['sdbh']}:{document['document_no'] or document['name']}"
            item = await db.scalar(select(FileAttachment).where(
                FileAttachment.category == CATEGORY, FileAttachment.remark == marker,
                FileAttachment.uploader == identity["username"]).order_by(FileAttachment.id.desc()))
            reused = item is not None
            if item is None:
                content = await _get(client, document["url"], court_api.MAX_FILE)
                if not content:
                    raise HTTPException(502, f"法院文书为空：{filename}")
                content_type = "application/pdf" if content.startswith(b"%PDF") else "application/octet-stream"
                upload = UploadFile(BytesIO(content), filename=filename, headers=Headers({"content-type": content_type}))
                saved = await upload_attachment(file=upload, record_id=None, finance_transaction_id=None, source_case_id=None,
                                                customer_guid=None, is_license=None, document_date=None,
                                                category=CATEGORY, remark=marker, identity=identity, db=db)
                item = await db.get(FileAttachment, int(saved["id"]))
            status, text = await _reading(item, identity["username"])
            results.append({
                "attachment_id": item.id, "name": item.original_name, "size": item.size, "reused": reused,
                "court": document["court"], "document_no": document["document_no"],
                "reading_status": status, "fields": extract(text, document["name"]),
                "text_excerpt": text[:EXCERPT_CHARS], "text_characters": len(text),
                "attachment": _attachment_dict(item),
            })
    numbers = list(dict.fromkeys(number for item in results for number in item["fields"]["官方案号"]))
    return {
        "court": results[0]["court"] if results else "", "count": len(results), "documents": results,
        "case_numbers": numbers,
        "next_step": "按收文技能两级匹配案件；唯一匹配后对每份文书调用“上传官方收文”，files.file 填 attachment_id，"
                     "body 填 case_id、court_case_no、document_date。",
    }
