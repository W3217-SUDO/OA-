"""钉钉存储及原生 Office 编辑接口，沿用现有企业应用凭证。"""

import hashlib
import re
from urllib.parse import quote, urlsplit

import httpx
from fastapi import HTTPException

from app.dingtalk import DingTalkError, dingtalk_client
from app.core.generated_file_storage import MAX_GENERATED_BYTES


def provider_url(value: str, *, editor: bool = False) -> str:
    parsed = urlsplit(value)
    host = parsed.hostname or ""
    allowed = ("dingtalk.com",) if editor else ("dingtalk.com", "aliyuncs.com")
    if (parsed.scheme != "https" or parsed.username or parsed.password or parsed.port not in {None, 443}
            or not any(host == domain or host.endswith("." + domain) for domain in allowed)):
        raise HTTPException(502, "钉钉返回的文件地址不符合安全要求")
    return value


def identifier(value) -> str:
    if not isinstance(value, str) or not value or len(value) > 256 or re.search(r"[\x00-\x20/\\?#]", value):
        raise HTTPException(502, "钉钉返回的文件或空间标识无效")
    return quote(value, safe="")


async def _token() -> str:
    try:
        return await dingtalk_client.access_token()
    except (DingTalkError, httpx.HTTPError, ValueError) as exc:
        raise HTTPException(503, "钉钉企业应用凭证不可用，请检查应用配置") from exc


async def member_union_id(user_id: str) -> str:
    token = await _token()
    try:
        async with httpx.AsyncClient(timeout=15, trust_env=False, follow_redirects=False) as client:
            response = await client.post("https://oapi.dingtalk.com/topapi/v2/user/get",
                                         params={"access_token": token}, json={"userid": user_id})
            if response.status_code != 200:
                raise HTTPException(502, "钉钉员工身份查询失败")
            body = response.json()
            result = body.get("result") if isinstance(body, dict) else None
            if (not isinstance(body, dict) or type(body.get("errcode")) is not int or body["errcode"] != 0
                    or not isinstance(result, dict) or result.get("userid") != user_id):
                raise HTTPException(403, "当前绑定账号不在钉钉应用的通讯录授权范围，或身份返回不一致")
            union_id = result.get("unionid")
            identifier(union_id)
            # 员工详情不提供 contact_type；沿用扫码登录的 UnionId 反查合同核验内部员工。
            member_response = await client.post("https://oapi.dingtalk.com/topapi/user/getbyunionid",
                                                params={"access_token": token}, json={"unionid": union_id})
            if member_response.status_code != 200:
                raise HTTPException(502, "钉钉企业成员身份查询失败")
            member_body = member_response.json()
            member = member_body.get("result") if isinstance(member_body, dict) else None
            if (not isinstance(member_body, dict) or type(member_body.get("errcode")) is not int
                    or member_body["errcode"] != 0 or not isinstance(member, dict)
                    or type(member.get("contact_type")) is not int or member["contact_type"] != 0
                    or member.get("userid") != user_id):
                raise HTTPException(403, "当前绑定账号不是钉钉应用所属企业的内部员工，或成员身份不一致")
        return union_id
    except (httpx.HTTPError, ValueError) as exc:
        raise HTTPException(502, "钉钉员工身份查询未完成") from exc


async def storage_request(method: str, path: str, union_id: str, body: dict | None = None) -> dict:
    token = await _token()
    try:
        async with httpx.AsyncClient(timeout=30, trust_env=False, follow_redirects=False) as client:
            response = await client.request(method, "https://api.dingtalk.com/v1.0/storage/" + path,
                                            params={"unionId": union_id}, json=body,
                                            headers={"x-acs-dingtalk-access-token": token})
        if not 200 <= response.status_code < 300:
            error = response.json()
            code = str(error.get("code", "")) if isinstance(error, dict) else ""
            # 不回传包含临时签名或用户资料的供应商原始响应。
            safe_code = code if re.fullmatch(r"[A-Za-z0-9_.-]{1,100}", code) else "provider_error"
            raise HTTPException(403 if response.status_code == 403 else 502,
                                f"钉钉文件操作失败（HTTP {response.status_code}，{safe_code}），请核对文件权限及 Office 服务")
        result = response.json()
        if not isinstance(result, dict):
            raise HTTPException(502, "钉钉文件接口响应格式无效")
        return result
    except (httpx.HTTPError, ValueError) as exc:
        raise HTTPException(502, "钉钉文件操作未获得有效响应，请核对操作状态后再处理") from exc


