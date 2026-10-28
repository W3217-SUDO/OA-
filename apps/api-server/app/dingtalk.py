from __future__ import annotations

import asyncio
import re
from datetime import datetime, timedelta, timezone

import httpx

from .config import settings


class DingTalkError(RuntimeError):
    pass


class DingTalkMembershipError(DingTalkError):
    """扫码身份不是应用所属企业的内部员工。"""


class DingTalkRejectedError(DingTalkError):
    """钉钉接口明确拒绝了本次工作通知。"""


class DingTalkUnknownResultError(RuntimeError):
    """请求已发出，但响应不足以确认工作通知是否发送成功。"""


class DingTalkClient:
    def __init__(self) -> None:
        self._access_token = ""
        self._expires_at = datetime.min.replace(tzinfo=timezone.utc)
        self._token_lock = asyncio.Lock()

    @property
    def configured(self) -> bool:
        return all((settings.dingtalk_corp_id, settings.dingtalk_agent_id, settings.dingtalk_app_key, settings.dingtalk_app_secret))

    async def access_token(self) -> str:
        if self._access_token and datetime.now(timezone.utc) < self._expires_at:
            return self._access_token
        async with self._token_lock:
            if self._access_token and datetime.now(timezone.utc) < self._expires_at:
                return self._access_token
            if not self.configured:
                raise DingTalkError("钉钉应用尚未配置")
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(
                    "https://api.dingtalk.com/v1.0/oauth2/accessToken",
                    json={"appKey": settings.dingtalk_app_key, "appSecret": settings.dingtalk_app_secret},
                )
            response.raise_for_status()
            payload = response.json()
            token = str(payload.get("accessToken") or "").strip()
            if not token:
                raise DingTalkError(str(payload.get("message") or "钉钉访问凭证获取失败"))
            expires_in = max(300, int(payload.get("expireIn") or 7200))
            self._access_token = token
            self._expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in - 120)
            return token

    async def user_by_auth_code(self, auth_code: str) -> dict:
        token = await self.access_token()
        async with httpx.AsyncClient(timeout=10) as client:
            auth_response = await client.post(
                f"https://oapi.dingtalk.com/topapi/v2/user/getuserinfo?access_token={token}",
                json={"code": auth_code},
            )
            auth_payload = auth_response.json()
            if int(auth_payload.get("errcode") or 0) != 0:
                raise DingTalkError(str(auth_payload.get("errmsg") or "钉钉免登身份校验失败"))
            user_id = str((auth_payload.get("result") or {}).get("userid") or "").strip()
            if not user_id:
                raise DingTalkError("钉钉未返回用户标识")
            user_response = await client.post(
                f"https://oapi.dingtalk.com/topapi/v2/user/get?access_token={token}",
                json={"userid": user_id, "language": "zh_CN"},
            )
            user_payload = user_response.json()
        result = user_payload.get("result") or {}
        return {"user_id": user_id, "name": str(result.get("name") or "").strip(), "mobile": str(result.get("mobile") or "").strip()}

    async def user_name(self, user_id: str) -> str:
        token = await self.access_token()
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(
                f"https://oapi.dingtalk.com/topapi/v2/user/get?access_token={token}",
                json={"userid": user_id, "language": "zh_CN"},
            )
            payload = response.json()
        if int(payload.get("errcode") or 0) != 0:
            raise DingTalkError(str(payload.get("errmsg") or "钉钉用户查询失败"))
        return str((payload.get("result") or {}).get("name") or "").strip()

    async def user_by_web_auth_code(self, auth_code: str) -> dict:
        """网页授权码与端内免登码不同，先换用户凭证再核验企业员工身份。"""
        async with httpx.AsyncClient(timeout=10) as client:
            token_response = await client.post("https://api.dingtalk.com/v1.0/oauth2/userAccessToken", json={
                "clientId": settings.dingtalk_app_key, "clientSecret": settings.dingtalk_app_secret,
                "code": auth_code, "grantType": "authorization_code",
            })
            token_response.raise_for_status()
            token_data = token_response.json()
            if not isinstance(token_data, dict) or not isinstance(token_data.get("accessToken"), str) or not token_data["accessToken"]:
                raise DingTalkError("钉钉扫码未返回用户访问凭证")
            user_response = await client.get("https://api.dingtalk.com/v1.0/contact/users/me",
                                             headers={"x-acs-dingtalk-access-token": token_data["accessToken"]})
            user_response.raise_for_status()
            user_data = user_response.json()
            if not isinstance(user_data, dict) or not isinstance(user_data.get("unionId"), str) or not user_data["unionId"]:
                raise DingTalkError("钉钉扫码未返回用户身份")
            app_token = await self.access_token()
            member_response = await client.post("https://oapi.dingtalk.com/topapi/user/getbyunionid",
                                                params={"access_token": app_token}, json={"unionid": user_data["unionId"]})
            member_response.raise_for_status()
            member_data = member_response.json()
            if not isinstance(member_data, dict) or type(member_data.get("errcode")) is not int or member_data["errcode"] != 0:
                raise DingTalkError("钉钉企业通讯录身份查询失败")
            member = member_data.get("result")
            if not isinstance(member, dict) or type(member.get("contact_type")) is not int or member["contact_type"] != 0 or not isinstance(member.get("userid"), str) or not member["userid"]:
                raise DingTalkMembershipError("钉钉扫码账号不是企业内部员工")
            detail_response = await client.post("https://oapi.dingtalk.com/topapi/v2/user/get",
                                                params={"access_token": app_token}, json={"userid": member["userid"], "language": "zh_CN"})
            detail_response.raise_for_status()
            detail_data = detail_response.json()
            if not isinstance(detail_data, dict) or type(detail_data.get("errcode")) is not int or detail_data["errcode"] != 0:
                raise DingTalkError("无法读取扫码员工的企业通讯录信息")
            detail = detail_data.get("result")
            if not isinstance(detail, dict) or detail.get("userid") != member["userid"]:
                raise DingTalkError("钉钉企业员工身份返回不完整")
            return {"user_id": member["userid"], "name": str(detail.get("name") or "").strip(), "mobile": str(detail.get("mobile") or "").strip()}

    async def send_work_notification(self, user_id: str, title: str, content: str) -> str:
        token = await self.access_token()
        text = f"{title}\n{content}".strip()
        if settings.dingtalk_app_url:
            text = f"{text}\n{settings.dingtalk_app_url}"
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(
                f"https://oapi.dingtalk.com/topapi/message/corpconversation/asyncsend_v2?access_token={token}",
                json={
                    "agent_id": int(settings.dingtalk_agent_id),
                    "userid_list": user_id,
                    "msg": {"msgtype": "text", "text": {"content": text[:2000]}},
                },
            )
        try:
            payload = response.json()
        except ValueError as exc:
            raise DingTalkUnknownResultError("钉钉工作通知响应不是有效 JSON，发送结果待核实") from exc
        if not isinstance(payload, dict) or type(payload.get("errcode")) is not int:
            raise DingTalkUnknownResultError("钉钉工作通知响应缺少有效 errcode，发送结果待核实")
        if payload["errcode"] != 0:
            raise DingTalkRejectedError(str(payload.get("errmsg") or "钉钉工作通知发送失败"))
        if not response.is_success:
            raise DingTalkUnknownResultError("钉钉工作通知响应状态异常，发送结果待核实")
        task_id = payload.get("task_id")
        if isinstance(task_id, bool) or not isinstance(task_id, (int, str)):
            raise DingTalkUnknownResultError("钉钉工作通知响应缺少有效 task_id，发送结果待核实")
        reference = str(task_id).strip()
        if not re.fullmatch(r"[0-9]+", reference) or int(reference) <= 0:
            raise DingTalkUnknownResultError("钉钉工作通知响应缺少有效 task_id，发送结果待核实")
        return reference


dingtalk_client = DingTalkClient()
