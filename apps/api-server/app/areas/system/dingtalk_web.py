"""浏览器钉钉扫码授权与首次员工账号绑定。"""

import hmac
import secrets
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode, urlsplit

import httpx
import jwt
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.dingtalk import DingTalkError, DingTalkMembershipError, dingtalk_client
from .dingtalk_auth import bind_verified_employee, login_verified_employee

router = APIRouter(prefix=f"{settings.api_prefix}/auth/dingtalk/web")
STATE_COOKIE = "oa_dingtalk_web_state"
BIND_COOKIE = "oa_dingtalk_web_binding"
COOKIE_PATH = f"{settings.api_prefix}/auth/dingtalk/web"


class WebLoginInput(BaseModel):
    auth_code: str = Field(min_length=1, max_length=512)
    state: str = Field(min_length=1, max_length=2048, pattern=r"^[A-Za-z0-9_.-]+$")


class WebBindingInput(BaseModel):
    username: str = Field(min_length=2, max_length=64)
    password: str = Field(min_length=1, max_length=128)


def callback_url() -> str:
    if not dingtalk_client.configured:
        raise HTTPException(status_code=503, detail="钉钉登录尚未配置")
    url = settings.dingtalk_app_url.strip()
    parsed = urlsplit(url)
    if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise HTTPException(status_code=503, detail="钉钉扫码登录需要配置正式 HTTPS 首页地址")
    return url


def ticket(audience: str, seconds: int, **claims: str) -> str:
    now = datetime.now(timezone.utc)
    return jwt.encode({
        **claims, "iss": "oa-dingtalk-web", "aud": audience,
        "iat": now, "exp": now + timedelta(seconds=seconds), "jti": secrets.token_urlsafe(32),
    }, settings.secret_key, algorithm="HS256")


def verify_ticket(value: str, audience: str) -> dict:
    try:
        return jwt.decode(value, settings.secret_key, algorithms=["HS256"], audience=audience,
                          issuer="oa-dingtalk-web", options={"require": ["exp", "iat", "jti", "aud", "iss"]})
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=400, detail="钉钉扫码已过期，请重新扫码登录") from exc


def set_cookie(response: JSONResponse, name: str, value: str, seconds: int) -> None:
    response.set_cookie(name, value, max_age=seconds, path=COOKIE_PATH, secure=True, httponly=True, samesite="lax")


def clear_cookie(response: JSONResponse, name: str) -> None:
    response.delete_cookie(name, path=COOKIE_PATH, secure=True, httponly=True, samesite="lax")


@router.get("/start")
async def start_web_login():
    redirect = callback_url()
    state = ticket("dingtalk-web-login", 300, client_id=settings.dingtalk_app_key, corp_id=settings.dingtalk_corp_id)
    query = urlencode({"client_id": settings.dingtalk_app_key, "redirect_uri": redirect,
                       "response_type": "code", "scope": "openid", "prompt": "consent", "state": state})
    response = JSONResponse({"authorize_url": f"https://login.dingtalk.com/oauth2/auth?{query}"}, headers={"Cache-Control": "no-store"})
    set_cookie(response, STATE_COOKIE, state, 300)
    clear_cookie(response, BIND_COOKIE)
    return response


@router.post("/login")
async def web_login(body: WebLoginInput, request: Request, db: AsyncSession = Depends(get_db)):
    callback_url()
    stored_state = request.cookies.get(STATE_COOKIE, "")
    if not stored_state or not hmac.compare_digest(stored_state, body.state):
        raise HTTPException(status_code=400, detail="钉钉扫码校验不一致，请从登录页重新扫码")
    claims = verify_ticket(body.state, "dingtalk-web-login")
    if claims.get("client_id") != settings.dingtalk_app_key or claims.get("corp_id") != settings.dingtalk_corp_id:
        raise HTTPException(status_code=400, detail="钉钉应用配置已变化，请重新扫码")
    try:
        ding_user = await dingtalk_client.user_by_web_auth_code(body.auth_code)
    except DingTalkMembershipError as exc:
        raise HTTPException(status_code=403, detail="扫码账号不是当前公司的内部员工，无法登录") from exc
    except (DingTalkError, httpx.HTTPError, ValueError) as exc:
        raise HTTPException(status_code=502, detail="钉钉扫码身份校验失败，请重新扫码或联系管理员检查登录配置") from exc
    data = await login_verified_employee(ding_user, db)
    if data is None:
        response = JSONResponse({"detail": "首次扫码请验证本人 OA 账号完成绑定", "binding_required": True}, status_code=403,
                                headers={"Cache-Control": "no-store"})
        set_cookie(response, BIND_COOKIE, ticket("dingtalk-web-bind", 600, user_id=ding_user["user_id"],
                                               client_id=settings.dingtalk_app_key, corp_id=settings.dingtalk_corp_id), 600)
    else:
        response = JSONResponse(jsonable_encoder(data), headers={"Cache-Control": "no-store"})
        clear_cookie(response, BIND_COOKIE)
    clear_cookie(response, STATE_COOKIE)
    return response


@router.post("/bind")
async def bind_web_login(body: WebBindingInput, request: Request, db: AsyncSession = Depends(get_db)):
    callback_url()
    claims = verify_ticket(request.cookies.get(BIND_COOKIE, ""), "dingtalk-web-bind")
    if claims.get("client_id") != settings.dingtalk_app_key or claims.get("corp_id") != settings.dingtalk_corp_id:
        raise HTTPException(status_code=400, detail="钉钉应用配置已变化，请重新扫码")
    user_id = claims.get("user_id")
    if not isinstance(user_id, str) or not user_id:
        raise HTTPException(status_code=400, detail="扫码身份无效，请重新扫码")
    data = await bind_verified_employee({"user_id": user_id}, body.username, body.password, db)
    response = JSONResponse(jsonable_encoder(data), headers={"Cache-Control": "no-store"})
    clear_cookie(response, BIND_COOKIE)
    return response