def _signed_resource(body: dict) -> tuple[str, dict]:
    info = body.get("headerSignatureInfo")
    if body.get("protocol") != "HEADER_SIGNATURE" or not isinstance(info, dict):
        raise HTTPException(502, "钉钉未返回受支持的文件传输协议")
    urls, headers = info.get("resourceUrls"), info.get("headers")
    if (not isinstance(urls, list) or not urls or not isinstance(urls[0], str)
            or not isinstance(headers, dict) or not all(isinstance(k, str) and isinstance(v, str) for k, v in headers.items())):
        raise HTTPException(502, "钉钉文件传输信息不完整")
    if any("\r" in k + v or "\n" in k + v for k, v in headers.items()):
        raise HTTPException(502, "钉钉文件传输请求头无效")
    return provider_url(urls[0]), headers


async def upload_copy(space_id: str, union_id: str, name: str, content: bytes) -> dict:
    base = "spaces/" + identifier(space_id)
    info = await storage_request("POST", base + "/files/uploadInfos/query", union_id, {
        "protocol": "HEADER_SIGNATURE", "multipart": False,
        "option": {"storageDriver": "DINGTALK", "preferIntranet": False,
                   "preCheckParam": {"name": name, "parentId": "0", "size": len(content),
                                     "md5": hashlib.md5(content, usedforsecurity=False).hexdigest()}},
    })
    upload_key = info.get("uploadKey")
    if not isinstance(upload_key, str) or not upload_key:
        raise HTTPException(502, "钉钉未返回文件上传标识")
    url, headers = _signed_resource(info)
    try:
        async with httpx.AsyncClient(timeout=60, trust_env=False, follow_redirects=False) as client:
            response = await client.put(url, headers=headers, content=content)
        if response.status_code not in {200, 201, 204}:
            raise HTTPException(502, f"钉钉文件副本上传失败（HTTP {response.status_code}）")
    except httpx.HTTPError as exc:
        raise HTTPException(502, "钉钉文件副本上传结果无法确认") from exc
    result = await storage_request("POST", base + "/files/commit", union_id, {
        "name": name, "parentId": "0", "uploadKey": upload_key, "option": {"size": len(content)},
    })
    if not isinstance(result.get("dentry"), dict):
        raise HTTPException(502, "钉钉未返回已提交的文件信息")
    return result["dentry"]


async def dentry_info(session: dict) -> dict:
    base = "spaces/" + identifier(session["space_id"]) + "/dentries/" + identifier(session["dentry_id"])
    result = await storage_request("POST", base + "/query", session["union_id"], {})
    dentry = result.get("dentry")
    allowed_extensions = {"docx", "xlsx", "xls"}
    expected_extension = str(session.get("office_extension") or "").lower()
    if (not isinstance(dentry, dict) or dentry.get("id") != session["dentry_id"]
            or dentry.get("spaceId") != session["space_id"]
            # DingTalk returns FILE in the storage API (the docs/examples also
            # use lowercase in places); treat the enum case-insensitively.
            or str(dentry.get("type", "")).upper() != "FILE"
            or dentry.get("status") != "NORMAL" or str(dentry.get("extension", "")).lower() not in allowed_extensions
            or (expected_extension and str(dentry.get("extension", "")).lower() != expected_extension)
            or not isinstance(dentry.get("version"), int) or dentry["version"] < 1
            or not isinstance(dentry.get("size"), int) or not 0 < dentry["size"] <= MAX_GENERATED_BYTES):
        raise HTTPException(409, "钉钉编辑副本已删除、变更格式或超出大小限制")
    return dentry


async def download_version(session: dict, version: int) -> bytes:
    path = "spaces/" + identifier(session["space_id"]) + "/dentries/" + identifier(session["dentry_id"]) + "/downloadInfos/query"
    info = await storage_request("POST", path, session["union_id"], {"option": {"version": version, "preferIntranet": False}})
    url, headers = _signed_resource(info)
    try:
        async with httpx.AsyncClient(timeout=60, trust_env=False, follow_redirects=False) as client:
            async with client.stream("GET", url, headers=headers) as response:
                if response.status_code != 200:
                    raise HTTPException(502, "钉钉文件下载失败，未保存回 OA")
                content = bytearray()
                async for chunk in response.aiter_bytes():
                    if len(content) + len(chunk) > MAX_GENERATED_BYTES:
                        raise HTTPException(413, "钉钉文件超过20MB，未保存回 OA")
                    content.extend(chunk)
                return bytes(content)
    except httpx.HTTPError as exc:
        raise HTTPException(502, "钉钉文件下载未完成，未保存回 OA") from exc


async def editor_url(session: dict) -> str:
    await dentry_info(session)
    path = "spaces/" + identifier(session["space_id"]) + "/dentries/" + identifier(session["dentry_id"]) + "/openInfos/query"
    result = await storage_request("POST", path, session["union_id"], {
        "option": {"type": "EDIT", "waterMark": True, "checkLogin": True},
    })
    if not isinstance(result.get("url"), str):
        raise HTTPException(502, "钉钉未返回 Office 编辑地址")
    return provider_url(result["url"], editor=True)
