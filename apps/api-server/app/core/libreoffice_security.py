"""WOPI 专属令牌、引擎 proof 校验和实时业务授权。"""

import base64
import secrets
import struct
from datetime import datetime, timezone

import jwt
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from fastapi import HTTPException, Request
from sqlalchemy import select

from app.config import settings
from app.core.libreoffice_config import discovery, editor_configuration
from app.core.permissions import (
    _ensure_record_module,
    _require_case_action,
    _require_case_detail_write_access,
    _user_permission_payload,
)
from app.models import User
from app.security import user_role_ids

WOPI_AUDIENCE = "sunhold-oa-wopi"
WOPI_ISSUER = "sunhold-oa-libreoffice"


def session_token(session: dict) -> str:
    return jwt.encode({
        "iss": WOPI_ISSUER, "aud": WOPI_AUDIENCE, "sub": session["user"],
        "case_id": session["case_id"], "attachment_id": session["attachment_id"],
        "sid": session["id"], "jti": session["token_id"],
        "iat": int(datetime.now(timezone.utc).timestamp()),
        "exp": int(datetime.fromisoformat(session["expires_at"]).timestamp()),
    }, settings.office_wopi_token_secret, algorithm="HS256")


def request_token(request: Request, session_id: str) -> tuple[str, dict]:
    editor_configuration()
    tokens = request.query_params.getlist("access_token")
    bearer = request.headers.get("authorization", "")
    if len(tokens) > 1 or (bearer and not bearer.startswith("Bearer ")):
        raise HTTPException(status_code=401, detail="WOPI 令牌格式无效")
    header_token = bearer.removeprefix("Bearer ") if bearer else ""
    token = tokens[0] if tokens else header_token
    if not token or len(token) > 4096 or (header_token and not secrets.compare_digest(token, header_token)):
        raise HTTPException(status_code=401, detail="WOPI 令牌缺失或不一致")
    try:
        payload = jwt.decode(token, settings.office_wopi_token_secret, algorithms=["HS256"],
                             audience=WOPI_AUDIENCE, issuer=WOPI_ISSUER,
                             options={"require": ["exp", "iat", "sub", "sid", "jti", "case_id", "attachment_id"]})
        if payload["sid"] != session_id or type(payload["case_id"]) is not int or type(payload["attachment_id"]) is not int:
            raise ValueError("令牌业务归属不匹配")
    except (jwt.PyJWTError, ValueError) as exc:
        raise HTTPException(status_code=401, detail="WOPI 令牌无效或已过期") from exc
    return token, payload


async def verify_proof(request: Request, token: str) -> None:
    config = editor_configuration()
    try:
        timestamp = int(request.headers["x-wopi-timestamp"])
        # WOPI 使用自公元 0001 年起的 .NET ticks，不是 Windows FILETIME。
        request_time = timestamp / 10_000_000 - 62_135_596_800
        age = datetime.now(timezone.utc).timestamp() - request_time
        if not -300 <= age <= 1200:
            raise ValueError("proof 时间戳超出有效范围")
        proof = request.headers["x-wopi-proof"]
        if len(proof) > 4096:
            raise ValueError("proof 过长")
        query = request.scope.get("query_string", b"").decode("ascii")
        url = config["wopi"] + request.url.path + ("?" + query if query else "")
        token_bytes, url_bytes = token.encode("utf-8"), url.upper().encode("utf-8")
        signed = (struct.pack(">I", len(token_bytes)) + token_bytes
                  + struct.pack(">I", len(url_bytes)) + url_bytes + struct.pack(">IQ", 8, timestamp))
        signatures = {name: base64.b64decode(value, validate=True) for name, value in (
            ("current", proof), ("old", request.headers.get("x-wopi-proofold", "")),
        ) if value}
    except (KeyError, ValueError, OverflowError, UnicodeError, struct.error) as exc:
        raise HTTPException(status_code=401, detail="WOPI 引擎 proof 缺失或无效") from exc
    for refresh in (False, True):
        keys = (await discovery(refresh=refresh))["proof"]
        for signature_name, prefix in (("current", ""), ("old", ""), ("current", "old")):
            if signature_name not in signatures or not keys.get(prefix + "modulus") or not keys.get(prefix + "exponent"):
                continue
            try:
                modulus = int.from_bytes(base64.b64decode(keys[prefix + "modulus"], validate=True), "big")
                exponent = int.from_bytes(base64.b64decode(keys[prefix + "exponent"], validate=True), "big")
                rsa.RSAPublicNumbers(exponent, modulus).public_key().verify(
                    signatures[signature_name], signed, padding.PKCS1v15(), hashes.SHA256())
                return
            except InvalidSignature:
                continue
            except ValueError as exc:
                raise HTTPException(status_code=502, detail="CODE discovery proof 公钥无效") from exc
    raise HTTPException(status_code=401, detail="WOPI 请求不是受信任引擎签发")


async def fresh_identity(username: str, db) -> dict:
    user = await db.scalar(select(User).where(User.username == username).execution_options(populate_existing=True))
    if not user or not user.is_active or user.must_change_password:
        raise HTTPException(status_code=401, detail="Office 账号已失效或需要修改密码")
    permission = await _user_permission_payload(user, db)
    roles = user_role_ids(user)
    return {"username": user.username, "display_name": user.display_name, "department": user.department,
            "role": roles[0], "role_ids": roles, "_actual_role": roles[0], "_actual_role_ids": roles,
            "menu_keys": permission.get("menu_keys") or [], "action_keys": permission.get("action_keys") or [],
            "data_scope": permission.get("data_scope"), "_page_menu_capability": False}


async def authorized_case(case_id: int, identity: dict, db):
    identity = await fresh_identity(identity["username"], db)
    record = await _ensure_record_module(case_id, "case", identity, db)
    await _require_case_detail_write_access(record, identity, db)
    if record.status == "已合并":
        raise HTTPException(status_code=409, detail="已合并案件不能在线编辑附件")
    await _require_case_action(identity, db, "case.document.manage")
    return record, identity
