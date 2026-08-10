from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

import httpx

from .config import settings


class DingTalkError(RuntimeError):
    pass


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
        payload = response.json()
        if int(payload.get("errcode") or 0) != 0:
            raise DingTalkError(str(payload.get("errmsg") or "钉钉工作通知发送失败"))
        return str(payload.get("task_id") or "")


dingtalk_client = DingTalkClient()
